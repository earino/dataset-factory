"""A job that deliberately fails.

Exercises the failure path end to end: the container writes a diagnostic, then exits
non-zero. The executor must record the failure, keep the diagnostics, and still upload
them, so a failing job is inspectable rather than just lost.
"""
from pathlib import Path

EXIT_CODE = 7


def main():
    out = Path("/output")
    out.mkdir(parents=True, exist_ok=True)
    (out / "partial.txt").write_text(
        "written before the failure; must survive in the uploaded artifacts\n")
    print("scout smoke: about to exit %d on purpose" % EXIT_CODE, flush=True)
    print("scout smoke: second line, on stderr", flush=True)
    return EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())