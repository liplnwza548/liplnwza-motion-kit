#!/usr/bin/env python3
"""Collapse visemes to one shape per timestamp (last shape wins).

Alignment outputs can emit several shapes at the same timestamp (the
Kurt job had 611 raw visemes collapsing to 429 timestamps). A rig that
picks by binary search over the raw list then depends silently on file
order. This step makes the choice explicit and recorded: input is a
list of {"start", "shape"} (or {"visemes": [...]}), output is the same
shape sorted by strictly increasing start, one entry per timestamp.

Usage:
  python3 renderer/dedup_visemes.py --in visemes.json --out visemes-dedup.json
Exit 0 on success; the input file is never modified.
"""
import argparse
import json
from pathlib import Path


def dedupe(visemes):
    dedup = {}
    for v in visemes:
        dedup[v["start"]] = v["shape"]  # last shape wins, explicitly
    return [{"start": s, "shape": dedup[s]} for s in sorted(dedup)]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    data = json.loads(Path(a.inp).read_text(encoding="utf-8"))
    visemes = data["visemes"] if isinstance(data, dict) else data
    out = dedupe(visemes)
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"visemes deduped: {len(visemes)} -> {len(out)}")


if __name__ == "__main__":
    main()
