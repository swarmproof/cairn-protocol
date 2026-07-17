# arXiv Submission Bundle — CAIRN Whitepaper

This directory contains everything needed to submit the CAIRN Protocol whitepaper to arXiv.

## Contents

| File | Purpose |
|---|---|
| `cairn-whitepaper.md` | Source document (mirror of `../../WHITEPAPER_V2.md` at submission time, with HTML `<sub>`/`<sup>` tags converted to pandoc native syntax) |
| `cairn-whitepaper.tex` | LaTeX source generated from the `.md` — arXiv-preferred upload format |
| `cairn-whitepaper.pdf` | Locally compiled PDF for visual review (BasicTeX render; arXiv renders independently) |
| `cairn-whitepaper.backup-pre-review-2026-05-11.md` | Pre-review-hardening snapshot, for revert/diff reference |
| `figures/` | 16 simulation figures (PNG) — ancillary supplementary material, not embedded in the paper. The empirical claims are carried by `§10.1` tables. See METADATA.md "Figures policy" for details. |
| `METADATA.md` | arXiv submission metadata (title, abstract, categories, license notes, checklist) |
| `README.md` | This file — build instructions and submission workflow |

## Building the submission

arXiv accepts either a PDF or LaTeX source. **LaTeX source is strongly preferred** because arXiv re-renders it, enabling search-indexable abstracts, better accessibility, and future-proofing. PDF-only submissions are permitted but second-class.

### Prerequisites (one-time install)

The conversion tooling is not currently installed on this machine. Install it:

```bash
# macOS via Homebrew
brew install pandoc
brew install --cask basictex    # minimal LaTeX — ~100 MB. For full LaTeX: brew install --cask mactex
eval "$(/usr/libexec/path_helper)"   # refresh PATH for new TeX binaries

# Verify
pandoc --version
xelatex --version
```

### Path A — Generate LaTeX source (preferred for arXiv)

**Pre-step (already applied to the snapshot in this directory):** convert raw HTML `<sup>...</sup>` and `<sub>...</sub>` tags in `cairn-whitepaper.md` to pandoc's native `^x^` / `~x~` syntax. Pandoc 3.9's `gfm` and `markdown+raw_html` readers silently drop unknown HTML inline tags, so this conversion is required for math-style super/subscripts (e.g., `F^0.80`, `F_LIVENESS`) to render correctly. The script:

```bash
python3 - <<'PY'
import re
src = open('cairn-whitepaper.md').read()
src = re.sub(r'<sup>([^<]*)</sup>', r'^\1^', src)
src = re.sub(r'<sub>([^<]*)</sub>', r'~\1~', src)
src = re.sub(r'\^([^^]*) ([^^]*)\^', r'^\1\\\\ \2^', src)
src = re.sub(r'~([^~]*) ([^~]*)~', r'~\1\\\\ \2~', src)
open('cairn-whitepaper.md', 'w').write(src)
PY
```

If you re-copy `WHITEPAPER_V2.md` from the repo root into the snapshot, re-run this conversion.

```bash
cd PUBLICATION/arxiv/

pandoc cairn-whitepaper.md \
  --from=markdown+raw_html+tex_math_dollars+pipe_tables+autolink_bare_uris+backtick_code_blocks+superscript+subscript \
  --to=latex \
  --standalone \
  --toc \
  --shift-heading-level-by=-1 \
  --metadata title="CAIRN: A Protocol for Agent Failure Detection, Classification, and Recovery in the On-Chain Agent Economy" \
  --metadata author="Maroua Boudoukha" \
  --metadata date="April 2026" \
  -V mainfont="DejaVu Serif" -V monofont="DejaVu Sans Mono" \
  -V geometry:margin=1in -V linkcolor:blue -V fontsize=10pt \
  --resource-path=. \
  --output=cairn-whitepaper.tex

# Compile locally to verify (after installing BasicTeX or MacTeX)
xelatex cairn-whitepaper.tex
xelatex cairn-whitepaper.tex    # second pass — resolves TOC and cross-refs
```

`--shift-heading-level-by=-1` ensures the markdown `## 1. Introduction` becomes `\section{}` (not `\subsection{}`). The `+superscript+subscript` extensions enable native `^x^` and `~x~` parsing.

**Upload to arXiv:** submit `cairn-whitepaper.tex` plus the `figures/` directory.

> **Note (this repo):** The `cairn-whitepaper.tex` checked into this directory is the result of running the above pipeline against the post-conversion snapshot. It is regenerated whenever `WHITEPAPER_V2.md` changes; the corresponding markdown snapshot here has the HTML-tag conversion already applied.

