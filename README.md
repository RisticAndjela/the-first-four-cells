# The First Four Cells

**Forecasting time to blastocyst from the rhythm of early human embryo development**

Two embryos can reach four cells at the same hour after fertilization. One may have spent much longer at three cells. Does knowing that history improve a forecast of how many hours remain until a blastocyst is observed?

This independent machine learning project uses time-lapse annotations from Nantes University Hospital. The dataset audit below is complete. Model training and evaluation are planned.

## Dataset and local setup

Use version 3 of the *Human embryo time-lapse video dataset* by Tristan Gomez and colleagues. The first experiment uses two small archives. [Dataset on Zenodo](https://zenodo.org/records/7912264) · [Accompanying paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC9120221/)

| Download | Size | Path after extraction |
| --- | ---: | --- |
| [Developmental annotations](https://zenodo.org/records/7912264/files/embryo_dataset_annotations.tar.gz) | 53.3 kB | `data/raw/embryo_dataset_annotations/<id>_phases.csv` |
| [Frame timestamps](https://zenodo.org/records/7912264/files/embryo_dataset_time_elapsed.tar.gz) | 859.5 kB | `data/raw/embryo_dataset_time_elapsed/<id>_timeElapsed.csv` |

Run from the repository root in Bash or Git Bash.

```bash
mkdir -p data/raw
(
  set -e
  cd data/raw
  base=https://zenodo.org/records/7912264/files
  for archive in embryo_dataset_annotations embryo_dataset_time_elapsed; do
    curl --fail --location --output "$archive.tar.gz" "$base/$archive.tar.gz"
    tar -xzf "$archive.tar.gz"
  done
)
```

## Building the analysis table

Create one row per embryo. Read each headerless annotation file as `event, start_frame, end_frame`. For each event, match its start frame to the explicit `frame_index` in the same embryo’s timestamp file and read the corresponding `time` in hours. Preserve the full embryo ID, including hyphens. Frame spacing varies, so a fixed minutes-per-frame conversion would distort the measured intervals.

| Quantity | Definition in hours | Role |
| --- | --- | --- |
| Four-cell timing | `t4` | Available at the forecast point |
| Time at two cells | `t3 − t2` | Early rhythm feature |
| Time at three cells | `t4 − t3` | Early rhythm feature |
| Remaining time | `tB − t4` | Prediction target |

Use the first frame labeled `tB` for the observed blastocyst. The separate `tSB` annotation marks the start of blastocyst formation. At prediction time, use only information available by the first four-cell frame. Even the end frame of the four-cell phase comes too late.

### Cohort audit

| Filter applied to the public archives | Embryos remaining |
| --- | ---: |
| Embryos with annotation files | 704 |
| Four-cell event recorded | 649 |
| Four-cell event followed by a blastocyst event | 444 |
| All four required events recorded in order | 288 |
| All four start frames matched to strictly increasing timestamps | **287** |

For embryo `MM445-2-2`, the blastocyst annotation starts at frame 610 and the timestamp file ends at frame 565. Exclude this row from the hours-based comparison. Preserve missing events in the audit so that an unobserved three-cell stage is distinguishable from a measured short interval.

## Experiment

Fit three predictors on the same 287 embryos. Give each embryo one held-out prediction from each model using identical five-fold splits. If verified patient or treatment-cycle identifiers are available, keep related embryos in the same fold. Otherwise use seeded embryo-level splits and document that patient-level independence remains unverified.

| Predictor | Inputs | Purpose |
| --- | --- | --- |
| Training median | Median remaining time in the training fold | Reference error in hours |
| Four-cell model | `t4` | Forecast from arrival time alone |
| Rhythm model | `t4`, `t3 − t2`, `t4 − t3` | Measure the contribution of early division timing |

Start with ordinary linear regression for both fitted models. Compute mean absolute error (MAE) from pooled held-out predictions. Report the paired difference **MAE(four-cell) − MAE(rhythm)** in hours. A positive value favors the rhythm model. Report uncertainty with a paired bootstrap of held-out errors, resampling by patient or cycle if grouping is verified.

## Planned outputs

- An embryo-level analysis table with event times, derived intervals and an exclusion log.
- A reproducible Python analysis with saved fold assignments and held-out predictions.
- A results table with MAE in hours for all three predictors and the paired improvement.
- A timeline figure comparing two embryos with similar four-cell timing and different early intervals. Show the forecast cutoff and the observed blastocyst time for each.

The estimate applies to embryos with the required early annotations and an observed blastocyst in this single-center dataset. The experiment evaluates developmental timing. Implantation, pregnancy and live birth are outside its scope.
