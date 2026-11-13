import json

from summarize import load, rank, render, reserva, table, valido, write_matrix_verdicts

H = ("claude", "opencode", "dsh", "pi")
SMALL, HARD = ("a", "b", "c", "d"), ("T1", "T5", "T7")


def rec(pack, harness, task, rep, done, wall=100.0, **extra):
    r = {"harness": harness, "harness_version": "1", "pack": pack, "task": task, "rep": rep, "model_id": f"org/{pack}:Q",
         "task_done": done, "steps_passed": None, "cheat": [], "wall_s": wall, "exit": 0, "timeout": False,
         "claimed_done": True, "turns": None, "input_tokens": None, "output_tokens": None}
    r.update(extra)
    return r


def pack_recs(pack, done, wall, harnesses, hard_done=None):
    """All sessions of one pack; the first `done` are done. hard_done fixes how many done sessions are hard tasks."""
    slots = [(h, t, rep) for t in SMALL + HARD for h in harnesses for rep in (1, 2)]
    if hard_done is not None:
        hard = [s for s in slots if s[1] in HARD]
        small = [s for s in slots if s[1] in SMALL]
        slots = hard[:hard_done] + small[:done - hard_done] + hard[hard_done:] + small[done - hard_done:]
    else:
        slots = sorted(slots, key=lambda s: s[1] not in HARD)
    return [rec(pack, h, t, rep, i < done, wall) for i, (h, t, rep) in enumerate(slots)]


def recs(k2_done, z4_done=0, k2_wall=100.0, z4_wall=100.0, harnesses=H, hard_done=None):
    return pack_recs("k2", k2_done, k2_wall, harnesses, hard_done) + pack_recs("z4", z4_done, z4_wall, harnesses)


def recs_by_harness(spec):
    out = []
    for h, (done, wall) in spec.items():
        slots = [(p, t, rep) for p in ("k2", "z4") for t in SMALL + HARD for rep in (1, 2)]
        out += [rec(p, h, t, rep, i < done, wall) for i, (p, t, rep) in enumerate(slots)]
    return out


def test_table_counts_done_and_median_of_done_sessions():
    rs = [rec("k2", "pi", "a", 1, True, 10), rec("k2", "pi", "b", 1, True, 30), rec("k2", "pi", "c", 1, False, 900)]
    assert table(rs)[("pi", "k2")] == {"done": 2, "n": 3, "median_wall_done_s": 20.0}


def test_table_median_is_none_without_done_sessions():
    assert table([rec("k2", "pi", "a", 1, False)])[("pi", "k2")]["median_wall_done_s"] is None


def test_reserva_passes_at_three_fewer_and_fails_at_four():
    assert reserva(recs(k2_done=40, z4_done=37))["pass"] is True
    assert reserva(recs(k2_done=40, z4_done=36))["pass"] is False


def test_reserva_reports_its_numbers():
    r = reserva(recs(k2_done=40, z4_done=38, k2_wall=100, z4_wall=120))
    assert (r["done_base"], r["done_cand"], r["tolerance"], r["ratio"]) == (40, 38, 3, 1.2)


def test_reserva_fails_when_slower_than_1_25x():
    assert reserva(recs(k2_done=40, z4_done=40, k2_wall=100, z4_wall=125))["pass"] is True
    assert reserva(recs(k2_done=40, z4_done=40, k2_wall=100, z4_wall=126))["pass"] is False


def test_reserva_has_no_verdict_without_done_sessions():
    r = reserva(recs(k2_done=0, z4_done=0))
    assert r["pass"] is None and r["ratio"] is None


def test_tolerance_is_proportional_when_a_harness_leaves():
    assert reserva(recs(k2_done=30, z4_done=27, harnesses=H[:3]))["tolerance"] == 3


def test_reserva_takes_another_candidate():
    rs = [dict(r, pack="z2") if r["pack"] == "z4" else r for r in recs(k2_done=40, z4_done=40)]
    assert reserva(rs, cand="z2")["pass"] is True


def test_rank_breaks_one_task_tie_by_time():
    r = rank(recs_by_harness({"pi": (20, 300), "claude": (21, 500), "dsh": (10, 100), "opencode": (15, 200)}))
    assert [h for h, *_ in r] == ["pi", "claude", "opencode", "dsh"]
    assert r[0] == ("pi", 20, 300.0)


def test_rank_keeps_a_two_task_lead():
    r = rank(recs_by_harness({"pi": (19, 300), "claude": (21, 500)}))
    assert [h for h, *_ in r] == ["claude", "pi"]


def test_valido_needs_one_hard_task_on_base():
    assert valido(recs(k2_done=16, hard_done=0)) is False
    assert valido(recs(k2_done=16, hard_done=1)) is True


def test_summary_names_the_two_repetition_caveat():
    md = render(recs(k2_done=40, z4_done=40))
    assert "2 repetições" in md and "| claude |" in md and "Reserva" in md


def test_summary_counts_failure_reasons():
    rs = recs(k2_done=40, z4_done=40)
    rs[-1].update(timeout=True, claimed_done=False)
    rs[-2].update(cheat=["tests_modified"])
    md = render(rs)
    assert "timeout | 1" in md and "tests_modified | 1" in md


def test_load_reads_session_records_and_skips_smoke(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "k2-pi-a-r1.json").write_text(json.dumps(rec("k2", "pi", "a", 1, True)))
    (d / "smoke-pi-b-r0.json").write_text(json.dumps(rec("smoke", "pi", "b", 0, True)))
    assert [r["pack"] for r in load(tmp_path)] == ["k2"]


def test_matrix_verdict_per_pair_without_session_text(tmp_path):
    write_matrix_verdicts(recs(k2_done=40, z4_done=40), tmp_path)
    f = tmp_path / "pi" / "org-k2-Q.md"
    assert f.is_file() and "harness-delivery-2026-11" in f.read_text()
    assert len(list(tmp_path.rglob("*.md"))) == 8
