"""The checker benchmark (#79): its question set, its runner and its scoring
(tests/acceptance/checker_benchmark.py). The hosts' checkers are not called here."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "acceptance"))
import checker_benchmark as bench  # noqa: E402


def test_the_shipped_set_holds_20_clean_and_40_planted_questions_with_convention_errors():
    shipped = bench.load_set(bench.SET_PATH)
    questions = shipped["questions"]
    assert len(questions) == 60
    assert sum(q["planted"] is None for q in questions) == 20
    kinds = [q["planted"]["kind"] for q in questions if q["planted"]]
    assert len(kinds) == 40 and kinds.count("convention") >= 10
    assert "notes/conventions.md" in shipped["files"]


def test_a_set_with_a_repeated_id_or_an_unknown_error_kind_is_refused(tmp_path):
    good = json.loads(bench.SET_PATH.read_text(encoding="utf-8"))
    repeated = {**good, "questions": good["questions"] + good["questions"][:1]}
    path = tmp_path / "set.json"
    path.write_text(json.dumps(repeated))
    with pytest.raises(ValueError, match="c01"):
        bench.load_set(path)
    odd = json.loads(json.dumps(good))
    odd["questions"][25]["planted"]["kind"] = "typo"
    path.write_text(json.dumps(odd))
    with pytest.raises(ValueError, match="kind"):
        bench.load_set(path)


SHIPPED = bench.load_set(bench.SET_PATH)


def pack_questions(pack: Path) -> tuple[str, list[str]]:
    """(pack token, the answer key of each question in order) read from an evidence pack."""
    text = pack.read_text(encoding="utf-8")
    token = text.split("Pack token: ", 1)[1].split()[0]
    keys = [part.split("Answer key:", 1)[1].split("~~~~")[1].strip() for part in text.split("### Question ")[1:]]
    return token, keys


def perfect_checker(pack: Path) -> dict:
    """A stand-in checker that knows which keys are planted."""
    token, keys = pack_questions(pack)
    planted = {q["key"] for q in SHIPPED["questions"] if q["planted"]}
    lines = [f"{n} | {'wrong' if key in planted else 'correct'} | stand-in" for n, key in enumerate(keys, 1)]
    return {"reply": "\n".join([token, *lines]), "seconds": 6.0, "usage": {"input_tokens": 1000}, "cost_usd": 0.06}


def test_a_run_submits_every_question_in_sets_of_at_most_six_and_scores_the_settled_verdicts(tmp_path):
    packs = []

    def checker(pack):
        packs.append(pack_questions(pack)[1])
        return perfect_checker(pack)

    result = bench.run(tmp_path / "run", SHIPPED, checker)
    assert sorted(len(keys) for keys in packs) == [6] * 10
    assert sorted(k for keys in packs for k in keys) == sorted(q["key"] for q in SHIPPED["questions"])
    s = result["summary"]
    assert (s["planted"], s["caught"], s["clean"], s["rejected"], s["unsettled"]) == (40, 40, 20, 0, 0)
    assert s["by_kind"]["convention"] == {"planted": 12, "caught": 12}
    assert s["seconds_per_question"] == pytest.approx(1.0) and s["cost_usd_per_question"] == pytest.approx(0.01)
    rows = {r["id"]: r for r in result["rows"]}
    assert rows["g01"]["verdict"] == "wrong" and rows["c01"]["verdict"] == "correct"
    assert json.loads((tmp_path / "run" / "results.json").read_text())["summary"] == s


def test_a_reply_without_the_pack_token_leaves_its_batch_unsettled_and_catches_nothing(tmp_path):
    def lazy(pack):
        _, keys = pack_questions(pack)
        return {"reply": "\n".join(f"{n} | wrong | x" for n in range(1, len(keys) + 1)), "seconds": 1.0,
                "usage": {}, "cost_usd": None}

    s = bench.run(tmp_path / "run", SHIPPED, lazy)["summary"]
    assert (s["caught"], s["rejected"], s["unsettled"]) == (0, 0, 60)
    assert s["cost_usd_per_question"] is None


PACK = Path("/l/2026-Fall/CS301 Automata/.state/checks/session-x-batch1.md")


def test_the_claude_code_checker_is_the_plugin_agent_with_only_the_pack_line_as_its_prompt():
    cmd = bench.host_cmd("claude", PACK, plugin=Path("/p/mimir"), model="haiku", effort="low")
    assert cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--agent") + 1] == "mimir:verifier" and cmd[cmd.index("--plugin-dir") + 1] == "/p/mimir"
    assert cmd[cmd.index("--model") + 1] == "haiku" and cmd[cmd.index("--effort") + 1] == "low"
    assert cmd[-1] == f"Check the evidence pack at {PACK}."
    default = bench.host_cmd("claude", PACK, plugin=Path("/p/mimir"))
    assert "--model" not in default and "--effort" not in default  # the agent's own setting


def test_the_codex_and_antigravity_checkers_get_the_helper_body_and_the_pack_line():
    for host, head in (("codex", ["codex", "exec"]), ("antigravity", ["agy", "-p"])):
        cmd = bench.host_cmd(host, PACK)
        assert cmd[:2] == head
        assert cmd[-1].startswith("You check answer keys for a study tool")
        assert cmd[-1].endswith(f"Check the evidence pack at {PACK}.")
    assert "read-only" in bench.host_cmd("codex", PACK)


def test_each_hosts_output_gives_the_checker_reply_and_its_usage():
    claude = json.dumps({"type": "result", "result": "ab12cd34\n1 | correct | ok", "total_cost_usd": 0.031,
                         "usage": {"input_tokens": 9, "cache_read_input_tokens": 7000, "output_tokens": 300}})
    assert bench.parse_output("claude", claude) == {
        "reply": "ab12cd34\n1 | correct | ok", "cost_usd": 0.031,
        "usage": {"input_tokens": 9, "cache_read_input_tokens": 7000, "output_tokens": 300}}
    codex = "\n".join(json.dumps(e) for e in [
        {"type": "thread.started", "thread_id": "t"},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "cat pack.md"}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "ab12cd34\n1 | wrong | step 2"}},
        {"type": "turn.completed", "usage": {"input_tokens": 20000, "cached_input_tokens": 15000, "output_tokens": 900}}])
    assert bench.parse_output("codex", codex) == {
        "reply": "ab12cd34\n1 | wrong | step 2", "cost_usd": None,
        "usage": {"input_tokens": 20000, "cached_input_tokens": 15000, "output_tokens": 900}}
    agy = "\n".join(json.dumps(e) for e in [
        {"event": "init", "conversation_id": "c"},
        {"event": "result", "result": {"status": "SUCCESS", "response": "ab12cd34\n1 | correct | ok\n",
                                       "usage": {"input_tokens": 5000, "output_tokens": 400, "thinking_tokens": 300}}}])
    assert bench.parse_output("antigravity", agy) == {
        "reply": "ab12cd34\n1 | correct | ok\n", "cost_usd": None,
        "usage": {"input_tokens": 5000, "output_tokens": 400, "thinking_tokens": 300}}


def test_report_row_shows_catch_rates_by_kind_and_the_cost_per_question():
    s = {"caught": 30, "planted": 40, "catch_rate": 75.0, "rejected": 1, "clean": 20, "unsettled": 0,
         "by_kind": {"general": {"planted": 28, "caught": 24}, "convention": {"planted": 12, "caught": 6}},
         "seconds_per_question": 4.2, "cost_usd_per_question": 0.0123,
         "usage_per_question": {"input_tokens": 10, "cache_read_input_tokens": 990, "output_tokens": 50}}
    assert bench.report_row("claude-sonnet", s) == ("| claude-sonnet | 30/40 (75.0%) | 24/28 | 6/12 | 1/20 | 0 | 4.2 s "
                                                     "| 1,000 in / 50 out | $0.0123 |")
