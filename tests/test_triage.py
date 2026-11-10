"""Filesystem boundary tests for the read-only ``session.py triage`` workflow."""

from __future__ import annotations

import json

import pytest

from test_session import (  # Reuse the same real workspace and command fixtures.
    MASTERY_HEAD, NOW, SS, TERM, _run, course, fails, home, index, ok, profile, root,
    save_scope, snapshot,
)

CONTEXT = {"now": NOW, "term": TERM, "course": "CS201 Theory", "class": "Urgent"}


def fingerprint(cdir, rows):
    text = ("# Fingerprint\n\n## Question types\n| type | frequency | marks |\n"
            "|---|---|---|\n")
    text += "".join(f"| {name} | {freq} | {marks} |\n" for name, freq, marks in rows)
    (cdir / ".state" / "fingerprint.md").write_text(text, encoding="utf-8")


def triage(home, associations=None, **context):
    payload = {**CONTEXT, **context}
    if associations is not None:
        payload["associations"] = associations
    return ok(home, "triage", payload)


def by_name(out):
    return {row["name"]: row for row in out["rows"]}


def test_extract_associate_status_and_rank_from_authoritative_files(home, root):
    cdir = course(home, mastery=[("Automata", "gap", "2026-10-10", 1, 0),
                                  ("Proofs", "mastered", "2026-10-10", 0, 2)])
    fingerprint(cdir, [
        ("DFA construction (source: past-papers/midterm.pdf)", "2 of 2 papers", "15"),
        ("Pumping proof (source: past-papers/final.pdf) (tentative) (prior term)", "1 of 2 papers", "20"),
        ("Minimization (source: past-papers/midterm.pdf)", "1 of 2 papers", "10"),
    ])
    profile(root, exams=[("CS201", "midterm", "2026-11-05")])
    before = snapshot(root)
    start = ok(home, "start", {"now": NOW})
    context = {"now": NOW, "term": start["term"], "course": start["course"], "class": start["class"]["class"]}
    draft = ok(home, "triage", context)
    assert draft["state"] == "needs-associations"
    assert (draft["course_dir"], draft["term"], draft["course"], draft["class"]) == (
        str(cdir), TERM, "CS201 Theory", "Standard")
    assert draft["mastery_topics"] == ["Automata", "Proofs"]
    assert draft["types"] == [
        {"name": "DFA construction", "source_note": "(source: past-papers/midterm.pdf)",
         "tentative": False, "prior_term": False},
        {"name": "Pumping proof", "source_note": "(source: past-papers/final.pdf) (tentative) (prior term)",
         "tentative": True, "prior_term": True},
        {"name": "Minimization", "source_note": "(source: past-papers/midterm.pdf)",
         "tentative": False, "prior_term": False},
    ]
    out = ok(home, "triage", {**context, "associations": {
        "DFA construction": "Automata", "Pumping proof": "Proofs", "Minimization": "Automata"}})
    assert out["state"] == "ready" and out["basis"] == "papers"
    assert out["drill"] == ["DFA construction", "Pumping proof", "Minimization"]
    assert [(r["topic"], r["reason"]) for r in out["rows"]] == [
        ("Automata", "gap"), ("Proofs", "mastered: revision"), ("Automata", "gap")]
    assert out["rows"][1]["source_note"] == draft["types"][1]["source_note"]
    assert out["rows"][1]["tentative"] is True and out["rows"][1]["prior_term"] is True
    assert out["line"] == "Ranked by marks × how often each type appeared in past papers."
    assert "associations" not in out and "types" not in out
    assert snapshot(root) == before


def test_null_association_uses_own_name_and_does_not_force_unseen(home, root):
    cdir = course(home, mastery=[("Heaps", "mastered", "2026-09-01", 0, 2)])
    fingerprint(cdir, [(" heaps ", "1 of 1 paper", "40"), ("New type", "1 of 1 paper", "5")])
    assert triage(home)["state"] == "needs-associations"  # Even an exact match is explicit.
    out = triage(home, {"HEAPS": None, "new   type": None})
    assert out["drill"] == ["New type"]
    heaps = by_name(out)["heaps"]
    assert (heaps["topic"], heaps["decision"], heaps["reason"]) == ("Heaps", "skip", "mastered")
    assert by_name(out)["New type"]["topic"] == "New type"


