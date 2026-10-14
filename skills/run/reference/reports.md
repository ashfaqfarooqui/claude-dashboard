# Reports

Two outputs the user asks for again and again. Use these shapes exactly, every time, so they can
be compared across sessions. Plain language throughout: name the behaviour, not the code
(STE, see `<plugin root>/skills/ste/SKILL.md`; no issue-ID shorthand in the prose).

## `status`

Read `MASTER.md` and the issue headers; check claimed commits with `git log` (step 1 of the
skill). Then print:

```
## <slug> — <done>/<total> done · wave <current wave> · usage <usage.py line>

| ID | What it fixes | Model | Wave | State | Waiting on |
|----|---------------|-------|------|-------|------------|
| <PFX>-NN | <one plain line> | sonnet | 2 | ☐ ready | — |
| <PFX>-NN | … | opus | 2 | ⊘ blocked | D4 |

**Next up:** <IDs eligible now, cheapest model first if usage is at caution>
**Needs you:** <open decisions D<n> with one line each, and anything under "Awaiting the user">
```

- Include every issue that is not `☑` or `✗`; end with one line counting the closed ones.
- *Waiting on* names the blocker: an issue ID, a decision `D<n>`, or "usage".

## `explain <ID>`

Read the issue to the bottom (dated appendices included) and the findings it cites, and open
the code it names. Then print:

```
## <ID> — <title in plain words>

**The problem.** <What goes wrong, for whom, and how you would notice. One short paragraph.>

**The fix.** <What changes and why that is the right place to change it.>

**Where else it can show up.** <Other places with the same pattern, with the command that finds
them — or "nowhere else", with the command that shows it.>

**If we fix it / if we don't.** <Impact each way: behaviour, risk, cost of waiting.>

**Model and effort.** <model> — <why that model, from the issue header>.

**What you need to decide.** <The open question, or "nothing — ready to dispatch".>
```
