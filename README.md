# The First Four Cells

**Forecasting time to blastocyst from the rhythm of early human embryo development**

Two embryos can reach four cells at the same hour after fertilization. One may have spent much longer at three cells. Does knowing that history improve a forecast of how many hours remain until a blastocyst is observed?

This independent machine learning project uses time-lapse annotations from Nantes University Hospital. The package includes a verified cohort, a runnable timing experiment and its held-out predictions.

## Run the foundation

From the extracted project directory, use Python 3.11 or later. The processed cohort ships with the project, so the timing experiment can run immediately. On Windows, activate the environment with `.venv\Scripts\activate`. On Linux or macOS, use `source .venv/bin/activate`.

```bash
python -m venv .venv
# Activate the environment, then run
python -m pip install -e .
four-cells evaluate
python -m unittest discover -s tests -v
```

Open `runs/baseline/metrics.csv` and `paired_gain.csv`. Per-embryo predictions include the fold and the predicted hour of blastocyst formation. Each run uses a fresh output directory. For a second run use, for example, `four-cells evaluate --output runs/second`. The bundled reference run is under `results/reference/`.

| Path | Responsibility |
| --- | --- |
| `src/first_four_cells/cohort.py` | Join event annotations to timestamps and audit exclusions |
| `src/first_four_cells/protocol.py` | Define the prediction cutoff and allowed features for each stage |
| `src/first_four_cells/evaluation.py` | Share folds across stages, fit models and quantify paired errors |
| `src/first_four_cells/cli.py` | Expose the cohort and evaluation commands |
| `scripts/build_cohort.py` | Preserve the original standalone cohort command |
| `tests/` | Check cutoff features, group separation and held-out metrics |

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

To rebuild both tables after extracting the archives, run `four-cells cohort` from the repository root.

## Timing experiment

The primary comparison starts at t4. Both ordinary linear regression models forecast remaining hours until tB. The clock model uses only t4. The rhythm model also uses t3 − t2 and t4 − t3. A third predictor returns the median remaining time from the training fold. Exploratory t2 and t3 runs use the same complete-case cohort and fold assignments. At t2 the clock is the only measured timing feature. At t3 the rhythm model gains its first interval. Adding the observed landmark time to a remaining-time forecast gives the predicted hour of tB and preserves its absolute error.

The reference run uses five shuffled embryo-level folds and seed 42. Verified patient or cycle IDs were unavailable for this run. Patient-level independence remains unverified. To use verified groups, supply `--groups groups.csv` with columns `embryo_id,group_id`. Grouped evaluation keeps related embryos together and bootstraps whole groups. The paired 95% percentile interval uses 5,000 resamples of held-out errors and is conditional on these fitted folds.

| Four-cell predictor | Held-out MAE (hours) |
| --- | ---: |
| Training median | 8.197 |
| Clock | 8.306 |
| Clock and rhythm | 8.080 |

The estimated paired gain is 0.226 hours (95% interval −0.027 to 0.493). The interval includes zero. This cohort includes embryos with complete early annotations and an observed blastocyst at one center. Earlier-stage comparisons inherit the same selection.

## Next experiment with microscopy

Use the central focal plane and the first annotated t4 frame. Build an image manifest keyed by full embryo ID, annotated start frame and path. Report missing or unreadable frames before fitting. Extract frozen ResNet-18 features with external pretrained weights. Compare timing-only ridge regression with timing-plus-image ridge regression on the same image-eligible embryos and outer folds. Fit scaling, any dimension reduction and hyperparameter selection within training data. The timing-only result above provides a reference. The image experiment requires its own matched comparison.


### Build the four-cell image manifest

Extract the Zenodo v3 central-plane archive `embryo_dataset.tar.gz` under `data/raw/`.
The image root contains one folder per full embryo ID. Use the extracted annotations from the timing experiment. From the project root run:

```shell
python -m pip install -e .
python -m first_four_cells.cli image-manifest
```

Use `--annotations DIR` and `--images DIR` for custom locations. The command matches the annotation start frame to the exact numeric RUN suffix and decodes the JPEG. The output at `data/processed/t4_image_manifest.csv` includes one row per cohort embryo. Resolve `image_path` relative to the image root. Use only rows with status `ok` in a matched image experiment. Inspect the other statuses to audit coverage.

### Explore two embryos visually

Run `python -m first_four_cells.cli visualize` and open `reports/embryo-explorer.html` in a browser. It uses bundled held-out predictions by default. Pass `--predictions runs/baseline/predictions.csv` to inspect your own run. The initial pair has the closest four-cell times and, among ties, the largest difference in time spent at three cells. Select any other pair or switch the model in the cohort scatterplot. The report embeds thumbnails when the t4 manifest and images are available. Pass `--images DIR` for a custom central-plane folder and regenerate after building a new manifest.
