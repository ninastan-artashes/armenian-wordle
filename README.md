# Բառախաղ · Eastern Armenian Wordle

A Wordle clone for **Eastern Armenian (արևելահայերեն)** that you can host on GitHub Pages in
one file. Word length (4 / 5 / 6 letters) and difficulty (easy → impossible) are switchable, and
the word list is **generated from a real modern Eastern Armenian corpus** instead of being
hand-typed.

```
index.html          ← the whole game, self-contained. Upload this and you are done.
```

---

## 1. Deploying on GitHub Pages (2 minutes)

1. Create a repository, e.g. `armenian-wordle`.
2. Upload **`index.html`** (and `.nojekyll`, which just stops GitHub from running Jekyll).
3. Repo → **Settings → Pages → Source: Deploy from a branch → Branch: `main` / `(root)`** → Save.
4. Open `https://<your-username>.github.io/armenian-wordle/`.

> **Publishing help:** see **[PUBLISH.md](PUBLISH.md)** for the exact `git` commands, the
> hidden-file caveat of the GitHub web uploader, and how to add this to a repo that already
> contains other files without touching them.

No build step, no server, no API keys. `index.html` also works when opened directly from disk
(`file://`), because every word is embedded in the file — there is no `fetch()`.

To use a custom domain, add a `CNAME` file with your domain in the repo root.

---

## 2. What the game does

| Feature | Detail |
|---|---|
| **Length** | 4, 5 or 6 **letters** — where `ու` and `և` count as one letter, as in Armenian letter-counting |
| **Difficulty** | `Դյուրին` easy · `Միջին` medium · `Դժվար` hard · `Անհնար` impossible — bands of corpus frequency |
| **Modes** | `Այսօրվա` daily (same word for everyone, one board per length+tier) and `Ազատ` endless practice |
| **Keyboard** | 40 keys in Armenian alphabetical order (38 letters + `ու` + `և`); real Armenian keyboard layouts also work, because typing `ո` then `ւ` merges into one `ու` tile (same for `ե`+`ւ` → `և`) |
| **Colors** | standard Wordle rules, with correct handling of repeated letters |
| **Extras** | result grid sharing (🟩🟨⬛), per-configuration statistics in `localStorage`, hard-refresh recovery of today's board, dark/light theme, Armenian ↔ English interface, Wiktionary link for the answer |
| **Dictionary check** | on by default (only corpora-attested words are accepted); switchable off in Settings |

Word counts shipped in this build:

| length | easy | medium | hard | impossible | total |
|---|---|---|---|---|---|
| 4 | 1,030 | 515 | 739 | 1,412 | **3,696** |
| 5 | 1,828 | 1,201 | 2,102 | 4,365 | **9,496** |
| 6 | 2,326 | 1,792 | 3,428 | 8,695 | **16,241** |

---

## 3. Where the words come from

The word list is **not** hand-written. It is derived from a modern Eastern Armenian corpus:

```
Armenian Wikipedia plain text (hywiki, ~340k articles, 322 MB gzipped)
        │  tokenise into Armenian graphemes (ու / և = one tile)
        ▼
  23,988,247 word tokens (382,102 distinct 4–6 letter candidates)
        │  drop proper nouns  →  a word must appear mostly lower-case in running text
        │  drop hapax noise  →  hunspell hy_AM spell-check validation
        │  drop 4/5/6-letter only, apply blocklist
        ▼
  29,433 validated words → split into 4 frequency bands per length
        ▼
  data/words.json  →  inlined into index.html
```

Details, sources and licensing: **[CORPUS.md](CORPUS.md)**.

---

## 4. Regenerating / extending the word list

```bash
pip install spylls                     # pure-python hunspell (only dependency)

# rebuild everything from the default Wikipedia corpus (downloads ~320 MB the first time)
python3 pipeline/build_wordlist.py --download
python3 pipeline/build_site.py         # writes index.html

# cheaper run: keep an existing corpus folder, skip re-download
python3 pipeline/build_wordlist.py --corpus-dir corpus
```

`build_wordlist.py` options that matter:

| flag | meaning | default |
|---|---|---|
| `--corpus-dir DIR` | folder with `.txt`, `.txt.gz`, `.csv`, `.tsv`, `.jsonl` — **all** files are counted together, so you can mix Wikipedia + news + subtitles | `corpus` |
| `--lengths 4,5,6` | which word lengths to emit | `4,5,6` |
| `--easy / --medium / --hard N` | minimum corpus occurrences for each band | `200 / 60 / 12` |
| `--min-count N` | minimum occurrences to be usable at all (also the `impossible` floor) | `1` |
| `--lower-ratio 0.5` | share of occurrences that must be lower-case (proper-noun filter) | `0.5` |
| `--blocklist FILE` | words/substrings to exclude (default `pipeline/blocklist.txt`) | — |
| `--no-hunspell` | skip spell-check validation (faster, noisier) | off |

### Adding a corpus of your own

Drop any UTF-8 text into `corpus/` — one file or a hundred, plain or gzipped — and rerun. Armenian
news sites, your own subtitles, books, chat exports all work, because the pipeline only needs raw
text. Mixing sources shifts the frequency bands, i.e. a word that is rare in an encyclopedia but
everyday in news properly lands in `easy`.

A weekly GitHub Action that regenerates and commits the lists is included in
`.github/workflows/rebuild-wordlist.yml` (delete it if you don't want it).

---

## 5. Project structure

```
index.html                       generated, self-contained game (this is what you deploy)
src/index.template.html          the game: HTML + CSS + JS, data injected at the marker
data/words.json                  tiered word pools + guess dictionary + metadata
pipeline/build_wordlist.py       corpus → filtered, tiered word list
pipeline/build_site.py           words.json + template → index.html
pipeline/blocklist.txt           words you never want to see (edit freely)
.github/workflows/rebuild…yml    optional scheduled rebuild
CORPUS.md                        corpus sources, method, licensing
```

`data/words.json` schema (also handy if you want to build your own front-end):

```jsonc
{
  "meta":  { "corpus": "…", "tokens_scored": 23988247, "bands": {…}, "lengths": [4,5,6] },
  "words": { "5": { "easy": ["համար", "որպես", …], "medium": […], "hard": […], "impossible": […] } },
  "dictionary": { "5": "համար որպես …" }   // every accepted guess, space separated
}
```

`window.HYWORDLE` exposes the live state (`S`, `cfg`, `POOLS`, `addLetter`, `submit`, …) for
debugging in the console or for writing tests.

---

## 6. Credits & licensing

* Code: MIT — do whatever you like with it.
* Word frequencies: derived from **Armenian Wikipedia** (CC BY-SA 3.0). A frequency list of
  individual word forms is generally treated as non-copyrightable data, but the polite thing is to
  keep the attribution line that is already in the game footer / help screen.
* Spell-check validation: **hunspell `hy_AM`** from the [dictionary-hy](https://www.npmjs.com/package/dictionary-hy)
  package (armspell), tri-licensed GPL-2.0 / LGPL-2.1 / MPL-1.1. Only a boolean validation result
  is used — no dictionary content is redistributed beyond the words that already occur in the corpus.

Made for Armenian speakers, learners and the diaspora-wordle-industrial complex.
