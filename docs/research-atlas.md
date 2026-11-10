# Research atlas · data, models, and results

## What is actually available

Each of the 704 identifiers in this project has one annotation file and one
timestamp file. The archive contains doubly nested directories; the reader
locates that layout or the standard `data/raw/` layout. If it finds two copies,
it requires an unambiguous path. In total, there are 310,894 unique
embryo–frame-index pairs and 8,461 annotated intervals. These are frame
timestamps. Images for those frames must be obtained separately.

| Source | Contents | Purpose |
| --- | --- | --- |
| 704 × `*_phases.csv` | Stage, first and last included frame | Transitions, reference phases, and outcomes |
| 704 × `*_timeElapsed.csv` | Frame index and hour | Joining to intervals, recording schedule, and available follow-up |
| `data/processed/cohort.csv` | 287 complete cases, one row per embryo | Initial early-rhythm study |
| `data/processed/exclusions.csv` | 417 exclusions from the initial study | Exclusion reason and selection analysis |
| `data/external/embryo_dataset_grades.csv` | Supplement from the same release, TE and ICM | Two separate morphological outcomes; retain `NA` |
| `runs/baseline` and `results/reference` | Predictions and metrics from two environment versions | Reproduction and comparison. Same seed, folds, and cohort hash; maximum prediction difference below 3 × 10⁻¹⁴ h |
| `__pycache__`, `*.pyc`, `*.egg-info/` | Local execution and installation artifacts | Regenerable and ignored by Git |
| `reports/embryo-explorer.html` | Generated visualisation | Retain for demonstration; the template controls future generation |

There are six annotation starts without a timestamp for the corresponding frame
and seven such ends. No embryo has duplicate frame indices. There are 1,300
successive pairs with the same recorded time; time never moves backward in the
supplied files. The interval code therefore requires strictly increasing start
hours. The last frame of one phase measures the final labelled observation in
that phase; the start of the next phase measures the next recorded transition.
Annotations are retrospective.

## Implementation map

Run all commands from the repository root. The shared form is
`python -m first_four_cells.cli research FAMILY --output runs/new-name`. The
package lives in `src/first_four_cells/analyses`. The shared loader is in
`events/`; `forecasting/` shares logic for two forecast types. The existing
baseline-experiment and explorer commands remain available.

| FAMILY | Data, unit, and outcome | Method and interpretation |
| --- | --- | --- |
| audit | All 704 recordings; table by identifier | Frame count, time step, largest timestamp gap, duplicates, missing links, and follow-up duration |
| trajectories | All labels and 120 ordered start/later-target combinations | Long-format ledger, stage coverage, medians and quartiles, 244 distinct recorded paths, and adjacent annotated transitions |
| sequences | Next recorded label for sequences with a known continuation | Training prevalence versus logistic regression from prior rhythm; OOF accuracy and macro-F1 for 12 starting stages |
| landmarks | Every pair with at least 50 usable durations; 105 forecast pairs in total | Ridge using only the current hour versus Ridge using preceding history; every individual prediction is available |
| benchmark | The same 287 embryos and outer folds as the baseline experiment | Median, OLS, Ridge, Huber, additive spline, Extra Trees, histogram gradient boosting, and a small MLP. MAE, RMSE, bias, paired differences, and quantile regressions for individual ranges |
| phenotypes | Early timing data, comparison of included and remaining embryos | Robust scaling, K-means for k=2…5, silhouette, stability over 20 subsamples, group medians, and extreme-rhythm ranks |
| observation | 649 embryos with known t4 time; target is whether tB is recorded after t4 | Training prevalence and logistic regression; ROC-AUC, average precision, Brier score, and available follow-up |
| grades | Separate TE and ICM grades among embryos labelled with t4 | Majority class and balanced logistic regression; balanced accuracy, confusion matrices, and predictions |
| images | First t4 frame on the central plane, verified image-row pairs only | Optional frozen ImageNet ResNet-18 + Ridge module; timing, image, and both inputs; paired difference in hours |

The threshold of 50 is a practical choice for this exploration.
`pair_support.csv` also provides case counts for all 15 remaining pairs. All 15
end in hatching (`tHB`), for which only five annotations exist. No model has a
sufficient basis for a general conclusion about hatching from those five cases.

## How to read the results

- **Initial experiment.** Three inputs at t4 and the same 287 embryos. MAE for
  the linear rhythm model is 8.080 h, Ridge 8.077 h, Huber 8.038 h, Extra Trees
  8.079 h, boosting 8.102 h, and spline 7.759 h. The training median gives
  8.197 h. The estimated spline gain over OLS is 0.321 h, with a paired 95%
  interval from −0.083 to 0.722 h. Models use fixed parameters. This is an
  exploratory comparison of multiple candidates on the same sample; a new,
  independent dataset is required to confirm a selected candidate. Nested
  validation was also run: within each of five outer training sets, three inner
  folds choose a model solely by MAE. In every numerical comparison, each test
  embryo has exactly one prediction per model. The small MLP has MAE 8.407 h;
  the full model-selection procedure has MAE 8.030 h. Fold-level selection is
  in `inner_selection.csv`.
- **Broader cohort.** Of 444 recordings with t4 followed by tB, 442 have both
  corresponding timestamps with a positive interval. The median from t4 to tB
  is 70.0 h. On those 442 embryos, matched clock/history Ridge models give
  7.989 and 7.861 h. The cohort, inputs, and treatment of incomplete data differ
  from the 287-embryo experiment.
- **Individual forecast uncertainty.** Gradient boosting fit to the 0.1 and
  0.9 quantiles gives achieved OOF coverage of 76.3% and mean width of 23.68 h
  at the nominal 80%. This range describes an individual duration. The bootstrap
  interval for MAE describes uncertainty in the difference between models.
