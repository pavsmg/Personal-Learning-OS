"""decisions.md #63: human review of graded outcomes over the CLI.

Lists graded observations (with the effective outcome after any prior
review) and appends a result-only correction. The raw evidence row is
never edited -- each review is an immutable history entry, latest wins.
"""

import argparse
import sys

from pydantic import ValidationError

from learning_os.mistakes import list_observations, record_evidence_review
from learning_os.mistakes.store import query_reviews

_OUTCOMES: tuple[str, ...] = (
    "not_reached",
    "incorrect",
    "partial",
    "correct",
    "correct_with_application",
)


def _cmd_list(args: argparse.Namespace) -> int:
    rows = list_observations(session_id=args.session, domain=args.domain)
    if args.concept:
        needle = args.concept.lower()
        rows = [row for row in rows if needle in row["concept"].lower()]
    if not rows:
        print("No observations found.")
        return 0
    for row in rows:
        flag = " [reviewed]" if row["reviewed"] else ""
        detail = (
            f" (graded {row['graded_outcome']})" if row["reviewed"] else ""
        )
        print(
            f"{row['session_id']} | {row['domain']} | {row['concept']} | "
            f"{row['outcome']} @ {row['quality']}{detail}{flag}"
        )
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    if args.outcome not in _OUTCOMES:
        print(f"error: outcome must be one of {', '.join(_OUTCOMES)}", file=sys.stderr)
        return 2
    if not args.reason.strip():
        print("error: --reason is required (why is the grade wrong?)", file=sys.stderr)
        return 2
    try:
        review = record_evidence_review(
            session_id=args.session,
            concept=args.concept,
            new_outcome=args.outcome,  # type: ignore[arg-type]
            reason=args.reason.strip(),
            domain=args.domain,
        )
    except (KeyError, ValueError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"Reviewed {review.concept!r} in session {review.session_id}: "
        f"{review.previous_outcome} -> {review.new_outcome} "
        f"(reason: {review.reason})"
    )
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    reviews = query_reviews(session_id=args.session, domain=args.domain, concept=args.concept)
    if not reviews:
        print("No reviews recorded.")
        return 0
    for review in reviews:
        print(
            f"{review.timestamp.isoformat()} | {review.session_id} | "
            f"{review.domain} | {review.concept} | "
            f"{review.previous_outcome} -> {review.new_outcome} | "
            f"{review.reviewer}: {review.reason}"
        )
    return 0


def run() -> None:
    parser = argparse.ArgumentParser(
        description="List graded observations and record human corrections of their outcome."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List observations with effective outcomes.")
    p_list.add_argument("--session", default=None, help="Filter by session id.")
    p_list.add_argument("--domain", default=None, help="Filter by domain.")
    p_list.add_argument("--concept", default=None, help="Substring filter on concept.")
    p_list.set_defaults(func=_cmd_list)

    p_review = sub.add_parser("review", help="Correct one observation's outcome.")
    p_review.add_argument("--session", required=True, help="Session id of the observation.")
    p_review.add_argument("--concept", required=True, help="Concept name (case-insensitive).")
    p_review.add_argument(
        "--domain",
        default=None,
        help="Required when the concept exists in several domains of the session.",
    )
    p_review.add_argument("--outcome", required=True, choices=_OUTCOMES)
    p_review.add_argument("--reason", required=True, help="Why the grade was wrong.")
    p_review.set_defaults(func=_cmd_review)

    p_history = sub.add_parser("history", help="Show the review audit trail.")
    p_history.add_argument("--session", default=None)
    p_history.add_argument("--domain", default=None)
    p_history.add_argument("--concept", default=None)
    p_history.set_defaults(func=_cmd_history)

    args = parser.parse_args()
    raise SystemExit(args.func(args))
