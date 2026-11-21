# PUBLISH.md — putting Բառախաղ on your GitHub Pages

I (the assistant) **cannot push for you**: this conversation has no GitHub connector and the
sandbox has no GitHub credentials (no token, no SSH key, no `gh` CLI). So this file contains the
exact steps to publish it yourself in ~2 minutes, plus the answer to "how do I do this without
touching files that are already in my repo".

Everything below assumes the project folder you already have:

```
armenian-wordle/
├── index.html                    ← the deployable game (self-contained, 804 KB)
├── .nojekyll                     ← hidden file, required-ish (stops Jekyll)
├── .gitignore                    ← hidden file
├── .github/workflows/rebuild-wordlist.yml   ← optional weekly corpus refresh
├── data/words.json
├── src/index.template.html
├── pipeline/build_wordlist.py
├── pipeline/build_site.py
├── pipeline/blocklist.txt
├── README.md
├── CORPUS.md
└── LICENSE
```

Choose **A** (existing repo) or **B** (new repo). Both use `git` on your own machine.

---

## A. Your repository already exists

### A1. Clone it and look at what is in it

```bash
git clone https://github.com/<your-username>/<repo>.git
cd <repo>
git status                 # must say "nothing to commit, working tree clean"
ls -la                     # note the existing files — you will not touch them
```

### A2. Copy the project in

Unzip `armenian-wordle.zip` **into a temporary folder**, then copy only the new files in:

```bash
# macOS / Linux (run from the cloned repo)
cp -R /path/to/armenian-wordle/{index.html,.nojekyll,.gitignore,data,src,pipeline,.github,README.md,CORPUS.md,LICENSE} .
```

```powershell
# Windows PowerShell (run from the cloned repo)
Copy-Item C:\path\to\armenian-wordle\index.html, C:\path\to\armenian-wordle\.nojekyll, C:\path\to\armenian-wordle\.gitignore, C:\path\to\armenian-wordle\README.md, C:\path\to\armenian-wordle\CORPUS.md, C:\path\to\armenian-wordle\LICENSE .
Copy-Item C:\path\to\armenian-wordle\data, C:\path\to\armenian-wordle\src, C:\path\to\armenian-wordle\pipeline, C:\path\to\armenian-wordle\.github -Recurse .
```

> Should the game live in a subfolder instead of the repo root (e.g. `/wordle/`)? Create the folder
> first and copy everything into it. The site URL then becomes
> `https://<user>.github.io/<repo>/wordle/`.

### A3. Check that you are only *adding*

```bash
git status
```

You should see **only** `new file:` lines. If you see `deleted:` or `modified:` for files that
belonged to the repo before, stop and re-copy more carefully — do **not** commit that.

### A4. Commit and push

```bash
git add index.html .nojekyll .gitignore data src pipeline .github README.md CORPUS.md LICENSE
git commit -m "Add Բառախաղ — Eastern Armenian Wordle (4/5/6 letters, 4 difficulty tiers)"
git push origin HEAD
```

No force-push, no `--mirror`, no branch deletion anywhere in this guide.

---

## B. You are creating a fresh repository

```bash
# 1. create an empty repo on github.com (no README, no .gitignore — keep it empty)

# 2. push the project
cd armenian-wordle
git init -b main
git add .
git commit -m "Բառախաղ — Eastern Armenian Wordle with corpus-built word list"
git remote add origin https://github.com/<your-username>/<repo>.git
git push -u origin main
```

Or with the GitHub CLI: `gh repo create <repo> --public --source=. --push`

---

## C. Enable GitHub Pages

1. Repo → **Settings** → **Pages**
2. **Source: Deploy from a branch** · **Branch: `main`** · **Folder: `/ (root)`** → **Save**
3. Wait ~30–60 s, then open `https://<your-username>.github.io/<repo>/`

`.nojekyll` is what keeps GitHub from running Jekyll over the folder (it can otherwise ignore
folders whose names start with `_`). Everything in this project is static, so the game needs no
build step on GitHub's side.

If you also pushed `.github/workflows/rebuild-wordlist.yml` and want the weekly corpus refresh to
work, enable **Settings → Actions → General → Workflow permissions → Read and write permissions**.

---

## D. If you would rather use the web UI (no git installed)

1. Open the repo → **Add file** → **Upload files**.
2. Drag in `index.html`, `README.md`, `CORPUS.md`, `LICENSE`, and the folders `data/`, `src/`,
   `pipeline/` — dragging a folder preserves its structure in Chrome/Edge/Firefox.
3. **Hidden files are skipped by drag-and-drop.** Create them by hand with
   **Add file → Create new file**:
   * `.nojekyll` — file name `.nojekyll`, leave the content empty.
   * `.gitignore` — paste the contents of `.gitignore`.
   * `.github/workflows/rebuild-wordlist.yml` — create the path by typing it in the filename box.
4. Commit message: *"Add Բառախաղ — Eastern Armenian Wordle"* → **Commit directly to the `main`
   branch** (that is the equivalent of option A4; no pull request is involved).

The web uploader only ever *adds* files, so existing files in the repo stay untouched — unless you
upload a file with the same name, which would replace it. Nothing in this project is named
`index.md`, `README.md`-with-content-you-want-to-keep, etc. **except possibly `README.md` and
`LICENSE`**: if the repo already has its own, rename ours to `README-wordle.md` before uploading.

---

## E. Common snags

| Symptom | Cause / fix |
|---|---|
| 404 at `…github.io/<repo>/` | Pages not enabled yet, or wrong folder (must be `/ (root)`), or the first deploy is still running (check the Actions tab). |
| Blank page, only the footer | A stray `index.html` from another project is at the root, or you uploaded the game into a subfolder — use the subfolder URL. |
| `git push` rejected (`non-fast-forward`) | Someone (or you, on another machine) pushed in the meantime: `git pull --rebase`, resolve, then push. Never `--force`. |
| `error: src refspec main does not match any` | You committed on a different branch name: `git branch -M main`, then push. |
| Site updated but the old game still shows | Browser/service-worker cache — hard reload, or wait a minute for the CDN. |
| Weekly rebuild Action fails on `pip install spylls` | Not needed for hosting — delete the workflow file if you don't want the automation. |

---

## F. What I could and could not do

* ✅ Built the project, verified it in a real browser (Chromium, 320–1280 px), regenerated the word
  list from scratch to prove the pipeline is reproducible.
* ✅ Packaged it: `armenian-wordle.zip` (full project, hidden files included) and
  `armenian-wordle.bundle` (a real git repository with one commit — `git clone armenian-wordle.bundle`
  gives you a ready-made repo with history).
* ❌ Could not list your repositories, pick the right one, upload files, or commit: no GitHub
  connector exists in this conversation and no credentials are available to the sandbox.
