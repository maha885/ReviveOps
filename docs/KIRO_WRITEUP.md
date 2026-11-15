# How Kiro was used in ReviveOps — draft

> Draft for the Kiroween write-up. Everything below is something that exists in the
> repository. Lines marked **[YOU FILL]** need your own experience — write what
> actually happened, and delete anything you did not do.

## Kiro apps used
- Kiro IDE (editor and terminal). **[YOU FILL: did you try the CLI, Web or Crew? If not, say so.]**

## Spec-driven development
- `.kiro/specs/reviveops/requirements.md`, `design.md` and `tasks.md` describe the product, architecture, and a phase-by-phase task list (foundation → scanner → intelligence → revival → submission).
- `tasks.md` is updated only for verified work, so it doubles as a progress log.
- The foundation, scanner, scoring, checklist, persistence and report features were implemented in Kiro from these specs. **[YOU FILL: how did working from a spec compare to just prompting? What went better or worse? Give one concrete example.]**

## Steering documents
- `.kiro/steering/product.md` — product principles: local-first, explainable, safe by default (inspect and recommend, never run repository commands), useful without AI, honest about heuristics.
- `.kiro/steering/tech.md` — technical conventions for the stack.
- These principles shaped real design decisions: the scanner never executes scanned code, and the Revive action writes only to a copy of the repository. **[YOU FILL: which steering instruction made the biggest difference to Kiro's output?]**

## Agent hooks
- `.kiro/hooks/pytest-on-save.json` — runs the backend test suite whenever a backend Python file is saved.
- Written by hand as a plain command hook (it does not use Kiro credits). **[YOU FILL: did it catch anything? Did it load in your Kiro version?]**

## Property-based testing
- `backend/tests/test_revive.py::test_plan_properties` uses Hypothesis to check that the revival planner is deterministic, never overwrites an existing file, and never emits code-marker words that would add new findings.
- This test was written outside the Kiro agent. **[YOU FILL: did property testing find anything unit tests missed? If not, say so.]**

## Not used
- Custom agents, MCP servers, Kiro powers and Kiro Crew were not used in this project. **[YOU FILL: edit this line if that changes before you submit.]**

## Honest division of work
- Kiro: foundation, scanner, scoring, checklist, persistence, report, and the first UI. **[YOU FILL: confirm]**
- Other AI assistance plus the Kiro editor: the Revive action, its tests, the score-transparency fix, the UI polish, the README, and the hook.
