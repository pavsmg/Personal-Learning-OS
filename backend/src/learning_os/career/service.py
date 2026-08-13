from typing import Any, Callable

from learning_os.career.models import JobFitAnalysis
from learning_os.career.prompt import build_cv_summary_prompt, build_job_fit_prompt
from learning_os.llm_client import LLMReply, chat_completion
from learning_os.mistakes import get_learning_profile
from learning_os.retrieval import concept_importance

STRENGTH_THRESHOLD = 0.7
NO_DATA_MESSAGE = (
    "Not enough tracked session history yet to summarize skills for a CV — "
    "this reflects concepts you've been quizzed on, and none qualify as a "
    "demonstrated strength yet."
)

ChatFn = Callable[..., LLMReply]

_RECORD_JOB_FIT_TOOL = {
    "type": "function",
    "function": {
        "name": "record_job_fit_analysis",
        "description": "Record the job-fit analysis.",
        "parameters": JobFitAnalysis.model_json_schema(),
    },
}
_RECORD_JOB_FIT_TOOL_CHOICE = {"type": "function", "function": {"name": "record_job_fit_analysis"}}


def summarize_skills_for_cv(_chat_fn: ChatFn = chat_completion) -> str:
    profile = get_learning_profile()
    strengths = [p for p in profile if p.mistake_count > 0 and p.conceptual_understanding >= STRENGTH_THRESHOLD]
    if not strengths:
        return NO_DATA_MESSAGE

    # Vault centrality (decisions.md #37), not job relevance -- deliberately
    # scoped to the CV summary only, not analyze_job_fit below: a job can
    # genuinely need a niche skill that isn't foundational to this vault at
    # all, so blending vault-wide importance into job matching would be the
    # wrong signal there. Concepts that aren't real vault note titles (a
    # real, common case -- see decisions.md #39) get importance 0 and just
    # sort last, not excluded.
    importance = {p.concept: concept_importance(p.concept) for p in strengths}
    strengths = sorted(strengths, key=lambda p: -importance[p.concept])

    reply = _chat_fn([{"role": "user", "content": build_cv_summary_prompt(strengths, importance)}], [])
    return reply.content or ""


def analyze_job_fit(job_description: str, _chat_fn: ChatFn = chat_completion) -> JobFitAnalysis:
    profile = get_learning_profile()
    reply = _chat_fn(
        [{"role": "user", "content": build_job_fit_prompt(job_description, profile)}],
        [_RECORD_JOB_FIT_TOOL],
        tool_choice=_RECORD_JOB_FIT_TOOL_CHOICE,
    )
    arguments: dict[str, Any] = reply.tool_calls[0].arguments
    return JobFitAnalysis(**arguments)
