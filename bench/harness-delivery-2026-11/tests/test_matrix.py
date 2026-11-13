from harness import Target
from matrix import Session, order, run_matrix
from run_session import record_path

H = ("claude", "opencode", "dsh", "pi")


def test_order_has_112_sessions_and_mirrors_packs(tmp_path):
    o = order(("k2", "z4"), H, tmp_path)
    assert len(o) == 112 and len(set(o)) == 112
    assert [s.pack for s in o[::28]] == ["k2", "z4", "z4", "k2"]
    assert [s.rep for s in o[::28]] == [1, 1, 2, 2]


def test_first_harness_rotates_by_task(tmp_path):
    o = order(("k2", "z4"), H, tmp_path)
    assert [s.task for s in o[0:28:4]] == ["a", "b", "c", "d", "T1", "T5", "T7"]
    assert [s.harness for s in o[0:28:4]] == ["claude", "opencode", "dsh", "pi", "claude", "opencode", "dsh"]
    assert [s.harness for s in o[4:8]] == ["opencode", "dsh", "pi", "claude"]


def test_order_skips_recorded_sessions(tmp_path):
    p = record_path(tmp_path, "k2", "claude", "a", 1)
    p.parent.mkdir(parents=True)
    p.write_text("{}")
    o = order(("k2", "z4"), H, tmp_path)
    assert len(o) == 111 and Session("k2", "claude", "a", 1) not in o


def test_reduced_matrix_keeps_the_shape(tmp_path):
    assert len(order(("k2", "z2"), H[:3], tmp_path)) == 84


def test_run_matrix_switches_the_server_once_per_block(tmp_path):
    switched, ran = [], []

    def switch(pack):
        switched.append(pack)
        return Target("h", 1, pack)

    def run(harness, task, pack, rep, target, out, logs):
        assert target.model_id == pack
        ran.append((pack, harness, task, rep))
        return {"task_done": True, "wall_s": 1.0, "timeout": False}

    run_matrix(("k2", "z4"), H, tmp_path, tmp_path / "l", switch=switch, run=run, stop=lambda: switched.append("stop"))
    assert switched == ["k2", "z4", "k2", "stop"] and len(ran) == 112


def test_run_matrix_stops_the_server_when_a_session_raises(tmp_path):
    calls = []

    def boom(*a):
        raise RuntimeError("x")

    try:
        run_matrix(("k2", "z4"), H, tmp_path, tmp_path / "l", switch=lambda p: Target("h", 1, p), run=boom,
                   stop=lambda: calls.append("stop"))
    except RuntimeError:
        pass
    assert calls == ["stop"]
