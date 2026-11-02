#!/usr/bin/env python3
"""Convert MFA alignment + TTS script into chip timing (MFA path).

Companion to prepare_cues.py, which covers the faster-whisper attention
alignment path. This file is deliberately separate: the inputs differ
(MFA JSON vs. segments + a local model), the tokenizer differs
(newmm + a per-job merge map vs. lexical chips), and merging the two
would turn two clear scripts into one branching one. Both paths share
the output contract: a bare list of {"word", "start", "end"} (the
PoseMouthRig reads words[-1]['end'] and expects a list) plus a
provenance sidecar.

Pipeline (fails loudly instead of guessing):
  1. Segment the script (whitespace stripped) with pythainlp newmm,
     or with a checked-in --tokens-cache whose concatenation is
     verified against the script before use.
  2. Apply --merge-map (list of {"parts": [...], "chip": str}) ->
     chips. The chip concatenation must equal the script
     concatenation exactly (NFC), or the run fails.
  3. Align MFA fragments (tiers.words.entries; '<eps>' and '' entries
     dropped) to chips by greedy concatenation: consume fragments
     (NFC-normalised) until their text equals the next chip. A '<unk>'
     fragment (MFA dictionary gap) consumes exactly one whole chip --
     its span is the chip's span. Any overshoot, leftover fragment,
     or leftover chip fails the run.
  4. Write the words list and a provenance sidecar (voice/script
     hashes when --voice is supplied, MFA model, merge report,
     multi-fragment groupings, <unk> resolutions).

Thai sara-am note: MFA spells it decomposed (nikhahit U+0E4D +
sara-aa U+0E32), but Python's NFC does NOT recompose that pair into
sara-am U+0E33 (composition exclusion), so it is mapped explicitly.
MFA times carry float32 noise (e.g. 16.719999); they are rounded to
milliseconds so output is stable and comparable across runs.

Usage:
  python3 renderer/mfa_to_cues.py --mfa-out mfa_out.json --script script.txt \\
      [--merge-map merge_map.json] [--tokens-cache tokens.json] \\
      [--voice voice.wav] [--mfa-model "thai_mfa (mfa align_one_hf)"] \\
      --out-words words.json --out-provenance words.provenance.json
merge_map.json format: {"newmm_merges": [{"parts": [...], "chip": str}]}
tokens cache format: {"tokens": [...]}
"""
import argparse
import hashlib
import json
import sys
import unicodedata
from datetime import date
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def nfc(s):
    return unicodedata.normalize("NFC", s).replace("\u0e4d\u0e32", "\u0e33")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--mfa-out", required=True)
    p.add_argument("--script", required=True)
    p.add_argument("--merge-map")
    p.add_argument("--tokens-cache")
    p.add_argument("--voice")
    p.add_argument("--mfa-model", default="thai_mfa (mfa align_one_hf)")
    p.add_argument("--out-words", required=True)
    p.add_argument("--out-provenance", required=True)
    a = p.parse_args(argv)

    script = Path(a.script)
    concat = "".join(script.read_text(encoding="utf-8").split())

    try:
        from pythainlp import word_tokenize
        toks = word_tokenize(concat, engine="newmm")
        tok_source = "pythainlp newmm (regenerated)"
    except ImportError:
        if not a.tokens_cache:
            raise SystemExit("FAIL: pythainlp unavailable and no --tokens-cache supplied")
        toks = json.loads(Path(a.tokens_cache).read_text(encoding="utf-8"))["tokens"]
        tok_source = f"{a.tokens_cache} (cached)"
    if "".join(toks) != concat:
        raise SystemExit("FAIL: token concatenation != script concatenation")

    merges = []
    if a.merge_map:
        merges = json.loads(Path(a.merge_map).read_text(encoding="utf-8")).get("newmm_merges", [])
    chips = []
    merge_report = []
    i = 0
    while i < len(toks):
        matched = False
        for m in merges:
            parts = m["parts"]
            if toks[i:i + len(parts)] == parts:
                chips.append(m["chip"])
                merge_report.append({"parts": parts, "chip": m["chip"]})
                i += len(parts)
                matched = True
                break
        if not matched:
            chips.append(toks[i])
            i += 1
    if "".join(chips) != concat:
        raise SystemExit("FAIL: chip concatenation != script concatenation")

    mfa = json.loads(Path(a.mfa_out).read_text(encoding="utf-8"))
    entries = mfa["tiers"]["words"]["entries"]
    frags = [(float(s), float(e), t) for s, e, t in entries if t not in ("<eps>", "")]
    words = []
    frag_groups = []
    unk_resolved = []
    fi = 0
    for chip in chips:
        if fi >= len(frags):
            raise SystemExit(f"FAIL: fragments exhausted at chip {chip!r}")
        start = frags[fi][0]
        acc = ""
        parts = []
        while True:
            if fi >= len(frags):
                raise SystemExit(f"FAIL: fragments exhausted inside chip {chip!r} (acc={acc!r})")
            s, e, t = frags[fi]
            parts.append(t)
            if t == "<unk>":
                implied = chip[len(acc):] if chip.startswith(acc) else None
                if implied is None or not implied:
                    raise SystemExit(f"FAIL: <unk> cannot complete chip {chip!r} from acc={acc!r}")
                unk_resolved.append({"chip": chip, "implied_text": implied, "start": s, "end": e})
                acc = chip
                fi += 1
                break
            acc += nfc(t)
            fi += 1
            if acc == chip:
                break
            if not chip.startswith(acc):
                raise SystemExit(f"FAIL: fragment accumulation overshoot for chip {chip!r}: acc={acc!r} from fragments {parts}")
        end = frags[fi - 1][1]
        words.append({"word": chip, "start": round(start, 3), "end": round(end, 3)})
        if len(parts) > 1:
            frag_groups.append({"parts": parts, "chip": chip, "start": start, "end": end})
    if fi != len(frags):
        raise SystemExit(f"FAIL: {len(frags) - fi} fragments left over after last chip")
    if "".join(w["word"] for w in words) != concat:
        raise SystemExit("FAIL: output word concatenation != script concatenation")
    for x, y in zip(words, words[1:]):
        if y["start"] < x["start"] or y["end"] < y["start"]:
            raise SystemExit("FAIL: word times not monotonic")

    out_words = Path(a.out_words)
    out_words.write_text(json.dumps(words, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    prov = {
        "generated": date.today().isoformat(),
        "mfa_model": a.mfa_model,
        "mfa_input": a.mfa_out,
        "token_source": tok_source,
        "newmm_tokens": len(toks),
        "chips": len(words),
        "total_chars": len(concat),
        "newmm_merges": merge_report,
        "mfa_fragment_groupings_multi": frag_groups,
        "unk_resolved": unk_resolved,
        "note": "words output stays a bare list for PoseMouthRig compatibility; this sidecar carries provenance.",
    }
    if a.voice:
        prov["voice"] = a.voice
        prov["voice_sha256"] = sha256(Path(a.voice))
    prov["script"] = a.script
    prov["script_sha256"] = sha256(script)
    Path(a.out_provenance).write_text(json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"tokens={len(toks)} chips={len(words)} chars={len(concat)}")
    print(f"newmm merges applied: {len(merge_report)}")
    print(f"multi-fragment chips: {len(frag_groups)}")
    print(f"<unk> resolved: {len(unk_resolved)}")
    print(f"wrote {out_words} and {a.out_provenance}")


if __name__ == "__main__":
    main()
