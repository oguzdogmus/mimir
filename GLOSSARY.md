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
The questions prepared and checked together as one batch, at most six.
_Avoid_: Batch, round

**Check ledger**:
The record of every prepared question and the outcome of its check, kept per session. A question earns mastery credit only when the ledger shows a settled check.
_Avoid_: Gate result

**Evidence pack**:
What the checker reads for one question set: the questions, their answer keys and the text of every cited source.

**Catch**:
A check verdict other than correct that led to a fixed answer key or a dropped question.

**Escape**:
A wrong answer key that reached the student, counted when the student challenges it and the tutor concedes.
