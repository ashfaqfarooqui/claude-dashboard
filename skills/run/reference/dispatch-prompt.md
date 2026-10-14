# Dispatch prompt

Keep it short: the rules live in `AGENT_PROMPT.md`, the task lives in the issue file. The prompt
only points at them, with **absolute paths**.

```
You are working on one issue in <absolute repo path or worktree path>.

Your task is <ISSUE-ID> and nothing else. Read these first, in order:
1. <plans dir>/AGENT_PROMPT.md — the rules; follow its prompt template section as your brief
2. <plans dir>/<ISSUE-ID>-<slug>.md — your issue; read it to the bottom
3. <plans dir>/FINDINGS.md — only the findings your issue cites
4. The SKILL.md of each skill your issue lists under **Skills:** — paths are in
   AGENT_PROMPT.md, section *Skills*

<Only if applicable — decisions, never rule overrides:>
Decision D<n> overrides part of your issue: <one line>.

<Only for worktree / parallel modes:>
You are in worktree <path> on branch <branch>. Commit there; do not touch other worktrees.
  — or —
Do not commit. Leave your changes unstaged; the orchestrator stages by path.

When done, report using the reporting template at the bottom of AGENT_PROMPT.md.
```

## Choices at dispatch

- **Model:** the one in the issue header. If you deviate, say why in the Log line.
- **Agent type:** `general-purpose` for code changes. Use a read-only type (`Explore`) only for
  analysis-only issues.
- **Background:** fine for subagents — you are notified when they finish. Do not poll.

## Anti-patterns seen in past campaigns

- "Read AGENT_PROMPT.md in the repo root" → the agent could not find it. Absolute paths only.
- "Ignore the attribution rule in AGENT_PROMPT.md" in every dispatch → one missed override is a
  wrong commit. Fix the file.
- Pasting the whole issue into the prompt → the agent skips the dated appendices in the file.
- No skills named → a Sonnet agent wrote blog posts in a generic voice and vault notes with the
  wrong category. Subagents only follow skills they are told to read.
- A bare suite count ("471 passed") with no command → the agent chases a phantom regression.
