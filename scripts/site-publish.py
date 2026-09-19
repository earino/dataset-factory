#!/usr/bin/env python3
"""Dataset website lifecycle: prepare / inspect / publish / verify / status."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from factory.site_pipeline import main

if __name__ == "__main__":
    raise SystemExit(main())