def test_associations_normalize_keys_and_resolve_canonical_topic_spelling(home, root):
    cdir = course(home, mastery=[("Graph Algorithms", "shaky", "2026-10-10", 1, 0)])
    fingerprint(cdir, [("Shortest paths", "1 of 1 paper", "20"), ("Spanning tree", "1 of 1 paper", "10")])
    out = triage(home, {" SHORTEST   paths ": " graph   algorithms ", "spanning TREE": "GRAPH ALGORITHMS"})
    assert out["drill"] == ["Shortest paths", "Spanning tree"]
    assert [row["topic"] for row in out["rows"]] == ["Graph Algorithms", "Graph Algorithms"]
    assert [row["reason"] for row in out["rows"]] == ["shaky", "shaky"]


@pytest.mark.parametrize("associations", [
    {}, {"A": None}, {"A": None, "B": None, "C": None},
    {"A": "Missing", "B": None}, {"A": "", "B": None},
    {"A": 1, "B": None}, {"A": [], "B": None},
    {"A": None, " a ": None, "B": None}, {"": None, "B": None}, [], "A", 1,
])
def test_bad_or_incomplete_associations_exit_2_without_writing(home, root, associations):
    cdir = course(home, mastery=[("Topic", "gap", "2026-10-10", 1, 0)])
    fingerprint(cdir, [("A", "1 of 1 paper", "10"), ("B", "1 of 1 paper", "5")])
    before = snapshot(root)
    fails(home, "triage", {**CONTEXT, "associations": associations}, "associations")
    assert snapshot(root) == before


def test_null_associations_is_invalid_instead_of_an_unfinished_first_pass(home, root):
    course(home)
    fails(home, "triage", {**CONTEXT, "associations": None}, "associations")


def test_rereads_mastery_and_rejects_association_to_removed_topic(home, root):
    cdir = course(home, mastery=[("Automata", "gap", "2026-10-10", 1, 0)])
    fingerprint(cdir, [("DFA construction", "2 of 2 papers", "15")])
    assert triage(home)["mastery_topics"] == ["Automata"]
    associations = {"DFA construction": "Automata"}
    assert triage(home, associations)["drill"] == ["DFA construction"]
    course(home, mastery=[("Automata", "mastered", "2026-10-17", 0, 2)])
    assert triage(home, associations)["drill"] == []
    course(home, mastery=[("Renamed topic", "gap", "2026-10-17", 1, 0)])
    before = snapshot(root)
    fails(home, "triage", {**CONTEXT, "associations": associations}, "associations")
    assert snapshot(root) == before


def test_rereads_fingerprint_and_requires_the_current_complete_map(home, root):
    cdir = course(home)
    fingerprint(cdir, [("A", "1 of 1 paper", "10")])
    assert [row["name"] for row in triage(home)["types"]] == ["A"]
    fingerprint(cdir, [("A", "1 of 1 paper", "10"), ("B", "1 of 1 paper", "30")])
    fails(home, "triage", {**CONTEXT, "associations": {"A": None}}, "associations")
    assert triage(home, {"A": None, "B": None})["drill"] == ["B", "A"]
    fingerprint(cdir, [("B", "1 of 1 paper", "5")])
    fails(home, "triage", {**CONTEXT, "associations": {"A": None, "B": None}}, "associations")


