---
name: brainstorm
description: Turn a rough idea into an agreed design brief DESIGN.md in ~/.claude/plans/<slug>/ through a questioning dialogue that challenges the idea instead of polishing it — one question at a time until every item on the clarity checklist is settled or parked as a D<n> decision. Optional first step before campaign:plan; the counterpart of campaign:audit for ideas rather than existing code.
when_to_use: When the user has an idea, feature, tool or project they want to shape before anything is built — "brainstorm X", "I have an idea for…", "help me think through…", "poke holes in this", "is this worth building?". Not for finding out what is wrong with existing code (campaign:audit) or for work that is already concrete (campaign:plan).
argument-hint: "[slug] [the idea, in a sentence]"
---

# campaign:brainstorm

Output: `~/.claude/plans/<slug>/DESIGN.md`, in the format defined in
`${CLAUDE_SKILL_DIR}/../plan/reference/format.md` (read its *Design brief* section
first), from the template `${CLAUDE_SKILL_DIR}/../plan/templates/DESIGN.md`.

Arguments: `$ARGUMENTS`

## Stance

The goal is a good outcome, not a happy user. A brainstorm that ends with the idea unchanged
has probably failed.

- **Say what you think is wrong.** Every proposal from the user gets the strongest objection
  you can find before it gets agreement. "That could work" with no objection attached means
  you have not looked hard enough yet.
- **No praise, no softening openers.** Do not start a reply with "Great idea", "Love it",
  "That makes sense". Start with the substance.
- **Change position on arguments, not on insistence.** If the user repeats a view without new
  information, keep your objection and say why. If they give a reason or evidence, say whether
  it answers the objection, and update if it does. Do not pretend to be persuaded.
- **The user decides.** When you still disagree after the user has heard the argument, say so
  once more in one line, record it under *Disagreements* in DESIGN.md, and go with their
  call. Do not reopen it every turn.
- **"Don't build it" and "build something smaller" are valid outcomes.** So is "this already
  exists". Check before the user invests in it.
- **Ground claims.** What the repo does is checked by reading it. What a third-party tool can
  do is checked in its docs for the version in use, and cited. Say which statements are your
  guesses.

## Language and pictures

The user reads a lot of model output. Make it fast to read.

**Write in Simplified Technical English (ASD-STE100), about 80 % of the way.** This applies to
your questions, your objections and all of DESIGN.md. Read `${CLAUDE_PLUGIN_ROOT}/skills/ste/SKILL.md` and
follow it, and run its checker on DESIGN.md before each handover:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ste/scripts/ste_check.py ~/.claude/plans/<slug>/DESIGN.md
```

Do not paste the checker output to the user.

**Show it when a picture is clearer than text.** The campaign dashboard renders DESIGN.md, so
you are not limited to text:

- **Mermaid** in a ```` ```mermaid ```` block for structure: the parts and how they connect, a
  data flow, a state machine, a sequence of steps, the options in a decision. This is the
  default. It is cheap to write and an agent can still read it.
- **Tables** to compare alternatives and risks.
- **Images** in `~/.claude/plans/<slug>/assets/`, linked with a relative path
  (`![What it shows](assets/flow.png)`). Use them only for things that are visual: a
  screenshot, a UI sketch, a plot that a script made.

Rules for pictures:

- A picture never holds a fact alone. Write one or two sentences under it that tell what it
  shows. Diagrams can hide gaps; the sentences make the gaps visible.
- Do not write SVG or HTML by hand. It costs many tokens and the dashboard does the HTML.
- Do not open your own images to check them. Each image costs many tokens to read. Check the
  script or the Mermaid source.
- In the chat, a short Mermaid block or a table is fine when it answers the question faster
  than prose.

## 1. Frame

- Restate the idea in two or three sentences, separating **what the user said** from **what
  you are assuming**. Ask them to correct it.
- Agree the `<slug>`. If `~/.claude/plans/<slug>/DESIGN.md` exists, this is a **resume**:
  read it, summarise where it stopped (open checklist items, open D<n>), and continue from
  there.
