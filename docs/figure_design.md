# Figure design and placement

The design starts with the comparison the reader needs to see. Consistent colours, typography and whitespace support that comparison. They cannot compensate for an unclear endpoint or an unfair comparator.

For a useful journal example, Dottori et al., *Cost-effective adaptation strategies to rising river flood risk in Europe* (Nature Climate Change, 2023), separate damage, exposed population and benefit-cost ratio into distinct panels in Figure 1. Their geographic variation is addressed separately. The transferable principle is to separate the questions “where?”, “how much?” and “at what cost?” rather than make one map answer all three. [Article and figures](https://www.nature.com/articles/s41558-022-01540-0).

| Reader's question | Proposed graphic | Design choice |
|---|---|---|
| Where are the sampled real assets? | `fig1_real_inventory` | Quiet country outlines, ten named locations and direct labels; the source-capacity bar chart is removed |
| When do sampled locations experience hot spells together? | `fig2_historical_heat_spells` | Five calendar strips, a common 0-10-plant scale and a peak-count column; the individual-site detail remains in the CSVs |
| What changes at equal action spending? | `results_equal_budget` | Two aligned paired-dot panels, showing all ten books and the contrast between mean and tail loss |
| Is funding closer to the intended target? | `results_funding` | Book-level dots, median diamonds, explicit zero-error and 0.5% reference lines; owner operation held fixed |
| Where does operating adaptation stop being effective? | `results_heat_severity` | A binned net-effect curve with the event count below it, including rare extremes |
| What do the selected extremes look like? | `supplementary_event_maps` | Two matched map extents and a shared anomaly scale; the absence of avoided failures is retained |

Teal consistently represents condition-informed operation or evidence; grey represents the class comparator. Warm colours encode temperature exposure. The original v2 models call their full-evidence setting `lam=1`; that is a likelihood-tempering setting, not a unit coefficient in a linear credibility blend.

The results show actual synthetic-book points. Their spread is not relabelled as a confidence interval. The severity plot uses no fitted smooth curve, and its four-event overflow group stays visible. Raster fields are exported at 400 dpi; text and marks remain vector elements where applicable. Fonts are specified at publication size, with no 3D effects, decorative cards or unnecessary chart borders.

The proposed files are six separate graphics, but that is not a recommendation to put all six in the main paper. The two real-data diagnostics establish an extraction pilot; the selected synthetic-event maps are better placed in supplementary material. A final main-text sequence still needs empirical engineering validation and actual climate-projection results. Numbering should be assigned only when the manuscript is available.
