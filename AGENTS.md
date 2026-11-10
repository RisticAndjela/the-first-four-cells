# Working on The First Four Cells

These instructions apply throughout the repository. Read README.md before changing the analysis. It defines the research question, the dataset version and the primary experiment. Keep implementation and documentation aligned. Describe model performance only after generating held-out predictions.

## Build the cohort

- Use the two Zenodo v3 archives named in the README. Keep downloaded files under `data/raw/` and write derived tables separately. The timing experiment requires only annotations and timestamps.
- Use one row per embryo. Recover its full ID by stripping the known filename suffix. IDs can contain multiple hyphens.
- Parse each headerless phase file as `event, start_frame, end_frame`. Join each event's start frame to the explicit `frame_index` for the same embryo. Read elapsed hours from `time`. Row offsets and assumed frame rates can yield incorrect times.
- Require observed `t2 < t3 < t4 < tB` in both frame order and elapsed hours for the primary comparison. Record exclusions with the embryo ID and reason. A missing stage has unknown duration.
- Recompute the audit from source files. Expected successive counts for v3 are 704 annotated embryos, 649 with t4, 444 with t4 followed by tB, 288 with all four events in order, and 287 with valid times. Investigate discrepancies. Let the missing-timestamp rule exclude `MM445-2-2` naturally.

## Enforce the prediction cutoff

Make the forecast at the first frame labeled `t4`. Build each feature matrix from the explicit columns below. Later events, phase end frames and total recording duration can reveal future development. Keep them out of predictor inputs. Use the first `tB` frame to calculate the target in hours. The earlier `tSB` event has a different meaning.

| Predictor | Inputs available at forecast time | Fit on the training fold |
| --- | --- | --- |
| Median baseline | None | Median of `tB - t4` |
| Four-cell model | `t4` | Ordinary linear regression |
| Rhythm model | `t4`, `t3 - t2`, `t4 - t3` | Ordinary linear regression |

## Evaluate the comparison

- Use the same eligible embryos and five folds for all three predictors. Save fold assignments keyed by full embryo ID. Keep verified patient or treatment-cycle groups together. If group identifiers are unavailable, use seeded embryo-level splits and report that patient-level independence is unverified. An ID prefix alone does not establish a relationship.
- Fit models and any learned preprocessing within each training fold. Check that every eligible embryo has exactly one held-out prediction per predictor and that each fold has disjoint training and evaluation groups when grouping is used.
- Compute mean absolute error in hours over pooled held-out predictions. Report the paired improvement as `MAE(four-cell) - MAE(rhythm)`. Bootstrap paired errors together, using the verified group as the resampling unit when available. Record the seed, number of resamples and interval level.
- Keep the primary comparison identifiable if exploratory models are added. Report the measured difference even when the rhythm model has equal or greater error.

## Verify and report changes

When changing ingestion, rerun the cohort audit. When changing modeling, regenerate held-out predictions and recompute metrics from those predictions. Record the commands actually run and distinguish verified outputs from planned work.

Preserve enough output to trace a reported result to event times, exclusion reasons, fold assignments and predictions. For the two-embryo timeline, show each embryo's four-cell cutoff and observed blastocyst time. Limit conclusions to developmental timing among eligible embryos with an observed blastocyst.