### Path B — Generate PDF directly (acceptable, simpler)

```bash
cd PUBLICATION/arxiv/

pandoc cairn-whitepaper.md \
  --from=gfm \
  --to=pdf \
  --pdf-engine=xelatex \
  --standalone \
  --toc \
  --metadata title="CAIRN: A Protocol for Agent Failure Detection, Classification, and Recovery in the On-Chain Agent Economy" \
  --metadata author="Maroua Boudoukha" \
  --metadata date="April 2026" \
  --resource-path=. \
  --variable=geometry:margin=1in \
  --variable=linkcolor:blue \
  --output=cairn-whitepaper.pdf
```

**Upload to arXiv:** submit `cairn-whitepaper.pdf`.

## Likely rendering issues and fixes

The whitepaper uses a few markdown constructs that need attention during conversion:

1. **Unicode math symbols** (≥, ≤, ×, σ, α, ≈, δ, etc.)
   — REQUIRES the DejaVu font variables in the pandoc command above. The default Latin Modern fonts silently DROP Greek glyphs (α, σ, δ, κ) — this is not cosmetic; the characters disappear from the rendered PDF, locally and on arXiv. The `∎` (QED) and `≫` symbols are absent even from DejaVu and have been replaced in the source with **QED.** and `>>` respectively — do not reintroduce them.

2. **Subscripts/superscripts written as `<sub>` / `<sup>` HTML tags**
   — pandoc GFM reader translates these to LaTeX `\textsubscript{}` / `\textsuperscript{}` automatically.

3. **Multi-column tables with long content**
   — Some tables (Section 10.1 experiment catalog, confusion matrix) may overflow the page width. If that happens, add this preamble:
   ```
   --include-in-header=<(echo '\usepackage{longtable}\n\usepackage{array}\n\renewcommand{\arraystretch}{1.2}')
   ```

4. **Code blocks with ASCII box-drawing characters** (Section 2.3 architecture diagram)
   — These render fine in xelatex if a monospaced Unicode font is used. Add to preamble:
   ```
   --include-in-header=<(echo '\usepackage{fontspec}\setmonofont{DejaVu Sans Mono}')
   ```
   (macOS has DejaVu Sans Mono via MacTeX; if missing, use `Menlo` or `Consolas`.)

5. **The "Note on protocol versions" blockquote after the Abstract**
   — pandoc will render as a quote block. Fine.

## Submission workflow

1. Run Path A (preferred) or Path B.
2. Open the generated PDF and visually inspect:
   - [ ] Title page includes title, author, date
   - [ ] Table of contents renders with all 11 top-level sections
   - [ ] All 16 figures appear and are legible
   - [ ] No overflowing tables (check sections 10.1, 6.5, 6.6, 3.1 especially)
   - [ ] Subscripts and Greek letters render correctly (*F*<sub>LIVENESS</sub>, σ, α, etc.)
   - [ ] No orphaned cross-references like "Section ??" or "Figure ??"
   - [ ] Code blocks for Solidity (§6.4) and ground-truth formula (§10.1) render in monospace
3. Go to https://arxiv.org/submit and create a new submission.
4. Paste metadata from `METADATA.md`.
5. Upload the `.tex` + `figures/` directory (Path A) or the `.pdf` (Path B).
6. Select license per `METADATA.md` recommendation.
7. Confirm endorsement: new arXiv contributors in `cs.DC` may need endorsement from an existing arXiv author in that category. Check the endorsement status page.
8. Submit for moderation. arXiv moderation queue is typically 1–3 business days.

## Cross-references between the paper and this repo

The paper's Reference [18] points readers back to:
```
simulation/                    # source code + results
simulation/RESULTS.md          # Run 1
simulation/RESULTS_EQ2.md      # Run 2
simulation/RESULTS_EQ3.md      # Run 3
simulation/RESULTS_EQ4.md      # Run 4
simulation/figures/fig1..fig16 # all figures
```

These files are in the parent repository (`github.com/MarouaBoud/cairn-protocol`) and should be preserved public alongside the arXiv submission for reproducibility.

## After submission

- arXiv will assign a preprint ID (e.g., `arXiv:2604.NNNNN`).
- Update the repository's README with the arXiv link.
- Announce via usual channels (X, LinkedIn, relevant Discord/Telegram communities).
- When the v2 contract is implemented and benchmarked (see PRD-04-V2-UPGRADE), submit a **v2** revision to arXiv with the measured gas numbers in Section 6.5, along with any reviewer feedback incorporated.
