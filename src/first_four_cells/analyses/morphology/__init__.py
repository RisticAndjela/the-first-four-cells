"""Predict the two recorded morphology grades independently at t4."""

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ...evaluation import make_folds, read_table
from ..events import prior_features


def evaluate(path, maps, seed, groups_file):
    rows = read_table(path)
    labels = {r["video_name"]: r for r in rows}
    if len(labels) != len(rows) or set(labels) != set(maps):
        raise ValueError(
            "The grade file must match the full set of unique recording IDs."
        )
    metrics, predictions, counts = [], [], []
    for task in ("TE", "ICM"):
        if any(r[task] not in {"NA", "A", "B", "C"} for r in rows):
            raise ValueError(f"Unexpected {task} grade")
        ids = sorted(
            i for i, e in maps.items() if "t4" in e and labels[i][task] != "NA"
        )
        x = np.array([prior_features(maps[i], "t4") for i in ids])
        y = np.array([labels[i][task] for i in ids])
        folds, _ = make_folds(ids, seed, groups_file)
        for name in ("train_majority", "balanced_logistic"):
            predicted = np.empty(len(ids), dtype="U1")
            for fold, (train, test) in enumerate(folds, 1):
                if name == "train_majority":
                    classes, n = np.unique(y[train], return_counts=True)
                    predicted[test] = classes[np.argmax(n)]
                else:
                    model = make_pipeline(
                        SimpleImputer(
                            strategy="median",
                            add_indicator=True,
                            keep_empty_features=True,
                        ),
                        StandardScaler(),
                        LogisticRegression(
                            C=0.25, class_weight="balanced", max_iter=500
                        ),
                    )
                    predicted[test] = model.fit(x[train], y[train]).predict(x[test])
                predictions.extend(
                    dict(
                        embryo_id=ids[i],
                        task=task,
                        fold=fold,
                        model=name,
                        actual=y[i],
                        predicted=predicted[i],
                    )
                    for i in test
                )
            metrics.append(
                dict(
                    task=task,
                    model=name,
                    n=len(ids),
                    balanced_accuracy=balanced_accuracy_score(y, predicted),
                )
            )
            matrix = confusion_matrix(y, predicted, labels=list("ABC"))
            counts.extend(
                dict(task=task, model=name, actual=a, predicted=b, n=matrix[j, k])
                for j, a in enumerate("ABC")
                for k, b in enumerate("ABC")
            )
    return {
        "grade_metrics": metrics,
        "grade_predictions": predictions,
        "grade_confusion": counts,
    }
