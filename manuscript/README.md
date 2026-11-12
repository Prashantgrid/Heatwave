# Actuarial digital twins for heatwave accumulation risk in European power insurance

Research draft, 12 November 2026. The study evaluates relative changes in portfolio accumulation from equipment failures and cooling-water output restrictions using a common modelled loss basis.

- [Manuscript PDF](latex/main.pdf) and [LaTeX source](latex/main.tex)
- [Europe map](latex/figures/era5_observed.pdf) and [owner–insurer workflow](latex/figures/adt_workflow.pdf)
- [ERA5-calibrated prototype and saved runs](era5_pilot/README.md)
- [PV field-validation source](field_validation/README.md)
- [Physics-based study design and handoff](../docs/claude_handoff.md)

## Reproduce the current figures and results offline

Run from the repository root. The committed inputs cover all four figures. The saved loss runs in the appendix use a real-weather-calibrated event generator and synthetic assets, vulnerability and insurance terms.

```sh
python -m pip install -r requirements.txt
python manuscript/era5_pilot/code/manuscript_figures.py
(cd manuscript/era5_pilot/data && python ../code/analyze_v3.py base heavy)
```

To compile the paper, run `latexmk -xelatex main.tex` in `manuscript/latex/`. The LaTeX build uses Nimbus Roman, Nimbus Sans and Latin Modern Math.
