"""
main.py
CLI entrypoint.

Usage:
    export GEMINI_API_KEY=your_key_here
    python main.py path/to/cv.pdf path/to/certificates_folder/
"""
from __future__ import annotations
import json
import sys

from pipeline import run_pipeline


def main(argv: list[str]) -> None:
    if len(argv) != 3:
        print("Usage: python main.py <cv_file> <certificates_folder>")
        sys.exit(1)

    cv_path, cert_dir = argv[1], argv[2]
    report = run_pipeline(cv_path, cert_dir)

    print(json.dumps(report.model_dump(mode="json"), indent=2, default=str))

    with open("candidate_report.json", "w") as f:
        json.dump(report.model_dump(mode="json"), f, indent=2, default=str)
    print("\nSaved candidate_report.json")


if __name__ == "__main__":
    main(sys.argv)
