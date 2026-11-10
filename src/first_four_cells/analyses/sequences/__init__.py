"""Forecast the next annotated stage from a prefix ending at a known event."""

from collections import Counter

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ...evaluation import make_folds
from ..events import STAGES, prior_features


def forecast(records, maps, seed, groups_file):
    predictions, metrics = [], []
    for stage in STAGES:
        next_stage = {}
        for embryo, events in records.items():
            if stage not in maps[embryo]:
                continue
            index = next(j for j, e in enumerate(events) if e.stage == stage)
            if index + 1 < len(events):
                next_stage[embryo] = events[index + 1].stage
        ids = sorted(next_stage)
        if len(ids) < 50 or len(set(next_stage.values())) < 2:
            continue
        x = np.array([prior_features(maps[i], stage) for i in ids])
        y = np.array([next_stage[i] for i in ids])
        splits, _ = make_folds(ids, seed, groups_file)
        for method in ("train_mode", "prefix_logistic"):
            predicted = np.empty_like(y)
            for fold, (train, test) in enumerate(splits, 1):
                counts = Counter(y[train])
                if method == "train_mode" or len(counts) == 1:
                    pred = [counts.most_common(1)[0][0]] * len(test)
                else:
                    estimator = make_pipeline(
                        SimpleImputer(
                            strategy="median",
                            add_indicator=True,
                            keep_empty_features=True,
                        ),
                        StandardScaler(),
                        LogisticRegression(C=0.25, max_iter=500),
                    )
                    pred = estimator.fit(x[train], y[train]).predict(x[test])
                predicted[test] = pred
                predictions.extend(
                    dict(
                        embryo_id=ids[j],
                        stage=stage,
                        fold=fold,
                        method=method,
                        actual=y[j],
                        predicted=predicted[j],
                    )
                    for j in test
                )
            metrics.append(
                dict(
                    stage=stage,
                    method=method,
                    n=len(ids),
                    accuracy=accuracy_score(y, predicted),
                    macro_f1=f1_score(y, predicted, average="macro", zero_division=0),
                )
            )
    return {"next_stage_metrics": metrics, "next_stage_predictions": predictions}
