#!/usr/bin/env python3
"""Check retrospective citations, or a current explicit two-destination approval."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory import approval_history, publication


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true')
    parser.add_argument('--candidate')
    args = parser.parse_args()
    if args.history == bool(args.candidate): parser.error('choose --history or --candidate')
    result = approval_history.check(ROOT) if args.history else publication.approved_plan(ROOT, args.candidate)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
