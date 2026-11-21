#!/usr/bin/env python3
"""
build_wordlist.py — Eastern Armenian word list generator for «Բառախաղ».

Pipeline
--------
1. CORPUS   : plain-text Eastern Armenian corpus (default: Armenian Wikipedia,
              ~340k articles, 322 MB gzipped). Any UTF-8 text / .txt.gz / CSV
              files you drop into --corpus-dir are counted too.
2. VALIDATE : every candidate is checked against a real hunspell hy_AM
              dictionary (dictionary-hy), so transliterated foreign names,
              typos and OCR garbage are dropped.
3. FILTER   : drop proper nouns (a word must occur mostly lower-case in
              running text), drop tokens that are not 4/5/6 graphemes long.
4. TIER     : split each length into easy / medium / hard / impossible bands
              by corpus frequency.
5. OUTPUT   : data/words.json  (pools per length+tier, plus the full guess
              dictionary).

Usage
-----
    python3 pipeline/build_wordlist.py                # uses ./corpus, downloads if empty
    python3 pipeline/build_wordlist.py --download     # force (re)download corpus
    python3 pipeline/build_wordlist.py --corpus-dir news/   # your own corpus folder
    python3 pipeline/build_wordlist.py --lengths 4,5,6,7 --easy 500 --medium 300 ...

Requirements: pip install spylls
Corpus license: see CORPUS.md
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import re
import sys
import time
import urllib.request
from collections import defaultdict

# --------------------------------------------------------------------------
# Armenian graphemes
# --------------------------------------------------------------------------
# U+0531–U+0556 upper, U+0561–U+0586 lower, U+0587 = և (ligature).
# NOTE: U+0559–U+055F are Armenian punctuation (՛ ՜ ՞ …) and must NOT be
# treated as letters, even though they sit inside the alphabet code block.
LETTER_RE = re.compile(r"[\u0531-\u0556\u0561-\u0586\u0587]+")


def graphemes(word: str) -> list[str]:
    """Split a word into tiles. ու (ո+ւ) and և count as ONE letter."""
    usable = word.replace("եւ", "և")          # decomposed ligature → և
    tiles, i = [], 0
    while i < len(usable):
        if usable[i] == "ո" and i + 1 < len(usable) and usable[i + 1] == "ւ":
            tiles.append("ու")
            i += 2
        else:
            tiles.append(usable[i])
            i += 1
    return tiles


def normalize(word: str) -> str:
    return word.replace("եւ", "և").lower()


# --------------------------------------------------------------------------
# Corpus download (Armenian Wikipedia plain text on Hugging Face)
# --------------------------------------------------------------------------
HF_BASE = ("https://huggingface.co/datasets/ffatty/"
           "plaintext-wikipedia-full-armenian/resolve/main/data")


def wiki_files() -> list[str]:
    files = []
    for part in ("01", "02", "03", "04"):
        for sub in ("01", "02", "03"):
            files.append(f"hywiki_{part}_of_05_part{sub}_of_03.txt.gz")
    return files


def download_corpus(dest: str) -> None:
    os.makedirs(dest, exist_ok=True)
    for name in wiki_files():
        path = os.path.join(dest, name)
        if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
            continue
        url = f"{HF_BASE}/{name}"
        print(f"  ↓ {name}", flush=True)
        tmp = path + ".part"
        urllib.request.urlretrieve(url, tmp)
        if os.path.getsize(tmp) < 100_000:      # an LFS pointer, not the file
            os.remove(tmp)
            print(f"    ! skipped {name} (placeholder file)")
            continue
        os.replace(tmp, path)


def iter_corpus_lines(corpus_dir: str):
    """Yield raw text lines from every .txt / .txt.gz / .csv file we find."""
    patterns = ["*.txt", "*.txt.gz", "*.csv", "*.tsv", "*.jsonl"]
    paths = sorted(p for pat in patterns for p in glob.glob(os.path.join(corpus_dir, pat)))
    if not paths:
        sys.exit(f"No corpus files (*.txt, *.txt.gz, *.csv) in {corpus_dir!r}")
    for path in paths:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt", encoding="utf-8", errors="ignore") as fh:
            yield from fh


# --------------------------------------------------------------------------
# hunspell validator (dictionary-hy → hy_AM.dic / hy_AM.aff)
# --------------------------------------------------------------------------
DIC_URL = "https://cdn.jsdelivr.net/npm/dictionary-hy/index.dic"
AFF_URL = "https://cdn.jsdelivr.net/npm/dictionary-hy/index.aff"


def _repair_aff(text: str) -> str:
    """Some hy_AM.aff blocks declare a wrong entry count, which breaks strict
    parsers. Rewrite every SFX/PFX block header with its true body size."""
    lines = text.splitlines()
    out, i = [], 0

    def is_header(fields: list[str]) -> bool:
        return (len(fields) == 4 and fields[0] in ("SFX", "PFX")
                and fields[2] in ("Y", "N") and fields[3].lstrip("-").isdigit())

    while i < len(lines):
        fields = lines[i].split("\t")
        if is_header(fields):
            kind, flag = fields[0], fields[1]
            body, j = [], i + 1
            while j < len(lines):
                nxt = lines[j].split("\t")
                if is_header(nxt) or not lines[j].startswith(kind) or nxt[1] != flag:
                    break
                body.append(lines[j])
                j += 1
            out.append("\t".join([kind, flag, fields[2], str(len(body))]))
            out.extend(body)
            i = j
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out) + "\n"


def get_validator(cache_dir: str):
    try:
        from spylls.hunspell import Dictionary
    except ImportError:
        sys.exit("Missing dependency:  pip install spylls")

    os.makedirs(cache_dir, exist_ok=True)
    dic = os.path.join(cache_dir, "hy.dic")
    aff = os.path.join(cache_dir, "hy.aff")
    if not os.path.exists(dic):
        print("  ↓ hy_AM dictionary", flush=True)
        urllib.request.urlretrieve(DIC_URL, dic)
        raw = urllib.request.urlopen(AFF_URL, timeout=60).read().decode("utf-8", "ignore")
        with open(aff, "w", encoding="utf-8") as fh:
            fh.write(_repair_aff(raw))
    d = Dictionary.from_files(os.path.join(cache_dir, "hy"))
    memo: dict[str, bool] = {}

    def valid(word: str) -> bool:
        hit = memo.get(word)
        if hit is None:
            hit = memo[word] = bool(d.lookup(word))
        return hit

    return valid


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-dir", default="corpus")
    ap.add_argument("--download", action="store_true",
                    help="force download of the default Wikipedia corpus")
    ap.add_argument("--cache-dir", default=".cache")
    ap.add_argument("--out", default="data/words.json")
    ap.add_argument("--lengths", default="4,5,6")
    ap.add_argument("--min-count", type=int, default=1,
                    help="minimum corpus occurrences for a word to be usable")
    ap.add_argument("--lower-ratio", type=float, default=0.5,
                    help="share of occurrences written lower-case (proper-noun filter)")
    ap.add_argument("--easy", type=int, default=200, help="easy band: count >= N")
    ap.add_argument("--medium", type=int, default=60, help="medium band: count >= N")
    ap.add_argument("--hard", type=int, default=12, help="hard band: count >= N")
    ap.add_argument("--no-hunspell", action="store_true",
                    help="skip dictionary validation (faster, noisier)")
    ap.add_argument("--blocklist", default=os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "blocklist.txt"),
                    help="file with substrings to exclude (offensive words etc.)")
    args = ap.parse_args()

    lengths = tuple(sorted({int(x) for x in args.lengths.split(",") if x.strip()}))
    t0 = time.time()

    if args.download or not glob.glob(os.path.join(args.corpus_dir, "*.txt*")):
        print("Corpus: downloading Armenian Wikipedia …")
        download_corpus(args.corpus_dir)

    valid = (lambda w: True) if args.no_hunspell else get_validator(args.cache_dir)

    blocked = []
    if args.blocklist and os.path.exists(args.blocklist):
        with open(args.blocklist, encoding="utf-8") as fh:
            blocked = [ln.strip() for ln in fh
                       if ln.strip() and not ln.startswith("#")]

    def is_blocked(word: str) -> bool:
        return any(b in word for b in blocked)

    print("Counting…")
    total = defaultdict(int)      # word -> occurrences
    lower = defaultdict(int)      # word -> occurrences written lower-case
    tokens = 0
    for n, line in enumerate(iter_corpus_lines(args.corpus_dir), 1):
        for raw in LETTER_RE.findall(line):
            if not 4 <= len(raw) <= 8:
                continue
            tiles = graphemes(raw)
            if len(tiles) not in lengths:
                continue
            w = normalize(raw)
            total[w] += 1
            tokens += 1
            if raw[0] == raw[0].lower() and raw[0] != raw[0].upper():
                lower[w] += 1
        if n % 500_000 == 0:
            print(f"  {n:,} lines · {len(total):,} candidates · {time.time()-t0:.0f}s",
                  flush=True)

    print(f"Scored {tokens:,} tokens, {len(total):,} distinct candidates "
          f"in {time.time()-t0:.0f}s")

    # ---------------- filter + tier ----------------
    pools: dict[int, dict[str, list[str]]] = {
        L: {"easy": [], "medium": [], "hard": [], "impossible": []} for L in lengths
    }
    guesses: dict[int, list[str]] = {L: [] for L in lengths}
    dropped = defaultdict(int)

    for w, c in total.items():
        L = len(graphemes(w))
        if L not in pools:
            continue
        if lower[w] / c < args.lower_ratio:
            dropped["proper noun / capitalised"] += 1
            continue
        if c < args.min_count:
            dropped["too rare"] += 1
            continue
        if not valid(w):
            dropped["not in hy_AM dictionary"] += 1
            continue
        if is_blocked(w):
            dropped["blocklisted"] += 1
            continue
        guesses[L].append(w)
        if c >= args.easy:
            pools[L]["easy"].append(w)
        elif c >= args.medium:
            pools[L]["medium"].append(w)
        elif c >= args.hard:
            pools[L]["hard"].append(w)
        else:
            pools[L]["impossible"].append(w)

    def freq_key(w: str) -> int:
        return -total[w]

    out_words: dict[str, dict[str, list[str]]] = {}
    for L in lengths:
        for tier in pools[L]:
            # within a tier, easiest first (helps deterministic "daily" picks
            # and lets you swap bands by editing --easy/--medium/--hard)
            pools[L][tier].sort(key=freq_key)
        out_words[str(L)] = {t: pools[L][t] for t in ("easy", "medium", "hard", "impossible")}
        guesses[L].sort(key=freq_key)

    data = {
        "meta": {
            "corpus": "Armenian Wikipedia plain text (hywiki, ~340k articles, CC BY-SA 3.0)",
            "tokens_scored": tokens,
            "candidates": len(total),
            "validator": "hunspell hy_AM (dictionary-hy 0.20, GPL/LGPL/MPL)",
            "min_count": args.min_count,
            "lower_ratio": args.lower_ratio,
            "bands": {"easy_min": args.easy, "medium_min": args.medium,
                      "hard_min": args.hard, "impossible_min": args.min_count},
            "lengths": list(lengths),
            "generated": time.strftime("%Y-%m-%d"),
        },
        "words": out_words,
        "dictionary": {str(L): " ".join(guesses[L]) for L in lengths},
    }

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))

    size_kb = os.path.getsize(args.out) / 1024
    print(f"\nDropped: {dict(dropped)}")
    for L in lengths:
        g = data["words"][str(L)]
        print(f"  {L} tiles: easy {len(g['easy']):>5} · medium {len(g['medium']):>5} · "
              f"hard {len(g['hard']):>5} · impossible {len(g['impossible']):>5} "
              f"· guess dictionary {len(guesses[L]):>6}")
    print(f"\nWrote {args.out} ({size_kb:,.0f} KB) in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
