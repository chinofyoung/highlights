from app.api import jobs


def test_create_returns_running_job():
    jid = jobs.create()
    rec = jobs.get(jid)
    assert rec["status"] == "running"
    assert rec["progress"] == 0.0
    assert rec["result"] is None and rec["error"] is None


def test_update_sets_fields():
    jid = jobs.create()
    jobs.update(jid, progress=0.5)
    assert jobs.get(jid)["progress"] == 0.5
    jobs.update(jid, status="done", result={"rallies": []}, progress=1.0)
    rec = jobs.get(jid)
    assert rec["status"] == "done" and rec["result"] == {"rallies": []}


def test_get_returns_copy_not_reference():
    jid = jobs.create()
    rec = jobs.get(jid)
    rec["progress"] = 9.9
    assert jobs.get(jid)["progress"] == 0.0


def test_update_unknown_job_is_noop():
    jobs.update("nope", progress=1.0)  # must not raise
    assert jobs.get("nope") is None


def test_concurrent_updates_are_safe():
    import threading
    jid = jobs.create()
    def bump():
        for _ in range(100):
            cur = jobs.get(jid)["progress"]
            jobs.update(jid, progress=cur)
    threads = [threading.Thread(target=bump) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert jobs.get(jid)["status"] == "running"  # no crash / corruption


def test_create_has_cancelled_false():
    jid = jobs.create()
    assert jobs.get(jid)["cancelled"] == False


def test_cancel_sets_cancelled_true():
    jid = jobs.create()
    jobs.cancel(jid)
    rec = jobs.get(jid)
    assert rec["cancelled"] == True
    assert rec["status"] == "cancelled"


def test_cancel_unknown_is_noop():
    jobs.cancel("nope")  # must not raise
    assert jobs.get("nope") is None