def test_class_and_saved_scope_apply_to_type_names_independently_of_recording_topic(home, root):
    cdir = course(home, mastery=[("Shared topic", "mastered", "2026-10-10", 0, 2),
                                  ("Gap topic", "gap", "2026-10-10", 1, 0)])
    fingerprint(cdir, [("In type", "2 of 2 papers", "20"), ("Out type", "2 of 2 papers", "50"),
                       ("New type", "1 of 2 papers", "10")])
    profile(root, exams=[("CS201", "midterm", "2026-11-05"), ("CS201", "final", "2026-12-20")])
    save_scope(home, **{"in": ["In type", "Gap topic"], "out": ["Out type", "Shared topic"]})
    associations = {"In type": "Shared topic", "Out type": "Gap topic", "New type": "Gap topic"}
    urgent = triage(home, associations)
    assert [(r["name"], r["topic"], r["decision"], r["scope"]) for r in urgent["rows"]] == [
        ("New type", "Gap topic", "drill", "not checked"),
        ("In type", "Shared topic", "skip", "in"),
        ("Out type", "Gap topic", "skip", "out")]
    standard = triage(home, associations, **{"class": "Standard"})
    assert standard["drill"] == ["In type", "New type"]
    assert by_name(standard)["Out type"]["reason"] == "not on this exam"
    # The next exam has no saved scope: every type can now be considered.
    after = triage(home, associations, now="2026-11-06T09:00:00+02:00")
    assert after["drill"] == ["Out type", "New type"]
    assert all(row["scope"] is None for row in after["rows"])


def test_topic_fallback_uses_start_remaining_and_scope_order(home, root):
    cdir = course(home, mastery=[("Outside", "gap", "2026-10-10", 1, 0),
                                  ("Done", "mastered", "2026-10-10", 0, 2),
                                  ("Inside", "shaky", "2026-10-10", 1, 0)])
    index(cdir, [("outline/syllabus.pdf", "outline")], [("Index only", "outline/syllabus.pdf#page=1")])
    profile(root, exams=[("CS201", "midterm", "2026-11-05")])
    save_scope(home, **{"in": ["Inside"], "out": ["Outside"]})
    start = ok(home, "start", {"now": NOW})
    out = triage(home)
    assert out["state"] == "ready" and out["basis"] == "outline"
    assert [r["name"] for r in out["rows"]] == [r["name"] for r in start["remaining"]] == ["Inside", "Outside"]
    assert out["drill"] == ["Inside"]
    assert [(r["marks"], r["marks_source"], r["frequency"], r["source_note"], r["tentative"], r["prior_term"])
            for r in out["rows"]] == [(None, "estimated", None, "", False, False)] * 2
    assert out["line"] == "No past papers: ranked from the course outline, without paper statistics."
    assert triage(home, {}) == out
    fails(home, "triage", {**CONTEXT, "associations": {"Inside": None}}, "associations")


@pytest.fixture
def final_course(home, root):
    cdir = course(home, mastery=[("FIR filters", "gap", "2026-10-10", 1, 0),
                                  ("IIR filters", "shaky", "2026-10-10", 1, 0),
                                  ("Filter design", "unseen", "", 0, 0),
                                  ("Multirate systems", "unseen", "", 0, 0),
                                  ("Revision", "mastered", "2026-10-10", 0, 2)])
    fingerprint(cdir, [("Fourier transform", "2 of 2 papers", "20"),
                       ("Z transform", "1 of 2 papers", "10"),
                       ("Sampling (source: past-papers/midterm.pdf) (prior term)", "1 of 2 papers", "5")])
    profile(root, exams=[("CS201", "final", "2026-12-20")])
    return cdir


