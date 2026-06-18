from app.eval.metrics import iou, score


def test_iou_basic():
    assert iou({"start": 0, "end": 10}, {"start": 0, "end": 10}) == 1.0
    assert iou({"start": 0, "end": 10}, {"start": 20, "end": 30}) == 0.0
    assert abs(iou({"start": 0, "end": 10}, {"start": 5, "end": 15}) - (5 / 15)) < 1e-9


def test_score_perfect():
    labels = [{"start": 0, "end": 10}, {"start": 20, "end": 30}]
    detected = [{"start": 0, "end": 10}, {"start": 20, "end": 30}]
    s = score(detected, labels)
    assert s["precision"] == 1.0 and s["recall"] == 1.0 and s["f1"] == 1.0
    assert s["tp"] == 2 and s["fp"] == 0 and s["fn"] == 0


def test_score_with_fp_and_fn():
    labels = [{"start": 0, "end": 10}, {"start": 100, "end": 110}]
    detected = [{"start": 0, "end": 10}, {"start": 50, "end": 60}]
    s = score(detected, labels, cutoff=0.5)
    assert s["tp"] == 1 and s["fp"] == 1 and s["fn"] == 1
    assert s["precision"] == 0.5 and s["recall"] == 0.5
