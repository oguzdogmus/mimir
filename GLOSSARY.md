# Mimir

Mimir helps students prepare for exams through teaching and practice. These terms describe the proposed teaching-preference design; they do not imply shipped behavior.

## Language

**Teaching preference**:
A student's preferred combination of support, guiding-question frequency and guiding-question depth, shared across courses.
_Avoid_: Learning ability, learning-style diagnosis

**Support**:
The amount and form of explanation offered before the student is asked to reason.

**Guiding-question frequency**:
How often the tutor invites reasoning: at checks only, at key decisions, or at every step. Not a quota of questions.

**Guiding-question depth**:
The kind of reasoning invited, such as recalling a rule, choosing a next step, explaining why or considering a changed case.
_Avoid_: Student ability

**Setup sampler**:
An optional setup experience using everyday mini-demonstrations to discover an initial teaching preference.
_Avoid_: Knowledge gauge, placement test

**Knowledge gauge**:
A course-specific initial assessment of what the student already knows, distinct from their teaching preference.
_Avoid_: Setup sampler

**Preference probe**:
A natural trial of one transition toward more Socratic teaching, continued across sessions until adopted or rejected.
_Avoid_: Knowledge check

**Application question**:
A question the student solves to practise using a method, distinct from a guiding question embedded in an explanation.

**Method-first support**:
An explanation of the solving method before the student attempts the problem, without supplying its answer.

**Example-first support**:
A complete worked demonstration on a separate example before the student attempts a fresh problem.

**Delivery class**:
How a study session runs: Standard (teaching) or Urgent (exam-focused drilling). Set by exam proximity unless the student chooses.
_Avoid_: Normal mode

**Key decision**:
A step where a plausible wrong choice gives a different final answer.
_Avoid_: Meaningful moment

**Level**:
One of three named settings on a teaching-preference axis.

**Transition**:
A move between two adjacent levels on one axis. Probe rejections are counted per transition.

**Provenance**:
Where a saved preference level came from: default, sampler, learned, explicit or legacy.

**Standing instruction**:
An explicit, lasting student request about how to teach, such as "always explain first". Not probed against.
_Avoid_: Temporary request

**Comfortable engagement**:
The student is answering and participating without pushback or signs of frustration; the precondition for starting a probe.

**Recipe**:
In Urgent, the short exam-sufficient method for a question type, shown before an application question.

**Session**:
One `started:` record in a course log. Preference evidence also requires different calendar days.