def test_all_fingerprint_types_out_of_scope_falls_back_to_remaining_route_without_associations(home, root, final_course):
    route_topics = ["FIR filters", "IIR filters", "Filter design", "Multirate systems"]
    save_scope(home, exam_name="final", exam_date="2026-12-20", words="FIR filters onwards",
               **{"in": route_topics + ["Revision"], "out": ["Fourier transform", "Z transform", "Sampling"]})
    before = snapshot(root)
    out = triage(home)
    assert out["state"] == "ready" and out["basis"] == "outline"
    assert out["drill"] == route_topics
    assert [r["name"] for r in out["rows"]] == route_topics + ["Fourier transform", "Z transform", "Sampling"]
    assert [r["reason"] for r in out["rows"]] == [
        "gap", "shaky", "not studied yet", "not studied yet",
        "not on this exam", "not on this exam", "not on this exam"]
    assert all(r["scope"] == "in" for r in out["rows"][:4])
    assert all(r["decision"] == "skip" and r["scope"] == "out" for r in out["rows"][4:])
    assert [r["topic"] for r in out["rows"]] == [r["name"] for r in out["rows"]]
    assert out["rows"][-1]["source_note"] == "(source: past-papers/midterm.pdf) (prior term)"
    assert out["rows"][-1]["prior_term"] is True
    assert out["line"] == "No past papers: ranked from the course outline, without paper statistics."
    assert triage(home, {}) == out
    assert snapshot(root) == before
    # Excluded past-paper statistics must not change the outline rows.
    (final_course / ".state" / "fingerprint.md").unlink()
    assert triage(home)["rows"] == out["rows"][:4]


@pytest.mark.parametrize("scope_case", ["in", "not checked", "no scope"])
def test_fingerprint_path_keeps_associations_when_any_type_is_not_out(home, root, final_course, scope_case):
    if scope_case != "no scope":
        save_scope(home, exam_name="final", exam_date="2026-12-20", words="FIR filters onwards",
                   **{"in": ["FIR filters"] + (["Fourier transform"] if scope_case == "in" else []),
                      "out": ["Z transform", "Sampling"]})
    draft = triage(home)
    assert draft["state"] == "needs-associations"
    assert [t["name"] for t in draft["types"]] == ["Fourier transform", "Z transform", "Sampling"]
    out = triage(home, {"Fourier transform": None, "Z transform": None, "Sampling": None})
    assert out["state"] == "ready" and out["basis"] == "papers"
    assert out["drill"] == (["Fourier transform", "Z transform", "Sampling"]
                            if scope_case == "no scope" else ["Fourier transform"])
    assert out["rows"][0]["scope"] == (None if scope_case == "no scope" else scope_case)
    assert out["line"] == "Ranked by marks × how often each type appeared in past papers."


def test_all_out_fallback_uses_index_when_route_is_complete_and_lists_shared_names_once(home, root, final_course):
    course(home, mastery=[("Fourier transform", "mastered", "2026-10-10", 0, 2)])
    index(final_course, [("outline/syllabus.pdf", "outline")],
          [("FOURIER   TRANSFORM", "outline/syllabus.pdf#page=1"),
           ("FIR filters", "outline/syllabus.pdf#page=2"),
           ("FIR FILTERS", "outline/syllabus.pdf#page=3")])
    save_scope(home, exam_name="final", exam_date="2026-12-20", words="FIR filters onwards",
               **{"in": ["FIR filters"], "out": ["Fourier transform", "Z transform", "Sampling"]})
    out = triage(home)
    assert out["state"] == "ready" and out["basis"] == "outline"
    assert out["drill"] == ["FIR filters"]
    assert [(r["name"], r["reason"]) for r in out["rows"]] == [
        ("FIR filters", "not studied yet"), ("Fourier transform", "not on this exam"),
        ("Z transform", "not on this exam"), ("Sampling", "not on this exam")]


def test_without_outline_fallback_includes_only_nonmastered_augmented_route(home, root):
    cdir = course(home, mastery=[("Done", "mastered", "2026-10-10", 0, 2),
                                  ("Gap", "gap", "2026-10-10", 1, 0)])
    index(cdir, [("slides/week1.pdf", "slides")], [("done", "slides/week1.pdf#page=1"),
          ("New topic", "slides/week1.pdf#page=2"), ("NEW   TOPIC", "slides/week1.pdf#page=3")])
    out = triage(home)
    assert out["drill"] == ["Gap", "New topic"]
    assert [r["topic"] for r in out["rows"]] == ["Gap", "New topic"]


