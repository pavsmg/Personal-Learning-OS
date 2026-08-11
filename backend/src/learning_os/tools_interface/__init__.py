from learning_os.mistakes import (
    estimate_mastery,
    get_learning_profile,
    get_recent_mistakes,
    recommend_review,
    save_mistake,
    search_mistakes,
)
from learning_os.retrieval import get_note, related_notes, search_notes
from learning_os.sessions import create_session, finish_session, summarize_session
from learning_os.tools_interface.registry import TOOLS, Tool, call_tool, register
from learning_os.tools_interface.stubs import (
    analyze_job_fit,
    get_curriculum,
    get_language_profile,
    get_learning_statistics,
    retrieve_vocabulary,
    summarize_skills_for_cv,
)

register("search_notes", "Keyword/full-text search over vault notes.", search_notes)
register("get_note", "Fetch a single note's full content and metadata by title.", get_note)
register(
    "related_notes",
    "1-hop wikilink graph traversal (outgoing links + backlinks) for a note.",
    related_notes,
)

register(
    "get_learning_profile",
    "Per-domain, per-concept mastery estimates for the learner.",
    get_learning_profile,
)
register("estimate_mastery", "Estimate mastery of a single concept within a domain.", estimate_mastery)
register(
    "recommend_review",
    "Recommend concepts worth reviewing, optionally scoped to a domain.",
    recommend_review,
)

register("search_mistakes", "Search past mistakes by concept/explanation text.", search_mistakes)
register("save_mistake", "Record a new mistake entry.", save_mistake)
register(
    "get_recent_mistakes",
    "Fetch the most recent mistakes, optionally scoped to a domain.",
    get_recent_mistakes,
)

register("create_session", "Plan a new learning session for a topic.", create_session)
register("finish_session", "Mark a session as finished.", finish_session)
register("summarize_session", "Produce a summary of a finished session.", summarize_session)

register(
    "get_language_profile",
    "Fetch a learner's profile for a specific language (delegates to Language-Lab).",
    get_language_profile,
)
register("get_curriculum", "Fetch the curriculum/roadmap for a specific language.", get_curriculum)
register(
    "retrieve_vocabulary",
    "Retrieve vocabulary for a language, optionally scoped to a topic.",
    retrieve_vocabulary,
)

register("get_learning_statistics", "Aggregate learning statistics across domains.", get_learning_statistics)

register(
    "summarize_skills_for_cv",
    "Turn current per-domain mastery into CV-ready skill language.",
    summarize_skills_for_cv,
)
register(
    "analyze_job_fit",
    "Compare a target job description against the learner profile: strengths to foreground, gaps to close.",
    analyze_job_fit,
)

__all__ = ["TOOLS", "Tool", "call_tool"]
