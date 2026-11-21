#!/usr/bin/env python3
"""
build_site.py — inject data/words.json into src/index.template.html and write
a single self-contained index.html that you can drop straight into a GitHub
Pages repo (no server, no fetch(), works from file:// too).

    python3 pipeline/build_site.py
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    data_path = os.path.join(ROOT, "data", "words.json")
    tpl_path = os.path.join(ROOT, "src", "index.template.html")
    out_path = os.path.join(ROOT, "index.html")

    if not os.path.exists(data_path):
        sys.exit("data/words.json not found — run pipeline/build_wordlist.py first")

    with open(data_path, encoding="utf-8") as fh:
        data = json.load(fh)
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()

    # Words that are guessable but belong to no answer pool (only present when
    # the build used a looser dictionary threshold). Usually empty.
    pools = set()
    for length, tiers in data["words"].items():
        for words in tiers.values():
            pools.update(words)
    extra = {}
    for length, blob in data.get("dictionary", {}).items():
        rest = [w for w in blob.split(" ") if w and w not in pools]
        if rest:
            extra[length] = " ".join(rest)
    data["dictionary_extra"] = extra

    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/")          # never break out of <script>
    html = tpl.replace("/*__DATA__*/ null /*__END_DATA__*/", blob)

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    kb = os.path.getsize(out_path) / 1024
    n = sum(len(v) for tiers in data["words"].values() for v in tiers.values())
    print(f"index.html written — {kb:,.0f} KB · {n:,} answer words · "
          f"{len(extra)} extra guess words")


if __name__ == "__main__":
    main()
