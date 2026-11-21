# Corpus & word-list method

This file explains exactly how the word pools are built, so the numbers in the game are
reproducible and so you can extend the corpus with your own sources.

---

## 1. Sources

### 1.1 Primary corpus — Armenian Wikipedia plain text

* Dataset: [`ffatty/plaintext-wikipedia-full-armenian`](https://huggingface.co/datasets/ffatty/plaintext-wikipedia-full-armenian)
* Content: the full Armenian Wikipedia (hywiki) exported as plain text, ~340 000 articles,
  12 gzip files, **322 MB compressed** (≈ 1.5 GB of text).
* Language: **Eastern Armenian**, contemporary written register (spelling reform orthography).
* License: CC BY-SA 3.0 (inherited from Wikipedia).
* Why it is a good base: it is large, free, constantly updated, mostly Eastern Armenian, and
  written by many different people — so the frequency ranking is not dominated by one author.
  It also contains proper nouns (names, places), which is why a capitalisation filter matters.

Downloaded automatically by `pipeline/build_wordlist.py --download`.

### 1.2 Validator — hunspell `hy_AM`

* Package: [`dictionary-hy`](https://www.npmjs.com/package/dictionary-hy) (armspell project),
  fetched from jsDelivr: `index.dic` (67 875 stems) + `index.aff` (affix rules).
* Used through [`spylls`](https://pypi.org/project/spylls/), a pure-Python hunspell engine, so
  inflected forms such as `կարդում`, `քաղաքներում`, `անդրադարձել` are recognised as valid.
* Only the boolean answer "is this a word?" is used; the dictionary itself is not redistributed.
* Licence: GPL-2.0 / LGPL-2.1 / MPL-1.1 (tri-licensed).
* Note: the shipped `.aff` declares wrong entry counts for three affix blocks; `build_wordlist.py`
  repairs them on the fly (`_repair_aff`) — otherwise strict hunspell parsers refuse to load it.

### 1.3 Optional extra sources (drop into `corpus/` and rerun)

More corpora = better frequency ranking for everyday vocabulary (news, speech) instead of
encyclopedic vocabulary only. Anything UTF-8 works:

| Source | Where | Notes |
|---|---|---|
| Armenian news sites (news.am, tert.am, 1in.am, civilnet.am, azatutyun.am, Hetq) | article text or RSS dumps | best single upgrade for "modern everyday" frequency |
| [`Karavet/ARPA-Armenian-Paraphrase-Corpus`](https://huggingface.co/datasets/Karavet/ARPA-Armenian-Paraphrase-Corpus) | Hugging Face, 5 915 sentence pairs | news-derived paraphrases |
| [`EdUarD0110/Armenian_sentences_100000`](https://huggingface.co/datasets/EdUarD0110/Armenian_sentences_100000) | Hugging Face, 100 k sentences | general sentences |
| Armenian Wikisource / public-domain literature | dumps.wikimedia.org | literary register, older orthography in places |
| OPUS `CCMatrix` / `OpenSubtitles` hy | opus.nlpl.eu | spoken/subtitle register |
| Your own WhatsApp/Telegram export, subtitles, classroom material | — | fastest way to bias the game toward your own vocabulary |

Procedure: put the files in `corpus/`, then

```bash
python3 pipeline/build_wordlist.py --corpus-dir corpus
python3 pipeline/build_site.py
```

Because bands are **relative frequency thresholds on the merged corpus**, adding a news corpus
automatically pushes news-common words into `easy` and encyclopedic rarities into `impossible`.

---

## 2. Tokenisation: what counts as a letter

Armenian word games count two multi-character units as single letters:

* **ու** = `ո` + `ւ` — e.g. `անուն` is **4** letters: ա‑ն‑ու‑ն
* **և** = `ե` + `ւ` — e.g. `արև` is **3** letters: ա‑ր‑և

So the tile set is 38 letters + `ու` + `և` = **40 keys**:

```
ա բ գ դ ե զ է ը թ ժ ի լ խ ծ կ հ ձ ղ ճ մ յ ն շ ո չ պ ջ ռ ս վ տ ր ց ւ փ ք օ ֆ ու և
```

Punctuation inside the Armenian Unicode block (`՛ ՜ ՞ …`, U+0559–U+055F) is **not** a letter and is
excluded by the tokeniser — an early version of this pipeline produced "words" like `լո՛ւռ` until
that was fixed.

Only words of exactly 4, 5 or 6 such letters are kept.

---

## 3. Filters, in order

| # | Filter | Rejected in the shipped build |
|---|---|---|
| 1 | length (after grapheme merge) must be in `--lengths` | — |
| 2 | **proper-noun filter**: the word must occur lower-case in ≥ 50 % of its occurrences (sentence-initial capitals are tolerated) | 296 779 |
| 3 | **dictionary filter**: `hunspell hy_AM` must accept the form | 55 286 |
| 4 | **blocklist** (`pipeline/blocklist.txt`, substring match) | 7 |
| 5 | minimum occurrences (`--min-count`, default 1) | 0 |

Survivors: **29 433** words (3 696 four-letter, 9 496 five-letter, 16 241 six-letter).
They form both the answer pools and the accepted-guess dictionary.

Why filter 2 is essential: Wikipedia is full of transliterated foreign names
(`Վաշինգտոն`, `Աբադյան`, `Գյոթե`). They are capitalised in nearly every occurrence, so they drop
out, while `քաղաքի` ("of the city") survives.

---

## 4. Difficulty bands

Bands are frequency thresholds on the number of corpus occurrences, applied inside each length:

| tier | label | rule | what you get |
|---|---|---|---|
| `easy` | Դյուրին | ≥ 200 occurrences | the words you meet in every paragraph (`համար`, `մարդ`, `քաղաքի`, `կարող`) |
| `medium` | Միջին | 60 – 199 | solid everyday vocabulary, no longer top-of-mind (`բժիշկ`, `շեփոր`, `փարոսի`, `մուրաբա`) |
| `hard` | Դժվար | 12 – 59 | real but uncommon (`ջաղաց`, `ուսանողական`-type words, idioms, technical nouns) |
| `impossible` | Անհնար | 1 – 11 | one-off attestations: archaic forms, obscure compounds, dialect words, `չ-` negations |

You can move the bands with `--easy 500 --medium 150 --hard 30`, or ask for more/fewer lengths with
`--lengths 3,4,5,6,7`.

Answers are shuffled deterministically for the daily puzzle
(`hash(date · length · tier)`), so every player gets the same word for the same configuration.

---

## 5. Known limitations (and honest notes)

* **No lemmatisation.** Armenian is agglutinative; `քաղաք`, `քաղաքի`, `քաղաքում`, `քաղաքներում` are
  separate entries, exactly as they appear in text. That is fine for a Wordle (all of them are real
  words a speaker knows), but it means the `easy` band contains many inflected forms rather than
  dictionary headwords. Adding a morphological analyser (e.g. Apertium `hye`) would let you restrict
  answers to base forms — a nice future upgrade.
* **Encyclopedic bias.** Without a news/speech corpus, "everyday" leans formal: `թվական`,
  `շրջան`, `կայքում` show up early. Add a news corpus (section 1.3) to fix that.
* **Dictionary gaps.** The hunspell `hy_AM` lexicon rejects ~55 k corpus forms (neologisms, proper
  compounds, rare inflections). Some genuine rare words are therefore lost; that is the price of
  throwing away typos and transliterations. `--no-hunspell` disables the check if you prefer recall
  over precision.
* **Proper names can slip through** in borderline cases (e.g. a name that often appears lower-case).
  Add it to `pipeline/blocklist.txt`.
* **Corpus is a snapshot.** Rerun the build (or let the included GitHub Action do it weekly) to
  keep the list contemporary.

---

## 6. Attribution

If you publish a game built from `data/words.json`, please keep a visible credit such as:

> Word frequencies derived from Armenian Wikipedia (CC BY-SA 3.0). Spell-check validation by
> hunspell hy_AM (armspell).

The game footer and the help dialog already contain this.
