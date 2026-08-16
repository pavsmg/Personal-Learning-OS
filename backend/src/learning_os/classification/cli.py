import argparse

from learning_os.classification.service import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    apply_classifications,
    classify_unlabeled_notes,
)


def run() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Classify vault notes that infer_domain would leave at 'general' into a real "
            "domain, by embedding similarity against domains already in use elsewhere in "
            "the vault. Dry run by default -- pass --apply to actually write."
        )
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help="Minimum cosine similarity to accept a classification (default: %(default)s).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write domain: into matched notes' frontmatter. Without this flag, only reports what would change.",
    )
    args = parser.parse_args()

    results = classify_unlabeled_notes(threshold=args.threshold)
    if not results:
        print("No notes classified above the confidence threshold.")
        return

    for result in sorted(results, key=lambda r: -r.confidence):
        print(f"{result.note_title!r} -> {result.domain} (confidence {result.confidence:.2f})")

    if args.apply:
        written = apply_classifications(results)
        print(f"\nWrote domain: to {written} note(s).")
    else:
        print(f"\n{len(results)} note(s) would be classified (dry run -- pass --apply to write for real).")


if __name__ == "__main__":
    run()
