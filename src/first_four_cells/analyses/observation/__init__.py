"""Model annotation availability and tabulate observed follow-up at the four-cell landmark."""

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ...evaluation import make_folds
from ..events import prior_features


def describe(maps, raw, audit, seed, groups_file):
    ids = sorted(i for i, events in maps.items() if "t4" in events)
    clocks = {r["embryo_id"]: r for r in audit}
    follow_up = []
    for embryo in ids:
        e = maps[embryo]
        cutoff = e["t4"]
        annotations = [event for event in raw[embryo] if event.stage == "tB"]
        after = [event for event in annotations if event.first > cutoff.first]
        last = clocks[embryo]["last_recorded_h"]
        elapsed = (
            None if last is None or last < cutoff.start_h else last - cutoff.start_h
        )
        follow_up.append(
            dict(
                embryo_id=embryo,
                t4_h=cutoff.start_h,
                recorded_tB_after_t4=int(bool(after)),
                observed_event_h=(after[0].start_h if after else None),
                recording_follow_up_h=elapsed,
                endpoint_status="annotated_after_t4" if after else "unresolved",
            )
        )
    x = np.asarray([prior_features(maps[i], "t4") for i in ids])
    y = np.asarray([r["recorded_tB_after_t4"] for r in follow_up])
    folds, _ = make_folds(ids, seed, groups_file)
    metrics, predictions = [], []
    for name, estimator in (
        ("prevalence", DummyClassifier(strategy="prior")),
        (
            "logistic",
            make_pipeline(
                SimpleImputer(
                    strategy="median", add_indicator=True, keep_empty_features=True
                ),
                StandardScaler(),
                LogisticRegression(C=0.25, max_iter=500),
            ),
        ),
    ):
        probabilities = np.empty(len(y))
        for fold, (train, test) in enumerate(folds, 1):
            fit = estimator.fit(x[train], y[train])
            probabilities[test] = fit.predict_proba(x[test])[
                :, list(fit.classes_).index(1)
            ]
            predictions.extend(
                dict(
                    embryo_id=ids[i],
                    fold=fold,
                    model=name,
                    annotated=y[i],
                    probability=probabilities[i],
                )
                for i in test
            )
        metrics.append(
            dict(
                model=name,
                n=len(y),
                positive=int(y.sum()),
                roc_auc=roc_auc_score(y, probabilities),
                average_precision=average_precision_score(y, probabilities),
                brier=brier_score_loss(y, probabilities),
            )
        )
    return {
        "follow_up": follow_up,
        "annotation_metrics": metrics,
        "annotation_predictions": predictions,
    }
