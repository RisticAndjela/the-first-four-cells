"""Descriptive rhythm clusters, extremes and selection diagnostics."""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import RobustScaler

from ...evaluation import load_cohort


def describe(cohort, maps, seed):
    ids, rows = load_cohort(cohort)
    columns = ("t4_h", "two_cell_h", "three_cell_h")
    x = np.array([[float(r[k]) for k in columns] for r in rows])
    scaler = RobustScaler().fit(x)
    z = scaler.transform(x)
    memberships, stability, profiles = [], [], []
    for k in (2, 3, 4, 5):
        fit = KMeans(k, n_init=20, random_state=seed).fit(z)
        labels = fit.labels_
        rng = np.random.default_rng(seed)
        scores = []
        for _ in range(20):
            subset = rng.choice(len(ids), int(0.8 * len(ids)), replace=False)
            transform = RobustScaler().fit(x[subset])
            model = KMeans(k, n_init=5, random_state=seed).fit(
                transform.transform(x[subset])
            )
            scores.append(
                adjusted_rand_score(labels, model.predict(transform.transform(x)))
            )
        stability.append(
            dict(
                k=k,
                silhouette=silhouette_score(z, labels),
                mean_subsample_ari=np.mean(scores),
            )
        )
        for cluster in range(k):
            mask = labels == cluster
            profiles.append(
                dict(
                    k=k,
                    cluster=cluster,
                    n=int(mask.sum()),
                    **dict(zip(columns, np.median(x[mask], axis=0))),
                )
            )
        memberships.extend(
            dict(embryo_id=e, k=k, cluster=c) for e, c in zip(ids, labels)
        )
    selection = []
    eligible = set(ids)
    for label, mask in (("included", True), ("other", False)):
        for stage in ("t2", "t3", "t4", "tB"):
            vals = [
                e[stage].start_h
                for i, e in maps.items()
                if (i in eligible) == mask and stage in e
            ]
            selection.append(
                dict(
                    cohort=label,
                    stage=stage,
                    n_observed=len(vals),
                    median_h=np.median(vals) if vals else None,
                )
            )
    extremes = [
        dict(embryo_id=i, largest_absolute_iqr_units=np.max(np.abs(row)))
        for i, row in zip(ids, z)
    ]
    return {
        "cluster_membership": memberships,
        "cluster_stability": stability,
        "cluster_profiles": profiles,
        "selection_by_stage": selection,
        "rhythm_extremes": sorted(
            extremes, key=lambda r: -r["largest_absolute_iqr_units"]
        ),
    }
