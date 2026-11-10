"""Matched image ablation using frozen external ImageNet features."""


import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ...evaluation import load_cohort, make_folds, paired_interval, read_table


def compare(cohort, manifest, images, seed, groups_file):
    import torch
    from PIL import Image
    from torchvision.models import ResNet18_Weights, resnet18

    ids, rows = load_cohort(cohort)
    manifest_rows = read_table(manifest)
    mapping = {r["embryo_id"]: r for r in manifest_rows}
    if len(mapping) != len(manifest_rows) or set(mapping) != set(ids):
        raise ValueError("Regenerate the t4 manifest for this cohort.")
    rows = [r for r in rows if mapping[r["embryo_id"]]["status"] == "ok"]
    ids = [r["embryo_id"] for r in rows]
    folds, groups = make_folds(ids, seed, groups_file)
    weights = ResNet18_Weights.IMAGENET1K_V1
    encoder = resnet18(weights=weights).eval()
    encoder.fc = torch.nn.Identity()
    transform = weights.transforms()
    embeddings = []
    with torch.inference_mode():
        for i in ids:
            path = (images / mapping[i]["image_path"]).resolve()
            if not path.is_relative_to(images.resolve()):
                raise ValueError("Image lies outside central-plane folder")
            with Image.open(path) as image:
                batch = transform(image.convert("RGB")).unsqueeze(0)
            embeddings.append(encoder(batch).squeeze(0).numpy())
    visual = np.array(embeddings)
    timing = np.array(
        [[float(r[k]) for k in ("t4_h", "two_cell_h", "three_cell_h")] for r in rows]
    )
    y = np.array([float(r["remaining_h"]) for r in rows])
    metrics, predictions, errors = [], [], {}
    for name, x in (
        ("timing", timing),
        ("image", visual),
        ("timing_image", np.column_stack((timing, visual))),
    ):
        pred = np.empty(len(ids))
        for fold, (train, test) in enumerate(folds, 1):
            model = make_pipeline(StandardScaler(), Ridge(alpha=100))
            pred[test] = model.fit(x[train], y[train]).predict(x[test])
            predictions.extend(
                dict(
                    embryo_id=ids[i],
                    fold=fold,
                    model=name,
                    actual_h=y[i],
                    predicted_h=pred[i],
                )
                for i in test
            )
        errors[name] = np.abs(pred - y)
        metrics.append(dict(model=name, n=len(ids), mae_h=errors[name].mean()))
    delta = errors["timing"] - errors["timing_image"]
    lo, hi = paired_interval(delta, groups, seed)
    return {
        "image_metrics": metrics,
        "image_predictions": predictions,
        "image_gain": [dict(gain_h=delta.mean(), ci_low_h=lo, ci_high_h=hi)],
    }
