"""Observed transitions, annotation coverage and durations for every stage pair."""

from collections import Counter, defaultdict
from itertools import combinations

import numpy as np

from ..events import STAGES, stage_map


def describe(records):
    ledger, pairs, paths, edges = [], [], Counter(), Counter()
    values = defaultdict(list)
    coverage = Counter()
    for embryo, events in records.items():
        names = [e.stage for e in events]
        paths[tuple(names)] += 1
        edges.update(zip(names, names[1:]))
        coverage.update(set(names))
        for e in events:
            ledger.append(
                dict(
                    embryo_id=embryo,
                    stage=e.stage,
                    first_frame=e.first,
                    last_frame=e.last,
                    onset_h=e.start_h,
                    last_labeled_h=e.last_h,
                )
            )
        observed = stage_map(events)
        for a, b in combinations(STAGES, 2):
            if a not in observed or b not in observed:
                continue
            first, last = observed[a], observed[b]
            if last.first > first.first and last.start_h > first.start_h:
                values[a, b].append(last.start_h - first.start_h)
    for a, b in combinations(STAGES, 2):
        v = values[a, b]
        quartiles = np.quantile(v, [0.25, 0.5, 0.75]) if v else (None,) * 3
        pairs.append(
            dict(
                start=a,
                target=b,
                n=len(v),
                q25_h=quartiles[0],
                median_h=quartiles[1],
                q75_h=quartiles[2],
            )
        )
    return {
        "event_ledger": ledger,
        "pair_support": pairs,
        "stage_coverage": [
            dict(stage=s, annotated=coverage[s], missing=len(records) - coverage[s])
            for s in STAGES
        ],
        "observed_paths": [
            dict(path=" > ".join(p), embryos=n) for p, n in paths.most_common()
        ],
        "observed_edges": [
            dict(source=a, target=b, count=n) for (a, b), n in edges.most_common()
        ],
    }
