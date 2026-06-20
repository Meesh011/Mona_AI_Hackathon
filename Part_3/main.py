"""
main.py
CLI entrypoint: validate one file or a whole folder of work permits.

Usage:
    export GEMINI_API_KEY=your_key_here
    python main.py path/to/permit.pdf
    python main.py path/to/folder_of_permits/
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from pdf_utils import file_to_images
from gemini_client import extract_permit_data
from validator import validate

ACCEPTED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


def validate_file(path: Path) -> dict:
    images = file_to_images(path)
    # Work permits are single-page; if multiple pages come back we use page 1
    # for the primary extraction (front of the card/letter is what matters).
    extracted = extract_permit_data(images[0])
    result = validate(path.name, extracted)
    return result.model_dump(mode="json")


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        print("Usage: python main.py <file_or_folder>")
        sys.exit(1)

    target = Path(argv[1])
    files: list[Path]

    if target.is_dir():
        files = sorted(p for p in target.iterdir() if p.suffix.lower() in ACCEPTED_EXTS)
    elif target.is_file():
        files = [target]
    else:
        print(f"Path not found: {target}")
        sys.exit(1)

    results = []
    for f in files:
        print(f"\n=== Processing {f.name} ===")
        try:
            result = validate_file(f)
        except Exception as exc:  # surface per-file errors without killing the batch
            result = {"filename": f.name, "verdict": "ERROR", "error": str(exc)}

        results.append(result)
        print(json.dumps(result, indent=2, default=str))

    out_path = Path("results.json")
    out_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nSaved {len(results)} result(s) to {out_path.resolve()}")


if __name__ == "__main__":
    main(sys.argv)
