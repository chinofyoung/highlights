def iou(a: dict, b: dict) -> float:
    inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    union = (a["end"] - a["start"]) + (b["end"] - b["start"]) - inter
    return inter / union if union > 0 else 0.0


def score(detected: list[dict], labels: list[dict], cutoff: float = 0.5) -> dict:
    matched = set()
    tp = 0
    matched_ious = []
    for d in detected:
        best_j, best_iou = -1, 0.0
        for j, l in enumerate(labels):
            if j in matched:
                continue
            v = iou(d, l)
            if v > best_iou:
                best_iou, best_j = v, j
        if best_j >= 0 and best_iou >= cutoff:
            tp += 1
            matched.add(best_j)
            matched_ious.append(best_iou)
    fp = len(detected) - tp
    fn = len(labels) - tp
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    mean_iou = sum(matched_ious) / len(matched_ious) if matched_ious else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision,
            "recall": recall, "f1": f1, "mean_iou": mean_iou}