def test_index_fallback_only_when_remaining_empty_keeps_distinct_topics_and_mastery(home, root):
    cdir = course(home, mastery=[("Done", "mastered", "2026-10-10", 0, 2)])
    index(cdir, [("outline/syllabus.pdf", "outline")], [("done", "outline/syllabus.pdf#page=1"),
          ("Index only", "outline/syllabus.pdf#page=2"), ("INDEX   ONLY", "outline/syllabus.pdf#page=3")])
    assert ok(home, "start", {"now": NOW})["remaining"] == []
    urgent = triage(home)
    assert urgent["drill"] == ["Index only"]
    assert [(r["name"], r["topic"], r["reason"]) for r in urgent["rows"]] == [
        ("Index only", "Index only", "not studied yet"), ("done", "Done", "mastered")]
    standard = triage(home, **{"class": "Standard"})
    assert standard["drill"] == ["done", "Index only"]


def test_empty_sources_are_a_ready_empty_ranking_and_do_not_write(home, root):
    course(home)
    before = snapshot(root)
    out = triage(home)
    assert out["state"] == "ready" and out["basis"] == "outline"
    assert out["rows"] == [] and out["drill"] == []
    assert out["line"] == "Nothing to drill: no question types."
    assert snapshot(root) == before


def test_escaped_pipes_and_source_annotations_survive_without_becoming_type_names(home, root):
    cdir = course(home, mastery=[("Graphs \\| trees", "gap", "2026-10-10", 1, 0)])
    suffix = "(source: past-papers/mid;term \\| practice (copy).pdf; past-papers/final.pdf) (prior term) (tentative)"
    fingerprint(cdir, [(f"Trees \\| graphs {suffix}", "2 of 3 papers", "20\\|25")])
    draft = triage(home)
    assert draft["mastery_topics"] == ["Graphs | trees"]
    extracted = draft["types"][0]
    assert extracted == {"name": "Trees | graphs", "source_note": suffix.replace("\\|", "|"),
                         "tentative": True, "prior_term": True}
    row = triage(home, {"Trees | graphs": "Graphs | trees"})["rows"][0]
    assert (row["name"], row["topic"], row["marks"], row["frequency"]) == (
        "Trees | graphs", "Graphs | trees", 20, "2 of 3 papers")
    assert row["source_note"] == extracted["source_note"]


@pytest.mark.parametrize("cell,expected,source", [
    ("20\\|25", 20, "printed"), ("12.5 marks", 12.5, "printed"), ("worth 7 marks", 7, "printed"),
    ("0", 0, "printed"), ("-", 10, "estimated"), ("unknown", 10, "estimated"),
    ("1/2 of 20 marks", 10, "estimated"), ("25% of 20 marks", 10, "estimated"),
    ("½ of 20 marks", 10, "estimated"), ("⅔ of 30 marks", 10, "estimated"),
    ("2 1/2 marks", 10, "estimated"), ("1½ marks", 10, "estimated"),
    ("-5 then 20 marks", 10, "estimated"), ("-0", 10, "estimated"),
])
def test_marks_use_first_ordinary_nonnegative_number_and_estimate_unknown_expressions(home, root, cell, expected, source):
    cdir = course(home)
    fingerprint(cdir, [("Known", "1 of 1 paper", "10"), ("Check", "1 of 1 paper", cell)])
    row = by_name(triage(home, {"Known": None, "Check": None}))["Check"]
    assert (row["marks"], row["marks_source"]) == (expected, source)


@pytest.mark.parametrize("frequency,expected", [
    ("2 of 3 papers", "2 of 3 papers"), ("1 of 1 paper", "1 of 1 paper"),
    ("0 of 3 papers", "0 of 3 papers"), ("0 of 0 papers", None),
    ("-", None), ("unreadable", None), ("2/3", None), ("", None),
])
def test_frequency_grammar_and_unknown_counts(home, root, frequency, expected):
    cdir = course(home)
    fingerprint(cdir, [("A", frequency, "10")])
    assert triage(home, {"A": None})["rows"][0]["frequency"] == expected


