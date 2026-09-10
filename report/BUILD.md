# Build the Final Report

Run from this directory with XeLaTeX:

```bash
mkdir -p build
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
xelatex -interaction=nonstopmode -halt-on-error -output-directory=build main.tex
```

The stabilized output is `build/main.pdf`.

The source uses `fontspec` and selects the first installed font in this fallback
order: Times New Roman, Tinos, then TeX Gyre Termes. No absolute font path is
required.

All required figures and the official cover are contained in `assets/`.
Figure 2.1 is supplied as a grayscale vector PDF. Figures 3.1 and 3.2 also have
editable TikZ sources in `assets/`; regenerate them only if those figure sources
are intentionally changed.

The PDF included at the package root is the canonical final report built from
these sources. Generated build files are not required for an independent rebuild.