- If there is a repo, read the parts the idea touches (entry points, the flow being changed,
  recent commits) before asking anything a quick read would answer.
- **Size it, out loud.** If the idea is a small change to existing code, say so and suggest
  skipping the campaign: a short in-chat design and plain implementation is enough. If it is
  several independent systems, say so and pick one to brainstorm first; the rest go into
  DESIGN.md as *Later*.

Write DESIGN.md now with what you have, and keep it current as you go (§4). A brainstorm that
lives only in the chat is lost at the next `/clear`.

## 2. Question until clear

Work through the **clarity checklist** below. Each turn:

1. Respond to the user's last answer: what it settles, and what is wrong with it if anything is.
2. Ask **one** question, the one whose answer changes the design most. Use `AskUserQuestion`
   when the answers are a small set of options (put your recommendation first, marked
   *(Recommended)*); plain text for open questions.
3. When the turn moved the brief, update DESIGN.md.

Do not batch questions. Do not ask what the repo, the docs or the earlier answers already
answer. Do not ask about implementation detail while the purpose is still unclear.

**Clarity checklist** — the brainstorm is done when each item is settled or parked as `D<n>`:

| Item | Settled when |
|---|---|
| Problem | Stated as a problem someone has today, not as the solution. With an example of it happening. |
| Who and why now | Who has the problem, how often, and what they do about it today. |
| Success | A check someone can run or observe, not "it works well". What would make this a failure? |
| Constraints | Time, cost, tools, compatibility, things that must not change. |
| Scope and non-goals | What is in, and what is explicitly out. |
| Approach | Chosen over at least two real alternatives, one of which is "do nothing / use what exists". |
| Risks | The pre-mortem (below) is answered: each risk has a mitigation or is accepted by name. |
| Verification | How each part of the design would be shown to work — the seed of campaign:plan's acceptance criteria. |

Unknowns that need facts rather than opinions (does the library support X? how slow is the
current path?) are not settled by asking the user. Find out — read the code, read the docs,
run a quick probe in the scratchpad — and say what you did. If finding out is real work, park
it as a `D<n>` or suggest `/campaign:audit` for it.

## 3. Challenge the approach

When the checklist is mostly settled, before writing the approach down:

- **Alternatives.** Present two or three approaches with their trade-offs, your recommendation
  first and why. Include the cheapest one that would solve most of the problem. Cut features
  the success criteria do not need.
- **Pre-mortem.** "It is six months from now and this failed. Why?" Give the three most likely
  reasons, and ask the user which they think is most likely. Each becomes a risk with a
  mitigation, or an accepted risk.
- **Steelman the opposite.** One paragraph making the best case against building this at all.
  If the user cannot answer it, that goes into DESIGN.md as an open risk, not into the bin.

Present the chosen design in short sections (what it is, the parts and how they connect, what
happens when something fails, how it is tested) and get agreement on each before moving on.

## 4. Write DESIGN.md

DESIGN.md is a working document for the user and for agents. Write it in STE (see
*Language and pictures*). Put a Mermaid diagram in *Approach* when the design has more than two
parts.

- Every checklist item has a section. Anything still open is a `D<n>` with the options and
  your recommendation, not a "TBD" in the prose.
- *Alternatives considered* records what was rejected and why, so it is not re-proposed later.
- *Disagreements* records where you objected and the user chose otherwise, with both
  positions in one line each. Empty is fine; omitting the section is not.
- Before handing over, reread it for contradictions, words that could be read two ways, and
  anything that is a wish rather than a checkable statement. Fix them inline. Then run
  `ste_check.py` on it.

## 5. Hand over

Show the user: the one-paragraph summary, the open `D<n>`, the disagreements, and your honest
verdict (build it / build the smaller version / don't build it), with the reason. Ask them to
review DESIGN.md before anything else happens.

Then suggest the next step: `/campaign:plan <slug>` to turn it into issues, `/campaign:audit
<slug>` if a factual question about existing code is blocking, or nothing if the verdict was
not to build. Do not write issues or code from this skill.
