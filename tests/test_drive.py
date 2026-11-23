"""The acceptance driver's Antigravity host (tests/acceptance/drive.py, #79)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent / "acceptance"))
import drive  # noqa: E402

CONV = "e63c1305-d24a-47cf-92c5-3a1a6263b2d6"
VERIFIER_BODY = (Path(__file__).resolve().parents[1] / "helpers" / "verifier.md").read_text(encoding="utf-8").split("---", 2)[2]


def step(index, step_type, state="DONE", **extra):
    return {"event": "step_update", "step_update": {"conversation_id": CONV, "step_index": index, "state": state,
                                                    "step_type": step_type, **extra}}


def say(index, *deltas):
    """An agent_response step streamed as text deltas, the last one DONE."""
    return [step(index, "agent_response", "ACTIVE" if i < len(deltas) - 1 else "DONE", text_delta=d)
            for i, d in enumerate(deltas)]


def run_command(index, command, output="Command exited with code 0."):
    info = {"name": "run_command", "parameters": {"CommandLine": command}}
    return [step(index, "tool", "ACTIVE", tool_name="run_command", tool_info=info),
            step(index, "tool", tool_name="run_command", tool_info={**info, "output": output})]


def define(index, name="mimir-verifier", prompt=VERIFIER_BODY, write=False):
    definition = {"name": name, "description": "checker", "system_prompt": prompt, "enable_write_tools": write,
                  "enable_mcp_tools": False, "enable_subagent_tools": False}
    return [step(index, "tool", "ACTIVE", tool_name="define_subagent", tool_info={"name": "define_subagent"}),
            step(index, "tool", tool_name="define_subagent",
                 tool_info={"name": "define_subagent", "parameters": {"definition": json.dumps(definition)},
                            "output": f'Subagent "{name}" defined.'})]


def invoke(index, type_name="mimir-verifier", prompt="Check the evidence pack at /l/pack.md."):
    return [step(index, "tool", "ACTIVE", tool_name="invoke_subagent",
                 tool_info={"name": "invoke_subagent", "parameters": {"TypeName": type_name}}),
            step(index, "subagent", tool_name="invoke_subagent",
                 subagent_info={"subagents": [{"type_name": type_name, "initial_prompt": prompt,
                                               "conversation_id": "child-1"}]})]


def result(text="ok"):
    return {"event": "result", "result": {"conversation_id": CONV, "status": "SUCCESS", "response": text,
                                          "duration_seconds": 46.9, "num_turns": 1,
                                          "usage": {"input_tokens": 16378, "output_tokens": 777,
                                                    "thinking_tokens": 496, "cache_read_tokens": 21558}}}


INIT = {"event": "init", "conversation_id": CONV, "init": {"cwd": "/l", "tools": ["run_command"]}}


def test_parse_antigravity_reads_the_conversation_texts_tool_calls_and_usage():
    events = [INIT, step(0, "user_input"), *say(1, "Standard delivery: ", "exam in 21 days"),
              *run_command(2, "python3 /p/scripts/session.py now"), *say(3, "Item 1: ..."), result()]
    session, tools, reply = drive.parse_antigravity(events)
    assert session == CONV
    assert reply == "Standard delivery: exam in 21 days\n\nItem 1: ..."
    assert tools[0] == "run_command: python3 /p/scripts/session.py now"
    assert tools[-1] == ("usage: input=16378 cache_read=21558 out=777 thinking=496 seconds=46.9")


def test_parse_antigravity_names_the_checker_definition_and_each_invocation():
    events = [INIT, *define(1), *invoke(2), *define(3, "helper", "You build pages.", write=True), result()]
    _, tools, _ = drive.parse_antigravity(events)
    assert tools[0] == ("define_subagent name=mimir-verifier from_verifier=yes write=False mcp=False "
                        "subagents=False")
    assert tools[1] == "invoke_subagent type=mimir-verifier: Check the evidence pack at /l/pack.md."
    assert tools[2] == "define_subagent name=helper from_verifier=no write=True mcp=False subagents=False"


def test_agy_cmd_starts_print_mode_with_the_plugin_dir_and_resumes_by_conversation(tmp_path):
    class Args:
        plugin = tmp_path / "mimir"
        message = "Let's study CS301."
        model = None
    first = drive.agy_cmd(Args, None)
    assert first[0] == "agy" and first[-2:] == ["-p", "Let's study CS301."]  # agy -p takes the next word as the prompt
    assert ["--add-dir", str(tmp_path / "mimir")] == first[first.index("--add-dir"):first.index("--add-dir") + 2]
    assert "--dangerously-skip-permissions" in first and first[-1] == "Let's study CS301."
    assert "--conversation" not in first
    later = drive.agy_cmd(Args, CONV)
    assert later[later.index("--conversation") + 1] == CONV


@pytest.mark.skipif(sys.platform == "win32", reason="the stand-in agy is a POSIX script")
def test_an_antigravity_turn_runs_in_the_fixture_with_the_installed_home_and_keeps_the_transcript(tmp_path, monkeypatch):
    """main() with a stand-in ``agy`` that prints one turn's events and records how it was called."""
    run = tmp_path / "run"
    (run / "home" / ".config" / "mimir").mkdir(parents=True)
    (run / "home" / ".config" / "mimir" / "root").write_text(str(run / "learning"))
    (run / "learning").mkdir()
    agy_home = tmp_path / "agy-home"
    (agy_home / ".gemini" / "config" / "plugins" / "mimir").mkdir(parents=True)
    # agy streams define_subagent without its system prompt; the conversation's full transcript keeps it.
    streamed = {"Name": "mimir-verifier", "Description": "checker"}
    events = [INIT, *say(1, "Standard delivery: exam in 21 days"),
              step(2, "tool", tool_name="define_subagent", tool_info={"name": "define_subagent", "parameters": streamed}),
              *invoke(3), result()]
    logs = agy_home / ".gemini" / "antigravity-cli" / "brain" / CONV / ".system_generated" / "logs"
    logs.mkdir(parents=True)
    call = {"name": "define_subagent", "args": {**streamed, "SystemPrompt": VERIFIER_BODY, "EnableWriteTools": False,
                                                "EnableMCPTools": False, "EnableSubagentTools": False}}
    (logs / "transcript_full.jsonl").write_text(json.dumps({"step_index": 2, "tool_calls": [call]}) + "\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "agy"
    fake.write_text("#!/usr/bin/env python3\nimport json, os, sys\n"
                    f"json.dump({{'argv': sys.argv[1:], 'home': os.environ['HOME'], 'cwd': os.getcwd()}}, "
                    f"open({str(tmp_path / 'call.json')!r}, 'w'))\n"
                    f"print({chr(10).join(json.dumps(e) for e in events)!r})\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{__import__('os').pathsep}{__import__('os').environ['PATH']}")
    plugin = agy_home / ".gemini" / "config" / "plugins" / "mimir"
    monkeypatch.setattr(sys, "argv", ["drive.py", "--run", str(run), "--host", "antigravity", "--plugin", str(plugin),
                                      "--agy-home", str(agy_home), "Let's study CS301."])
    drive.main()
    call = json.loads((tmp_path / "call.json").read_text())
    assert call["home"] == str(run / "home") and call["cwd"] == str(run / "learning")
    assert (run / "home" / ".gemini").resolve() == (agy_home / ".gemini").resolve()
    assert (run / "session_id").read_text().strip() == CONV
    transcript = (run / "transcript.md").read_text()
    assert "- define_subagent name=mimir-verifier from_verifier=yes write=False mcp=False subagents=False" in transcript
    assert (run / "events" / "agy-transcript-full.jsonl").read_text() == (logs / "transcript_full.jsonl").read_text()
    assert "- invoke_subagent type=mimir-verifier" in transcript
    assert "Standard delivery: exam in 21 days" in transcript
    assert (run / "events" / "turn-1.jsonl").is_file()
