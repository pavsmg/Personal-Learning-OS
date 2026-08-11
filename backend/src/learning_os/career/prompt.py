from learning_os.mistakes.models import MasteryEstimate

CV_SUMMARY_PROMPT_TEMPLATE = """\
Here is a learner's tracked conceptual strengths — concepts they've been \
quizzed on in tutoring sessions and shown solid understanding of, grouped \
by domain (domain, concept, conceptual_understanding 0-1, mistake_count):

{profile_lines}

Write a concise, professional, CV-ready summary of these technical \
strengths, organized by domain. Rules:
- Do not invent skills, employers, projects, years of experience, or \
anything not implied by this list.
- Do not claim more than "demonstrated understanding of X through tracked \
review" — this reflects conceptual understanding verified in conversation, \
not applied/production experience.
- Keep it tight: a short paragraph or a few grouped bullet points, not an \
essay.
"""

JOB_FIT_PROMPT_TEMPLATE = """\
Job description:
{job_description}

Learner's tracked profile — every concept they've been quizzed on in \
tutoring sessions, both strong and weak (domain, concept, \
conceptual_understanding 0-1, mistake_count):

{profile_lines}

Extract the skills/technologies this job actually requires, then:
- matching_strengths: tracked concepts from the profile with \
conceptual_understanding >= 0.7 that are genuinely relevant to this job's \
requirements. Don't force a match that isn't really there.
- gaps: skills/technologies this job requires that are either not in the \
tracked profile at all, or present with conceptual_understanding < 0.7. \
Don't invent a gap the job description doesn't actually imply.

Call record_job_fit_analysis with the result.
"""


def _format_profile(profile: list[MasteryEstimate]) -> str:
    if not profile:
        return "(nothing tracked yet)"
    return "\n".join(
        f"- {p.domain} / {p.concept}: conceptual_understanding={p.conceptual_understanding:.2f}, "
        f"mistake_count={p.mistake_count}"
        for p in profile
    )


def build_cv_summary_prompt(profile: list[MasteryEstimate]) -> str:
    return CV_SUMMARY_PROMPT_TEMPLATE.format(profile_lines=_format_profile(profile))


def build_job_fit_prompt(job_description: str, profile: list[MasteryEstimate]) -> str:
    return JOB_FIT_PROMPT_TEMPLATE.format(
        job_description=job_description,
        profile_lines=_format_profile(profile),
    )
