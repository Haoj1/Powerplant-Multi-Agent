# LaTeX Report - Build Instructions

## Prerequisites

- LaTeX distribution: TeX Live (macOS: `brew install --cask mactex`) or MiKTeX
- Required packages: geometry, setspace, natbib, graphicx, booktabs, hyperref, amsmath, listings

## Compile

```bash
cd report
pdflatex main
bibtex main
pdflatex main
pdflatex main
```

Or use latexmk (if installed):

```bash
latexmk -pdf main.tex
```

## Output

- `main.pdf` — Final report

## Customize

1. **Title page**: Replace `{Your Name}` and `{Month and Year}` in `main.tex`
2. **Figures**: Place in `report/figures/` and uncomment `\includegraphics` in the document. Eval charts are in `evaluation/report/` (e.g., `01_detection_by_signal.png`)
3. **References**: Edit `references.bib` to add or modify entries

## TGS Format

- Page size: US Letter (8.5" × 11")
- Margins: 1"
- Font: 12pt Times (mathptmx)
- Body: Double-spaced
- References: Single-spaced (ieeetr style)
- Page numbers: Upper right, start at 2 (title page unnumbered)