- **Two rhythm groups.** When k=2 is set in advance, the groups contain 247 and
  40 embryos. Median three-cell-stage durations are 1.0 and 10.1 h. Clusters
  and extreme examples support video selection for visual inspection; clinical
  interpretation requires separate evidence.
- **Annotation presence.** After t4, there are 444 positive tB records among
  649 recordings. The logistic model gives ROC-AUC 0.526. Recording termination,
  absent annotation, and biological arrest can have different meanings. The
  `unresolved` status retains that uncertainty.
- **Grades.** TE denotes trophectoderm and ICM the inner cell mass. The added
  CSV contains 196 known TE and 160 ICM grades, including only 15 and 8 C grades
  respectively. Requiring known t4 leaves 187 and 151 cases. Balanced logistic
  regression gives balanced accuracy of 0.328 and 0.425 against a 0.333
  reference. Interpret rare-class results with the confusion matrix.
- **Preventing information leakage.** At t4, the model sees only that hour and
  available earlier starts. tB, the end of t4, total recording duration, future
  annotation count, and final grades remain outside the inputs. Medians,
  missing-value indicators, and scaling are learned in training data. For
  multiple pairs, every clock/history comparison uses the same cases and folds
  for that pair. Comparing MAE across different pairs also changes task
  difficulty and cohort composition.
- **Independence.** The same embryo remains in one fold within a task. A patient
  or cycle ID is not documented in the upload. If verified mapping is obtained,
  use `--groups path.csv` with `embryo_id,group_id` columns for all included
  embryos. Intervals are conditional on predictions from those folds. The share
  of selected recordings cannot be transferred directly to another clinic.

## Extensions for missing data

**Central plane.** Download `embryo_dataset.tar.gz`, run `image-manifest`,
install the optional package, and run the matched ablation. On first use,
torchvision downloads the named ImageNet weights. The supplied project has no
images. The visual-model implementation awaits end-to-end verification on real
images.

```shell
python -m pip install -e ".[vision]"
python -m first_four_cells.cli image-manifest
python -m first_four_cells.cli research images --manifest data/processed/t4_image_manifest.csv --output runs/image-v1
```

**Full video and all seven planes.** The command below initialises an index of
plane, frame, image, and phase for every actually available plane. It retains an
empty label before the first labelled frame and in gaps. All planes and frames
for the same embryo must use the same split. The full video may be used for
offline stage identification. To forecast a future event, treat every video as
a prefix up to a predefined cutoff.

```shell
python -m first_four_cells.analyses.imaging.frame_index --image-root data/raw
```

| Research direction | Required data | First comparable experiment |
| --- | --- | --- |
| Recognition of the current stage | Images and an index of labelled frames | Timing as the baseline, frame-level CNN, then a temporal model; Macro-F1 and phase-start error in hours |
| Video dynamics and earlier t2/t3/t4 cutoffs | Images for every early event or short histories | Final frame versus a short sequence; pooling or temporal convolution, then GRU; measure gain on the same embryos |
| Focus robustness | Align the same `embryo_id` and RUN across available planes | Central plane versus the best estimated sharpness or aggregation over multiple planes; analysis by plane |
| Visual similarity and extreme cases | Images and frozen embeddings | Nearest neighbours from another embryo, blinded pair review; control lighting, device, and focus |
| Self-supervised learning | Recordings and local development splits | Representations learned from training embryos only versus external weights; verify that an external medical checkpoint has not seen evaluation embryos |
| Visual TE/ICM assessment | Validated grades and images at a predefined time | Ordinal model versus majority and logistic baselines; early grade forecasting and grading an already visible blastocyst are different tasks |
| Segmentation, individual-cell tracking, fragmentation | Masks, tracks, or specially verified labels | Annotate an evaluation sample and measure Dice, count error, or tracking quality |
| Survival and competing risks | Reliable time of last review, reason for termination, and outcome adjudication | Create a verified event table from `follow_up.csv`; only then use Kaplan–Meier, Cox/AFT, or discrete hazards after checking assumptions |
| Implantation, pregnancy, and live birth | Linked transfer and outcome data with the correct analysis unit | Separate cohort, rules for multiple transfers, and independent validation |
| Transfer across clinics and subgroups | Another clinic or verified patient, device, and temporal metadata | Grouped and temporal splits, errors by group, calibration, and external validation |

These directions form a map for subsequent work. The delivered results cover
tabular packages. The image index and ResNet command are prepared for the next
phase. The optimal method depends on the goal and the verification approach.

## Supplement provenance

Gomez et al., _Human embryo time-lapse video dataset_, Zenodo v3:
https://doi.org/10.5281/zenodo.7912264. The original
`embryo_dataset_grades.csv` from that release was added, MD5
`25eca34656454d3cfc6d8c59305b200e`. Existing sources from the user project
were not repackaged.

## Development sequence

1. Open `stage_coverage`, `pair_support`, and `benchmark_metrics`. Always record
   the population and forecast time before selecting a model.
2. The priority for new images is a prospectively defined pair of t4 experiments:
   the same embryos, exactly the same splits, and the same regressor type; only
   the image is added. Separate the processing-selection pilot from the final
   sample. Verify the frame and focus before comparison.
3. For appearance and rhythm at several different stages, repeat the comparison
   on a shared cohort. Choose the primary metric in advance for point forecasts;
   measure coverage and width for individual intervals.
4. Before claiming applicability beyond this dataset, obtain verified cycle
   identifiers, data on why recording ended, and an independent dataset with
   the same outcome definitions.
