import sys

from learning_os.career.service import analyze_job_fit, summarize_skills_for_cv


def run() -> None:
    print("=== CV skills summary ===")
    print(summarize_skills_for_cv())

    job_description = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("\nPaste a job description: ")
    if not job_description.strip():
        return

    print("\n=== Job fit analysis ===")
    result = analyze_job_fit(job_description)
    print("Matching strengths:")
    for strength in result.matching_strengths:
        print(f"  - {strength}")
    print("Gaps:")
    for gap in result.gaps:
        print(f"  - {gap}")


if __name__ == "__main__":
    run()
