import argparse
import asyncio
import json
from functools import lru_cache
from typing import Any

from openai import AsyncOpenAI

from learning_os.config import get_settings
from learning_os.conversation.prompt import TUTORING_TOOLS, build_system_prompt
from learning_os.realtime.audio import Microphone, Speaker, SAMPLE_RATE, load_echo_cancel_module, unload_module
from learning_os.realtime.session_log import SessionLog
from learning_os.realtime.tools import to_realtime_tools
from learning_os.serialization import serialize_for_json, to_json
from learning_os.sessions import create_session, finish_session, record_turn, summarize_session
from learning_os.sessions.models import SessionPlan
from learning_os.tools_interface import call_tool


@lru_cache
def _get_async_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=get_settings().openai_api_key)


async def handle_tool_call(name: str, arguments: dict[str, Any]) -> str:
    try:
        result = call_tool(name, **arguments)
        return to_json(serialize_for_json(result))
    except Exception as exc:  # noqa: BLE001 — feed the error back to the model, don't crash the loop
        return to_json({"error": str(exc)})


def _session_config(plan: SessionPlan) -> dict[str, Any]:
    return {
        "type": "realtime",
        "output_modalities": ["audio"],
        "instructions": build_system_prompt(plan),
        "audio": {
            "input": {
                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                "turn_detection": {"type": "server_vad"},
                "transcription": {"model": "whisper-1"},
            },
            "output": {
                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                "voice": get_settings().openai_realtime_voice,
            },
        },
        "tools": to_realtime_tools(TUTORING_TOOLS),
    }


async def run_voice_session(topic: str | None = None, debug: bool = False) -> None:
    plan = create_session(topic)
    client = _get_async_client()
    log = SessionLog(plan.session_id)
    log.write(f"SESSION START domain={plan.domain!r} objective={plan.objective!r} concepts={plan.concepts}")
    print(f"(logging this session to {log.path})")

    async with client.realtime.connect(model=get_settings().openai_realtime_model) as connection:
        await connection.session.update(session=_session_config(plan))

        module_id = await load_echo_cancel_module()
        speaker = Speaker()
        await speaker.start()
        response_in_progress = False
        assistant_transcript: list[str] = []

        async def stream_microphone() -> None:
            async with Microphone() as mic:
                async for chunk in mic.chunks():
                    await connection.input_audio_buffer.append(audio=chunk)

        mic_task = asyncio.create_task(stream_microphone())
        print("Ready — start talking any time, even while it's speaking. Press Ctrl+C to stop.\n")

        try:
            async for event in connection:
                if event.type == "input_audio_buffer.speech_started":
                    print("\n[listening...]")
                    if response_in_progress:
                        # Barge-in: cancel the server-side response *and* cut
                        # local playback immediately, rather than letting
                        # whatever's still queued drain out and overlap.
                        await connection.response.cancel()
                        await speaker.restart()
                elif event.type == "input_audio_buffer.speech_stopped":
                    print("[thinking...]")
                elif event.type == "conversation.item.input_audio_transcription.completed":
                    print(f"You said: {event.transcript}")
                    log.write(f"USER: {event.transcript}")
                    record_turn(plan.session_id, "user", event.transcript)
                elif event.type == "response.output_audio_transcript.delta":
                    print(event.delta, end="", flush=True)
                    assistant_transcript.append(event.delta)
                elif event.type == "response.created":
                    response_in_progress = True
                elif event.type == "response.output_audio.delta":
                    await speaker.write(event.delta)
                elif event.type == "response.function_call_arguments.done":
                    arguments = json.loads(event.arguments)
                    output = await handle_tool_call(event.name, arguments)
                    if debug:
                        print(f"\n[tool call] {event.name}({arguments}) -> {output[:200]}")
                    log.write(f"TOOL CALL: {event.name}({arguments}) -> {output}")
                    await connection.conversation.item.create(
                        item={"type": "function_call_output", "call_id": event.call_id, "output": output}
                    )
                    await connection.response.create()
                elif event.type == "response.done":
                    response_in_progress = False
                    if assistant_transcript:
                        full_text = "".join(assistant_transcript)
                        log.write(f"ASSISTANT: {full_text}")
                        record_turn(plan.session_id, "assistant", full_text)
                        assistant_transcript.clear()
                    print()
                elif event.type == "error":
                    print("API error:", event.error)
                    log.write(f"ERROR: {event.error}")
        finally:
            mic_task.cancel()
            await asyncio.gather(mic_task, return_exceptions=True)
            await speaker.stop()
            await unload_module(module_id)
            finish_session(plan.session_id)
            summary = summarize_session(plan.session_id)
            print(f"\n--- {summary.summary} ---")
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