@pytest.mark.parametrize("frequency", ["5 of 3 papers", "1 of 0 papers"])
def test_readable_impossible_frequency_is_a_row_error_before_association(home, root, frequency):
    cdir = course(home)
    fingerprint(cdir, [("Broken", frequency, "10")])
    before = snapshot(root)
    err = fails(home, "triage", CONTEXT, "fingerprint.md row 6")
    assert "Broken" in err
    assert snapshot(root) == before


def test_duplicate_fingerprint_types_are_errors_but_do_not_break_start_scope_reading(home, root):
    cdir = course(home, mastery=[("Topic", "gap", "2026-10-10", 1, 0)])
    fingerprint(cdir, [("Duplicate (source: past-papers/a.pdf)", "5 of 3 papers", "10"),
                       (" duplicate  (source: past-papers/b.pdf)", "1 of 1 paper", "20")])
    profile(root, exams=[("CS201", "midterm", "2026-11-05")])
    save_scope(home, **{"in": ["Topic"]})
    assert ok(home, "start", {"now": NOW})["scope"]["new"] == ["Duplicate"]
    # Isolate duplicate checking from the invalid count above.
    fingerprint(cdir, [("Duplicate (source: past-papers/a.pdf)", "1 of 1 paper", "10"),
                       (" duplicate  (source: past-papers/b.pdf)", "1 of 1 paper", "20")])
    fails(home, "triage", CONTEXT, "fingerprint")


def test_template_placeholder_is_not_a_real_question_type(home, root):
    cdir = course(home, mastery=[("Actual topic", "gap", "2026-10-10", 1, 0)])
    fingerprint(cdir, [("<question type> (source: <file>) (tentative)", "<n of m papers>", "<marks>")])
    assert triage(home)["drill"] == ["Actual topic"]


def test_symlinked_memory_reads_as_empty_and_external_target_is_unchanged(home, root, tmp_path):
    cdir = course(home)
    targets = {}
    for name, content in (("fingerprint.md", "## Question types\n| type | frequency | marks |\n|---|---|---|\n| Outside | 1 of 1 paper | 20 |\n"),
                          ("mastery.md", MASTERY_HEAD + "| Outside | gap | ev | 2026-10-10 | | 1 | 0 | |\n")):
        target = tmp_path / name
        target.write_text(content, encoding="utf-8")
        targets[target] = target.read_bytes()
        memory = cdir / ".state" / name
        memory.unlink(missing_ok=True)
        memory.symlink_to(target)
    out = triage(home)
    assert out["state"] == "ready" and out["rows"] == []
    assert {p: p.read_bytes() for p in targets} == targets


def test_explicit_symlinked_course_is_refused(home, root, tmp_path):
    cdir = course(home)
    target = tmp_path / "course"
    cdir.rename(target)
    cdir.symlink_to(target, target_is_directory=True)
    fails(home, "triage", CONTEXT, "symlink")


def test_triage_is_byte_deterministic_and_read_only(home, root):
    cdir = course(home)
    fingerprint(cdir, [("A", "1 of 2 papers", "20"), ("B", "2 of 2 papers", "10")])
    payload = {**CONTEXT, "associations": {"A": None, "B": None}}
    before = snapshot(root)
    first, second = _run(SS, home, "triage", payload), _run(SS, home, "triage", payload)
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout and first.stdout.count(b"\n") == 1
    assert json.loads(first.stdout)["drill"] == ["A", "B"]
    assert snapshot(root) == before


@pytest.mark.parametrize("missing", ["now", "term", "course", "class"])
def test_requires_resolved_context_instead_of_inferring_it(home, root, missing):
    course(home)
    fails(home, "triage", {k: v for k, v in CONTEXT.items() if k != missing}, missing)


@pytest.mark.parametrize("field,value", [("now", None), ("now", "2026-10-17"), ("term", ""),
                                          ("course", None), ("class", "urgent"), ("class", None)])
def test_invalid_context_exits_2(home, root, field, value):
    course(home)
    fails(home, "triage", {**CONTEXT, field: value}, field)


def test_missing_explicit_course_exits_2(home, root):
    fails(home, "triage", CONTEXT, "course")
