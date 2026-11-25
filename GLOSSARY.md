# Mimir

Mimir helps students prepare for exams through teaching and practice.

## Language

**Teaching settings**:
A student's saved levels of support, guiding-question frequency and guiding-question depth, shared across courses.
_Avoid_: Teaching preference, learning ability, learning-style diagnosis

**Support**:
The amount and form of explanation offered before the student is asked to reason.

**Guiding-question frequency**:
How often the tutor invites reasoning: at checks only, at key decisions, or at every step. Not a quota of questions.

**Guiding-question depth**:
The kind of reasoning invited, such as recalling a rule, choosing a next step, explaining why or considering a changed case.
_Avoid_: Student ability

**Setup sampler**:
An optional setup experience using everyday mini-demonstrations to choose initial teaching settings.
_Avoid_: Knowledge gauge, placement test

**Knowledge gauge**:
A course-specific initial assessment of what the student already knows, distinct from their teaching settings.
_Avoid_: Setup sampler

**Probe trial**:
A natural trial of one transition toward more independent teaching, continued across eligible Standard sessions until adopted or rejected. Paused, not applied, in sessions within 48 hours of an exam.
_Avoid_: Preference probe, knowledge check

**Application question**:
A question the student solves to practise using a method, distinct from a guiding question embedded in an explanation.

**Question type**:
A recurring form of exam question, such as DFA construction. Several question types may belong to the same topic whose mastery is tracked.

**Method-first support**:
An explanation of the solving method before the student attempts the problem, without supplying its answer.

**Example-first support**:
A complete worked demonstration on a separate example before the student attempts a fresh problem.

**Delivery class**:
How a study session runs: Standard (teaching) or Urgent (exam-focused drilling). Set by exam proximity unless the student chooses.
_Avoid_: Normal mode

**Lasting delivery choice**:
A student's choice of delivery class saved for one exam ("always study normally for this exam"). It expires when that exam passes; any other choice lasts one session.

**Key decision**:
A step where a plausible wrong choice gives a different final answer.
_Avoid_: Meaningful moment

**Level**:
One of three named settings on a teaching-settings axis.

**Transition**:
A move between two adjacent levels on one axis. Probe-trial rejections are counted per transition.

**Provenance**:
Where a saved teaching-settings level came from: default, sampler, learned, explicit or legacy.

**Standing instruction**:
An explicit, lasting student request about how to teach, such as "always explain first". Not probed against.
_Avoid_: Temporary request

**Comfortable engagement**:
The student is answering and participating without pushback or signs of frustration; the precondition for starting a probe trial.

**Exam scope**:
The question types and topics one exam covers, resolved once from the student's words ("the midterm covers sessions 1–19"), confirmed by the student and saved with that exam. Types outside it are listed last, marked, and not drilled. A name the student is unsure about is ranked normally with a "not checked" mark, like a new question type. The scope follows its exam when the exam's date or time changes.
_Avoid_: Guessing coverage from paper names

**Recipe**:
In Urgent, the short exam-sufficient method for a question type, shown before an application question.

**Session**:
One `started:` record in a course log. Preference evidence also requires different calendar days.

**Checker**:
The independent helper that checks a question's answer key against the course sources before the key reaches the student. When a host has none, the tutor makes a same-context check and tells the student.
_Avoid_: Verifier, grader

**Question set**:
The questions prepared and checked together, at most six. Not called a batch or a round.
_Avoid_: Batch, round

**Checker batch**:
One checker call: the questions of one question set (or of its recheck) read from one evidence pack and settled together. The name belongs to the call, never to the set.

**Check ledger**:
The record of every prepared question and the outcome of its check, kept per session. A question earns mastery credit only when the ledger shows a settled check.
_Avoid_: Gate result

**Evidence pack**:
What the checker reads for one question set: the questions, their answer keys and the text of every cited source.

**Catch**:
A check verdict other than correct that led to a fixed answer key or a dropped question.

**Escape**:
A wrong answer key that reached the student, counted when the student challenges it and the tutor concedes.

**House style**:
The shared Mimir look, named Skald, that every visual Mimir makes in its own voice follows, whatever the subject: the feel, palette, type and composition.
_Avoid_: Template, theme, design system

**Mock paper**:
A practice paper made to look like the instructor's own papers, so the student practises in the form they will meet in the exam. It follows the instructor's format, not the house style.
_Avoid_: Practice midterm, mock exam handout

**Motion level**:
How much animation a student wants in visuals: none, gentle or full. Saved once in the profile for all courses and changed only when the student says so. Not a teaching setting: never probed or learned. A missing or unreadable value is built as none; a missing value is asked once at the next study session.
_Avoid_: Animation preference, reduced motion

**Notation**:
Every visual property of a figure that carries meaning in its field or for the professor: shapes, symbols, proportions, positions, scales, and colours where the field assigns them. The house style never changes notation. When unsure whether a property is notation, it is.

**Figure kind**:
One of four kinds of figure, each allowing a different amount of house style: a depiction of a real thing (a heart, a bacterium), a formal notation (an ERD, a DFA, a circuit), a plot of data or a function, or Mimir's own sketch (an analogy, a concept map). When unsure, the stricter kind applies.

**Field notes**:
Conventions that hold across fields, kept one line each in the house style guide. The conventions of one field live in its field pack, researched per course, not in notes the maintainer adds. A professor's own conventions belong in the fingerprint instead.

**Field pack**:
The builder guidance for one field, saved once in the student's workspace and shared by all of the student's courses in that field: the field's figure kinds mapped to the four figure kinds, its conventions and recipes, an accuracy checklist per figure kind, its base figures and the content of its blind test page. Researched from public sources when a course's field is first known, every rule with its source. A course uses one field pack, or two when it spans two fields. The course's own materials override it. No builder draws without it: the visual shell refuses to build for a course with no field pack.
_Avoid_: Field notes, field guide, domain pack

**Field researcher**:
The helper that researches a field pack from high-trust public sources, in the background, when ingest first meets a course's field, or when a visual is wanted for a course that has no field pack yet. Its whole input is the field name and public topic names, never text, names or paths from the student's course files. It saves the pack through the field pack store, which refuses a rule without a source or a figure kind without a checklist.
_Avoid_: Field scout, pack builder

**Base figure**:
A recurring subject of a field (a heart, a truss, a neuron) built carefully once, checked against its field pack's checklist and saved in the field pack as a reusable SVG with stable part ids. Later visuals of that subject start from it and only add labels, steps and highlights.
_Avoid_: Template, stock figure

**Figure checker**:
The independent, read-only helper that checks one built figure against its field pack's accuracy checklist for that figure kind, before a base figure is saved or a blind test page is scored. It returns a pass or a fail with a reason for every checklist item, plus an overall verdict that passes only when every item does. It reads only the figure, its figure kind and that checklist.
_Avoid_: Figure verifier, figure grader

**Teaching highlight**:
The one standard mark that points at the part of a figure being discussed. Never a colour change where colour is notation.
