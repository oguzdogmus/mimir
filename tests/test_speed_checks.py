"""The acceptance counter for the speed rules of #77 (tests/acceptance/speed_checks.py)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "acceptance"))
import speed_checks  # noqa: E402


def text(t):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}


def tool(name, tid="t", **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "id": tid, "input": inp}]}}


def submit(n=1):
    """A ``verify.py submit`` call with ``n`` questions (the gate of the speed slice)."""
    questions = [{"item": f"quiz:{i}", "topic": "CFG", "origin": "practice", "question": "q", "key": "k"}
                 for i in range(n)]
    return tool("Bash", command="python3 /p/scripts/verify.py submit <<'EOF'\n"
                + json.dumps({"term": "2026-Fall", "course": "CS301", "session": "s", "questions": questions})
                + "\nEOF")


def settle(**extra):
    return tool("Bash", command="python3 /p/scripts/verify.py settle <<'EOF'\n"
                + json.dumps({"batch": 1, "checker": "independent", "reply": "t\n1 | correct | ok", **extra})
                + "\nEOF")


RECORD = tool("Bash", command="python3 /p/scripts/session.py record <<'EOF'\n{}\nEOF")


def checker(tid="c1", **extra):
    return tool("Agent", tid, subagent_type="mimir:verifier", description="check", prompt="...", **extra)


def failures(events):
    found = speed_checks.check_turn(events)
    found.pop("K_ok", None)
    return {k: v for k, v in found.items() if v}


def test_an_answer_turn_with_feedback_first_passes():
    assert failures([text("Right: {aⁿbcⁿ}. Item 2: ..."), RECORD]) == {}


def test_an_answer_turn_that_records_before_the_feedback_fails_j():
    assert set(failures([tool("Read", file_path="recording.md"), RECORD, text("Right.")])) == {"J"}


def test_a_turn_without_record_is_not_an_answer_turn():
    assert failures([tool("Bash", command="python3 /p/scripts/session.py now"), text("Standard delivery")]) == {}


def test_a_set_start_with_its_first_question_before_the_checks_passes_and_quotes_it():
    found = speed_checks.check_turn([text("Item 1: describe S → aSc | b."), submit(5), checker(run_in_background=False),
                                     settle()])
    assert found["K_ok"] == ["Item 1: describe S → aSc | b."]
    assert not any(found[c] for c in "JKLMN")


def test_a_gate_or_dispatch_before_any_text_fails_k():
    assert set(failures([submit(), checker(run_in_background=False), settle(), text("Item 1: ...")])) == {"K"}
    assert set(failures([checker(run_in_background=False), text("Item 1: ...")])) == {"K"}


def test_a_set_and_one_recheck_pass_but_a_third_dispatch_or_a_seventh_item_fails_l():
    ok = [text("Item 1"), submit(3), checker("a"), settle(), submit(1), checker("b"), settle()]
    assert failures(ok) == {}
    assert set(failures(ok + [checker("c")])) == {"L"}
    assert set(failures([text("Item 1"), submit(7)])) == {"L"}


def test_a_background_dispatch_fails_m_whether_asked_for_or_started_so():
    assert set(failures([text("Item 1"), checker(run_in_background=True)])) == {"M"}
    started = {"type": "system", "subtype": "task_started", "tool_use_id": "c1", "is_background": True}
    assert set(failures([text("Item 1"), checker("c1"), started])) == {"M"}
    host_key = {"type": "system", "subtype": "task_started", "tool_use_id": "c1", "is_backgrounded": True}
    assert set(failures([text("Item 1"), checker("c1"), host_key])) == {"M"}  # Claude Code's own field name
    foreground = {**started, "is_background": False}
    assert failures([text("Item 1"), checker("c1", run_in_background=False), foreground]) == {}


def test_subagent_steps_do_not_count_as_the_tutors():
    inner = {**tool("Bash", command="python3 /p/scripts/pdftext.py pages"), "parent_tool_use_id": "c1"}
    assert failures([text("Item 1"), checker("c1"), inner, RECORD]) == {}


def test_cli_reads_a_run_folder_and_exits_1_on_a_failure(tmp_path, capsys):
    events = tmp_path / "events"
    events.mkdir()
    (events / "turn-1.jsonl").write_text("\n".join(json.dumps(e) for e in [text("Item 1"), submit(), checker(), settle()]))
    (events / "turn-2.jsonl").write_text("not json\n" + json.dumps(RECORD) + "\n" + json.dumps(text("Right.")))
    assert speed_checks.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "J FAIL K PASS L PASS M PASS N PASS"
    assert "turn-2 J FAIL" in out[-2]


def test_a_batch_settled_without_a_checker_call_fails_n():
    """#23: a host ran the gate, skipped the checker and typed correct verdicts."""
    assert set(failures([text("Item 1"), submit(2), settle()])) == {"N"}
    assert set(failures([text("Item 1"), submit(1), checker("a"), settle(), submit(1), settle()])) == {"N"}
    assert set(failures([text("Item 1"), submit(1), settle(checker="self")])) == {"N"}


def test_a_settle_after_its_checker_or_a_failed_dispatch_passes_n():
    assert failures([text("Item 1"), submit(2), checker("a"), settle()]) == {}
    assert failures([text("Item 1"), submit(2), checker("a"), settle(dispatch_failed=True)]) == {}
