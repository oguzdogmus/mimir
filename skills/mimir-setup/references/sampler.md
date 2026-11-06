# Teaching-style sampler (setup step 6)

Quick everyday demonstrations, one teaching setting at a time. The student picks a style; nobody solves the example tasks. This is not the knowledge gauge: no course material, nothing graded, nothing written to `mastery.md` or a log.

1. Run only the sections named in `remaining` from `session.py prefs`, in that order. Each gets one message: its lead line, its three options exactly as written (the bold letter and the quoted text, without the level in brackets), then "Which suits you: A, B or C?" and wait. Nothing else in that message: no preview of the next section and no readiness question.
2. The reply names A, B or C, or describes one of them: run `python3 "<mimir>/scripts/session.py" pref-event` with `{"event": "sampler", "axis": "<section name>", "level": "<the level in that option's brackets>"}` and print its `line` verbatim. "Don't mind", "either" or "the middle one" picks B. Then show the next section in the same message.
3. After the last section, its `line` is the tentative summary. Go straight on to setup step 7: no confirmation question.
4. "Skip", "stop" or "no more" at any point ends the sampler: run `pref-event` with `{"event": "sampler-skip"}`, print its `line` verbatim and go on to setup step 7. Choices already made stay; unanswered settings keep their defaults.
5. The questions inside the options are illustrations. If the student answers one, say "That's just the example. Which style suits you: A, B or C?"

## support

Lead: "How much explanation do you want before you try? Same small task each time: a 15% tip on a €40 bill."

**A** (`example-first`) "First a different one, fully worked: 15% of €30. 10% is €3, half of that is €1.50, so €4.50. Now yours."
**B** (`method-first`) "The method: take 10%, then add half of that again. Now yours."
**C** (`try-first`) "Try it first and tell me how far you get. I'll help where it goes wrong."

None of the three gives this bill's answer.

## frequency

Lead: "How often should I ask you something while explaining? Same task each time: when to leave for a 9:00 train, with a 25-minute walk and 5 minutes spare at the station. All three end in the same place."

**A** (`checks only`) "25 minutes of walking plus 5 spare is 30. 30 minutes before 9:00 is 8:30. Your turn: a 10:15 bus with a 20-minute walk and 5 minutes spare."
**B** (`key decisions`) "The walk is 25 minutes. What else goes into the total? (You: the 5 spare.) So 30 minutes, and you leave at 8:30. Your turn: a 10:15 bus with a 20-minute walk and 5 minutes spare."
**C** (`every step`) "How long is the walk? (You: 25.) Anything to add? (You: 5 spare.) So the total? (You: 30.) So when do you leave? (You: 8:30.) Your turn: a 10:15 bus with a 20-minute walk and 5 minutes spare."

Each option shows the same working and ends on the same check; only when the questions come differs.

## depth

Lead: "What kind of question should I ask? Same moment each time: you doubled a cookie recipe, so 2 eggs became 4."

**A** (`next step`) "The recipe also has 150 g of sugar. How much now?"
**B** (`why`) "Why does every ingredient double, not just the eggs?"
**C** (`what-if`) "Once your doubled list is done: with only 3 eggs, how much of the original recipe could you make?"
