"""Conditional forecasts across all supported event pairs."""

from itertools import combinations

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ...evaluation import make_folds
from ..events import STAGES, prior_features


def landmarks(maps, seed, groups_file, min_cases=50):
    results, predictions = [], []
    for a, b in combinations(STAGES, 2):
        ids = sorted(
            k
            for k, e in maps.items()
            if a in e
            and b in e
            and e[a].first < e[b].first
            and e[a].start_h < e[b].start_h
        )
        if len(ids) < min_cases:
            continue
        x = np.array([prior_features(maps[k], a) for k in ids])
        y = np.array([maps[k][b].start_h - maps[k][a].start_h for k in ids])
        splits, _ = make_folds(ids, seed, groups_file)
        for features in ("clock", "history"):
            cols = x[:, :1] if features == "clock" else x
            estimator = make_pipeline(
                SimpleImputer(
                    strategy="median", add_indicator=True, keep_empty_features=True
                ),
                StandardScaler(),
                Ridge(alpha=10),
            )
            error = []
            for fold, (train, test) in enumerate(splits, 1):
                pred = estimator.fit(cols[train], y[train]).predict(cols[test])
                error.extend(np.abs(pred - y[test]))
                predictions.extend(
                    dict(
                        embryo_id=ids[i],
                        start=a,
                        target=b,
                        features=features,
                        fold=fold,
                        actual_h=y[i],
                        predicted_h=p,
                    )
                    for i, p in zip(test, pred)
                )
            results.append(
                dict(
                    start=a,
                    target=b,
                    features=features,
                    n=len(ids),
                    mae_h=np.mean(error),
                )
            )
    return {"landmark_metrics": results, "landmark_predictions": predictions}
