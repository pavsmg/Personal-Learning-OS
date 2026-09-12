import argparse
import asyncio
import json
import sys
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI, WebSocketConnectionClosedError

from learning_os.config import get_settings
from learning_os.conversation.prompt import END_SESSION_NUDGE, TUTORING_TOOLS, build_system_prompt
from learning_os.debug_output import print_tool_call
from learning_os.language import LANGUAGES
from learning_os.realtime.audio import (
    BYTES_PER_SAMPLE,
    SAMPLE_RATE,
    Microphone,
    Speaker,
    load_echo_cancel_module,
    reap_stale_echo_cancel_modules,
    unload_module,
)
from learning_os.realtime.tools import to_realtime_tools
from learning_os.session_log import SessionLog
from learning_os.serialization import serialize_for_json, to_json
from learning_os.sessions import create_session, finish_session, record_turn, summarize_session
from learning_os.sessions.models import SessionPlan
from learning_os.tools_interface import call_tool


@lru_cache
def _get_async_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


# The paplay subprocess needs a moment to connect to its PipeWire sink
# before it can accept audio without stuttering -- open_session() (called
# right after Speaker.start()) triggers the model to start talking almost
# immediately, so without a short wait the very first response's audio
# arrives before playback is actually ready for it. Not tuned against real
# measurements, just long enough to clear typical subprocess/device
# handshake overhead -- decisions.md #58.
SPEAKER_WARMUP_SECONDS = 0.3


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> str:
    """call_tool is synchronous (real vault/SQLite I/O, and a first-ever
    vault-index build costs ~2s) -- run it in a thread so it can't block
    this loop's own event processing. Without this, every grounding tool
    call (rule 5, almost always right before the tutor starts talking)
    stalls the mic read loop and Speaker.write() for its full duration,
    which is a real, confirmed cause of choppy assistant audio
    (decisions.md #59). Threading alone isn't the whole fix -- see
    run_voice_session's response.function_call_arguments.done handling,
    which now also runs this concurrently with the rest of event dispatch
    instead of awaiting it inline (decisions.md #61)."""
    try:
        result = await asyncio.to_thread(call_tool, name, **arguments)
        return to_json(serialize_for_json(result))
    except Exception as exc:  # noqa: BLE001 — feed the error back to the model, don't crash the loop
        return to_json({"error": str(exc)})


async def open_session(connection: Any) -> None:
    """Rule 8 has the tutor open the session itself. The text loop does that
    by asking for the first reply outright; over the Realtime API nothing is
    spoken until a response is created, so without this the model sits
    waiting for the learner — the exact opposite of the rule, and not a
    disobedient model but an unreachable instruction (decisions.md #48)."""
    await connection.response.create()


async def request_closing(connection: Any) -> None:
    """The same wrap-up turn the text loop gets from END_SESSION_NUDGE: a
    spoken recap of what was covered, before the session is summarized."""
    await connection.conversation.item.create(
        item={
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": END_SESSION_NUDGE}],
        }
    )
    await connection.response.create()


def _session_config(plan: SessionPlan) -> dict[str, Any]:
    settings = get_settings()
    # far_field noise reduction: the SDK's own docs recommend it specifically
    # for "laptop or conference room microphones" (as opposed to near_field
    # for headphones) -- our setup (PipeWire echo-cancel over open speakers,
    # not a headset mic) matches that exactly. Filters audio before it
    # reaches VAD/transcription, which is where a real session produced a
    # nonsense transcript ("Good riddance and be safe, Force...") that reads
    # like a transcription-model hallucination on noisy/quiet input, not an
    # actual mis-hearing of real words (decisions.md #58).
    transcription: dict[str, Any] = {
        "model": settings.openai_realtime_transcription_model,
        # Feeding the session's own planned concepts as keywords helps the
        # transcription model recognize domain vocabulary it would
        # otherwise mis-hear (e.g. "Electromagnetism", "GraphRAG") --
        # decisions.md #61. The SDK docs list this as supported for
        # gpt-transcribe/gpt-live-transcribe specifically, not explicitly
        # confirmed for openai_realtime_transcription_model's default
        # (gpt-4o-mini-transcribe); the SDK doesn't validate this
        # client-side, so an unsupported field would surface (if at all)
        # as a logged "error" event or a mismatched session.updated echo,
        # both now logged -- check those after a real session before
        # trusting this is actually taking effect.
        "keywords": plan.concepts,
    }
    if plan.domain not in LANGUAGES:
        # Supplying the language improves accuracy and latency per the
        # SDK's own docs -- skipped for language-domain sessions, where the
        # learner may genuinely be speaking the target language, not
        # English, and forcing "en" would actively hurt transcription there.
        transcription["language"] = "en"

    return {
        "type": "realtime",
        "output_modalities": ["audio"],
        "instructions": build_system_prompt(plan),
        "audio": {
            "input": {
                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                # Raised from the SDK's 500ms default (decisions.md #59): a
                # real session showed a longer thinking-pause getting read
                # as "done talking," splitting one answer into unrelated
                # fragments ("science." then "Thank you." as two separate
                # transcribed turns) and triggering a response before the
                # learner had actually finished.
                "turn_detection": {
                    "type": "server_vad",
                    "silence_duration_ms": settings.openai_realtime_silence_duration_ms,
                },
                "noise_reduction": {"type": settings.openai_realtime_noise_reduction},
                "transcription": transcription,
            },
            "output": {
                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                "voice": get_settings().openai_realtime_voice,
            },
        },
        "tools": to_realtime_tools(TUTORING_TOOLS),
    }


