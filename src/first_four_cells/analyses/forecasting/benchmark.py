"""Exploratory benchmark on the primary cohort and all observed landmark pairs."""

import numpy as np
from sklearn.base import clone
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import HuberRegressor, LinearRegression, Ridge
from sklearn.model_selection import GroupKFold, KFold, cross_val_predict
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

from ...evaluation import load_cohort, make_folds, paired_interval


def early_models(seed):
    return {
        "median": DummyRegressor(strategy="median"),
        "linear": LinearRegression(),
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=5)),
        "huber": make_pipeline(StandardScaler(), HuberRegressor(max_iter=500)),
        "additive_spline": make_pipeline(
            SplineTransformer(n_knots=4, degree=2), StandardScaler(), Ridge(alpha=10)
        ),
        "small_mlp": TransformedTargetRegressor(
            regressor=make_pipeline(
                StandardScaler(),
                MLPRegressor(
                    hidden_layer_sizes=(12, 6),
                    alpha=0.5,
                    early_stopping=False,
                    solver="lbfgs",
                    max_iter=2000,
                    random_state=seed,
                ),
            ),
            transformer=StandardScaler(),
        ),
        "extra_trees": ExtraTreesRegressor(
            n_estimators=100, min_samples_leaf=12, random_state=seed
        ),
        "hist_boost": HistGradientBoostingRegressor(
            max_iter=60, max_leaf_nodes=5, min_samples_leaf=20, random_state=seed
        ),
    }


def benchmark(cohort, seed, groups_file):
    ids, rows = load_cohort(cohort)
    folds, groups = make_folds(ids, seed, groups_file)
    x = np.array(
        [[float(r[k]) for k in ("t4_h", "two_cell_h", "three_cell_h")] for r in rows]
    )
    y = np.array([float(r["remaining_h"]) for r in rows])
    predictions, metrics, intervals = [], [], []
    errors = {}
    for name, model in early_models(seed).items():
        estimate = np.empty(len(ids))
        for fold, (train, test) in enumerate(folds, 1):
            estimate[test] = clone(model).fit(x[train], y[train]).predict(x[test])
            for i in test:
                predictions.append(
                    dict(
                        embryo_id=ids[i],
                        fold=fold,
                        model=name,
                        actual_h=y[i],
                        predicted_h=estimate[i],
                    )
                )
        errors[name] = np.abs(estimate - y)
        metrics.append(
            dict(
                model=name,
                mae_h=errors[name].mean(),
                rmse_h=np.sqrt(np.mean((estimate - y) ** 2)),
                bias_h=np.mean(estimate - y),
            )
        )
    # Select within each outer training split; the held-out embryos never choose the model.
    selected = np.empty(len(ids))
    selection = []
    for fold, (train, test) in enumerate(folds, 1):
        inner = (
            list(GroupKFold(3).split(x[train], groups=groups[train]))
            if groups_file
            else list(KFold(3, shuffle=True, random_state=seed).split(x[train]))
        )
        candidates = early_models(seed)
        scores = {}
        for name, estimator in candidates.items():
            inner_predictions = cross_val_predict(
                estimator, x[train], y[train], cv=inner
            )
            scores[name] = np.abs(inner_predictions - y[train]).mean()
        winner = min(scores, key=scores.get)
        selected[test] = candidates[winner].fit(x[train], y[train]).predict(x[test])
        selection.extend(
            dict(fold=fold, candidate=name, inner_mae_h=value, chosen=name == winner)
            for name, value in scores.items()
        )
        predictions.extend(
            dict(
                embryo_id=ids[i],
                fold=fold,
                model="nested_selection",
                actual_h=y[i],
                predicted_h=selected[i],
            )
            for i in test
        )
    errors["nested_selection"] = np.abs(y - selected)
    metrics.append(
        dict(
            model="nested_selection",
            mae_h=errors["nested_selection"].mean(),
            rmse_h=np.sqrt(np.mean((selected - y) ** 2)),
            bias_h=np.mean(selected - y),
        )
    )
    for m in metrics:
        diff = errors["linear"] - errors[m["model"]]
        m["gain_vs_linear_h"] = diff.mean()
        m["gain_lo_h"], m["gain_hi_h"] = paired_interval(diff, groups, seed)
    for fold, (train, test) in enumerate(folds, 1):
        limits = []
        for q in (0.1, 0.9):
            model = HistGradientBoostingRegressor(
                loss="quantile",
                quantile=q,
                max_leaf_nodes=4,
                max_iter=50,
                random_state=seed,
            )
            limits.append(model.fit(x[train], y[train]).predict(x[test]))
        low, high = np.sort(limits, axis=0)
        for j, i in enumerate(test):
            intervals.append(
                dict(
                    embryo_id=ids[i],
                    fold=fold,
                    actual_h=y[i],
                    lo_h=low[j],
                    hi_h=high[j],
                    covered=int(low[j] <= y[i] <= high[j]),
                )
            )
    return {
        "benchmark_metrics": metrics,
        "benchmark_predictions": predictions,
        "quantile_intervals": intervals,
        "inner_selection": selection,
    }
