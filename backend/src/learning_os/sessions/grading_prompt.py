GRADING_PROMPT_TEMPLATE = """\
You are grading a finished tutoring session transcript, after the fact — \
not tutoring live. Domain: {domain}.

Planned concepts for this session (grade every one of them, even if the \
transcript never actually got to it):
{concepts}

Full session transcript:
{transcript}

For each planned concept, output exactly one grade:

- not_reached: the concept was never actually quizzed — mentioned in \
passing, or not discussed at all, does not count. Only a real attempt to \
have the learner recall or explain it counts as "reached."
- incorrect: the learner's answer was wrong, per the tutor's own \
in-transcript verdict.
- partial: the learner's answer was right in part, or right but notably \
incomplete, per the tutor's own in-transcript verdict.
- correct: the learner gave a correct explanation/definition, per the \
tutor's own in-transcript verdict — but no distinct follow-up application \
question was posed and answered afterward for this same concept.
- correct_with_application: ALL THREE of the following are true and \
verifiable directly in the transcript text: (1) the learner gave a \
correct base explanation, (2) the tutor then posed a distinct, novel \
concrete-scenario follow-up question about that same concept (not just \
restating the definition), and (3) the learner's answer to that specific \
follow-up was also judged correct. If you cannot point to that exact \
three-part exchange in the transcript, grade it correct instead — do not \
credit a merely fluent-sounding answer with correct_with_application.

For every grade, also give:
- quality (0.0-1.0): how strongly the transcript evidence supports this \
specific grade — a clean, unambiguous exchange gets a high value; a \
borderline or hard-to-classify one gets a lower value. This is about your \
confidence in the grade, not the outcome itself.
- rationale: one or two sentences citing the specific exchange (quote or \
closely paraphrase the relevant turns) that justifies this grade. For \
correct_with_application, the rationale must name the follow-up question \
and the learner's answer to it specifically.

Call record_session_grades with one grade per planned concept, in the \
order the concepts were given above.
"""


def build_grading_prompt(domain: str, concepts: list[str], transcript: str) -> str:
    concept_lines = "\n".join(f"- {concept}" for concept in concepts)
    return GRADING_PROMPT_TEMPLATE.format(domain=domain, concepts=concept_lines, transcript=transcript)