def _task_failure_logger(name: str, log: SessionLog) -> Any:
    """Attached via add_done_callback to mic_task/end_task -- decisions.md
    #61. Without this, either task dying silently (parec missing, a raised
    exception deep in request_closing) meant the learner just stopped being
    heard, or Enter stopped working, with zero indication why. A task we
    cancelled ourselves at teardown is expected and stays silent; anything
    else -- a raised exception, or the task simply finishing on its own
    before we asked it to -- gets logged."""

    def _callback(task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        message = f"{name} task failed: {exc}" if exc is not None else f"{name} task ended unexpectedly"
        print(f"[audio] {message}", file=sys.stderr)
        log.write(f"{name.upper()} TASK ENDED: {message}")

    return _callback


async def run_voice_session(topic: str | None = None, debug: bool = False) -> None:
    plan = create_session(topic)
    client = _get_async_client()
    log = SessionLog(plan.session_id)
    log.write(f"SESSION START domain={plan.domain!r} objective={plan.objective!r} concepts={plan.concepts}")
    print(f"(logging this session to {log.path})")

    async with client.realtime.connect(model=get_settings().openai_realtime_model) as connection:
        await connection.session.update(session=_session_config(plan))

        response_in_progress = False
        assistant_transcript: list[str] = []
        assistant_line_open = False
        call_number = 0
        closing_requested = False
        current_response_id: str | None = None
        current_audio_item_id: str | None = None
        current_audio_item_bytes = 0
        current_audio_item_started_at: float | None = None
        # response_id -> tool-call tasks still running for that response.
        # decisions.md #61: a single response can request more than one
        # tool call (confirmed in real logs -- search_notes and get_note in
        # the same turn); creating a follow-up response after *each* one
        # individually raced the server. Now every call for a response runs
        # concurrently, and exactly one follow-up response is created once
        # all of them are in.
        pending_tool_tasks: dict[str, list[asyncio.Task]] = {}

        def _fresh_line() -> None:
            nonlocal assistant_line_open
            if assistant_line_open:
                print()
                assistant_line_open = False

        async def run_tool_call(name: str, call_id: str, arguments: dict[str, Any]) -> tuple[str, str, dict, str]:
            output = await handle_tool_call(name, arguments)
            return call_id, name, arguments, output

        # decisions.md #61: acquisition moved inside the try/finally below
        # (previously it ran before the try started at all, so a failure
        # partway through -- e.g. Speaker.start() erroring after the
        # echo-cancel module had already loaded -- leaked it permanently).
        module_id: str | None = None
        speaker: Speaker | None = None
        mic_task: asyncio.Task | None = None
        end_task: asyncio.Task | None = None

        async def stream_microphone() -> None:
            async with Microphone() as mic:
                async for chunk in mic.chunks():
                    await connection.input_audio_buffer.append(audio=chunk)

        async def wait_for_end_request() -> None:
            """Ending with Enter rather than Ctrl+C is what makes a closing
            turn possible at all. Reads stdin via a pipe transport, not a
            thread (decisions.md #61): asyncio.to_thread's underlying
            worker thread can't actually be interrupted by task
            cancellation -- it stays blocked in readline() until the
            process exits, which meant Ctrl+C could hang for minutes
            waiting on the executor's shutdown timeout instead of exiting.
            A pipe-based reader responds to cancellation immediately."""
            nonlocal closing_requested
            running_loop = asyncio.get_running_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            transport, _ = await running_loop.connect_read_pipe(lambda: protocol, sys.stdin)
            try:
                await reader.readline()
            finally:
                transport.close()
            closing_requested = True
            print("\n[wrapping up...]")
            await request_closing(connection)

        try:
            await reap_stale_echo_cancel_modules()
            module_id = await load_echo_cancel_module()
            speaker = Speaker()
            await speaker.start()

            mic_task = asyncio.create_task(stream_microphone())
            mic_task.add_done_callback(_task_failure_logger("microphone", log))

            end_task = asyncio.create_task(wait_for_end_request()) if sys.stdin.isatty() else None
            if end_task is not None:
                end_task.add_done_callback(_task_failure_logger("end-request", log))

            print("Ready — start talking any time, even while it's speaking. Press Enter to finish.\n")
            await asyncio.sleep(SPEAKER_WARMUP_SECONDS)
            await open_session(connection)

            async for event in connection:
                if event.type == "input_audio_buffer.speech_started":
                    _fresh_line()
                    print("[listening...]")
                    if response_in_progress:
                        # Server-side VAD already auto-cancels the in-flight
                        # response by default (ServerVad.interrupt_response
                        # defaults to true) -- an explicit client-side
                        # response.cancel() here used to race that server-
                        # side cancel, which is exactly what produced the
                        # response_cancel_not_active errors #59/#60 had to
                        # build defenses around. Removed: local cleanup
                        # (playback, state) is still entirely our job, since
                        # only the client knows what's actually been heard
                        # (decisions.md #61).
                        if current_audio_item_id is not None and current_audio_item_started_at is not None:
                            elapsed = asyncio.get_running_loop().time() - current_audio_item_started_at
                            played_bytes = min(
                                current_audio_item_bytes,
                                int(elapsed * SAMPLE_RATE * BYTES_PER_SAMPLE),
                            )
                            audio_end_ms = int(played_bytes / (SAMPLE_RATE * BYTES_PER_SAMPLE) * 1000)
                            try:
                                await connection.conversation.item.truncate(
                                    item_id=current_audio_item_id,
                                    content_index=0,
                                    audio_end_ms=audio_end_ms,
                                )
                            except Exception as exc:  # noqa: BLE001 — best-effort; the item may already be finished
                                log.write(f"TRUNCATE FAILED (harmless): {exc}")
                        await speaker.restart()
                        current_response_id = None
                        current_audio_item_id = None
                        assistant_transcript.clear()
                        response_in_progress = False
                        if closing_requested:
                            # The learner interrupted the closing recap --
                            # treat that as "I'm done," not as a new turn to
                            # answer (decisions.md #61: previously the
                            # response-id staleness filter meant a barge-in
                            # here could make the loop never see a matching
                            # response.done again, so Enter would stop
                            # working).
                            break
                elif event.type == "input_audio_buffer.speech_stopped":
                    _fresh_line()
                    print("[thinking...]")
                elif event.type == "conversation.item.input_audio_transcription.completed":
                    _fresh_line()
                    print(f"You said: {event.transcript}")
                    log.write(f"USER: {event.transcript}")
                    record_turn(plan.session_id, "user", event.transcript)
                elif event.type == "conversation.item.input_audio_transcription.failed":
                    _fresh_line()
                    print("[transcription failed]")
                    log.write(f"TRANSCRIPTION FAILED: {event.error}")
                elif event.type == "response.output_audio_transcript.delta":
                    if event.response_id != current_response_id:
                        continue  # a stray delta for a response we've already cancelled/moved past
                    print(event.delta, end="", flush=True)
                    assistant_line_open = True
                    assistant_transcript.append(event.delta)
                elif event.type == "response.created":
                    current_response_id = event.response.id
                    response_in_progress = True
                elif event.type == "response.output_audio.delta":
                    if event.response_id != current_response_id:
                        continue  # same staleness guard as the transcript delta above
                    if event.item_id != current_audio_item_id:
                        current_audio_item_id = event.item_id
                        current_audio_item_bytes = 0
                        current_audio_item_started_at = asyncio.get_running_loop().time()
                    current_audio_item_bytes += await speaker.write(event.delta)
                elif event.type == "response.function_call_arguments.done":
                    arguments = json.loads(event.arguments)
                    task = asyncio.create_task(run_tool_call(event.name, event.call_id, arguments))
                    pending_tool_tasks.setdefault(event.response_id, []).append(task)
                elif event.type == "response.done":
                    if event.response.id != current_response_id:
                        continue  # a stray done for an already-cancelled response; nothing of ours to update
                    response_in_progress = False
                    if assistant_transcript:
                        full_text = "".join(assistant_transcript)
                        log.write(f"ASSISTANT: {full_text}")
                        record_turn(plan.session_id, "assistant", full_text)
                        assistant_transcript.clear()
                    _fresh_line()
                    print()

                    tasks = pending_tool_tasks.pop(event.response.id, [])
                    if tasks:
                        for call_id, name, arguments, output in await asyncio.gather(*tasks):
                            if debug:
                                call_number += 1
                                print_tool_call(call_number, name, arguments, output)
                            log.write(f"TOOL CALL: {name}({arguments}) -> {output}")
                            await connection.conversation.item.create(
                                item={"type": "function_call_output", "call_id": call_id, "output": output}
                            )
                        # Exactly one follow-up response for however many
                        # tool calls this turn made (decisions.md #61) --
                        # this response.done doesn't end the turn, the
                        # follow-up response's own eventual response.done
                        # does.
                        await connection.response.create()
                        continue

                    if closing_requested:
                        # response.done means the server is finished
                        # *generating* -- local playback can still be
                        # catching up, so wait for it to actually finish
                        # before tearing the speaker down (decisions.md
                        # #59), or the last sentence gets cut off audibly
                        # even though the full text already reached the log.
                        await speaker.wait_until_drained()
                        break
                elif event.type == "session.updated":
                    # Visibility for manual verification after a real
                    # session: if _session_config's dict ever has a bad key
                    # the SDK doesn't validate client-side, this is the only
                    # place that would show it (decisions.md #61).
                    log.write(f"SESSION CONFIG ECHOED: {event.session}")
                elif event.type == "error":
                    _fresh_line()
                    print("API error:", event.error)
                    log.write(f"ERROR: {event.error}")
                else:
                    # Not silently dropped -- rate_limits.updated,
                    # input_audio_buffer.timeout_triggered, and anything
                    # else unhandled at least leaves a trace (decisions.md
                    # #61).
                    log.write(f"UNHANDLED EVENT: {event.type}")

            if not closing_requested:
                _fresh_line()
                print("\n[connection closed by the server]")
                log.write("CONNECTION CLOSED (unexpected, server-initiated)")
        except WebSocketConnectionClosedError as exc:
            _fresh_line()
            print(f"\n[connection error: {exc}]")
            log.write(f"CONNECTION ERROR: {exc}")
        finally:
            if assistant_transcript:
                # A session ending mid-response (Ctrl+C, a connection error)
                # would otherwise lose the partial turn from both the log
                # and #44's grading transcript (decisions.md #61).
                full_text = "".join(assistant_transcript)
                log.write(f"ASSISTANT (incomplete): {full_text}")
                record_turn(plan.session_id, "assistant", full_text)

            leftover_tool_tasks = [task for tasks in pending_tool_tasks.values() for task in tasks]
            for task in (mic_task, end_task, *leftover_tool_tasks):
                if task is not None:
                    task.cancel()
            await asyncio.gather(
                *(t for t in (mic_task, end_task, *leftover_tool_tasks) if t is not None), return_exceptions=True
            )
            if speaker is not None:
                await speaker.stop()
            if module_id is not None:
                await unload_module(module_id)

            finish_session(plan.session_id, _log=log)
            summary = summarize_session(plan.session_id)
            _fresh_line()
            print(f"--- {summary.summary} ---")
            log.write(f"SUMMARY: {summary.summary}")
            log.write("SESSION END")
            log.close()


def run() -> None:
    parser = argparse.ArgumentParser(description="Personal Learning OS — voice conversation")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Print each tool call (name, arguments, and result) as it happens, for inspection/testing.",
    )
    parser.add_argument(
        "topic", nargs="*", help="Topic to study (omit to let the system pick automatically)."
    )
    args = parser.parse_args()

    topic = " ".join(args.topic) if args.topic else None
    if topic is None:
        topic = input("What do you want to study today? (leave blank to let it pick) ").strip() or None

    asyncio.run(run_voice_session(topic, debug=args.debug))


if __name__ == "__main__":
    run()
