---
name: ste
description: Write in Simplified Technical English (ASD-STE100), about 80 % of the way, and check the result with scripts/ste_check.py. The language for every campaign file (DESIGN.md, FINDINGS.md, MASTER.md, issues, AGENT_PROMPT.md, agent reports) and for the docs, READMEs, PR bodies and commit messages that campaign agents write.
when_to_use: Whenever a campaign skill or a campaign agent writes prose a person or an agent reads, or when the user asks for STE, "simplified technical English", "ASD-STE100", "aircraft-manual English". Not for code or code comments.
argument-hint: "[file to check]"
---

# Simplified Technical English (ASD-STE100)

Write so the reader understands on the first read. ASD-STE100 (Issue 9, 2025) is a controlled
language from aerospace maintenance manuals. Karpathy recommends it for LLM output, "80 % of the
way", because the full specification is strict (post of 2026-10-02,
https://x.com/karpathy/status/2105819303471976479).

## Rules

- One topic in each paragraph. Not more than six sentences in each paragraph.
- Not more than 20 words in an instruction. Not more than 25 words in a descriptive sentence.
- One instruction in each sentence. Put a condition before the instruction ("If the gate fails,
  stop.").
- Use the active voice. Use the passive only when you do not know who does the action.
- Use the simple present, simple past or simple future. Do not use the present perfect
  ("has changed" → "changed").
- Do not use complex verb groups ("should have been done" → "do it").
- Use an -ing word only as a noun or in a noun. No trailing clauses like ", thus making …".
- Use one word for one meaning. When you name a thing, keep that name. Do not use synonyms.
- Do not make noun clusters of more than three words. Use "of" or a short phrase.
- Do not leave out words to save space (articles, verbs, subjects).
- Use vertical lists for complex text and for steps.
- Start a warning with the command or the condition: "Do not run `cargo clean`. The only copy
  of the ledger is in `target/`."
- Use the technical names of the project (tools, files, functions, flags) unchanged. They are
  not STE words, but they are correct.

"80 %" means: break a rule when the rule makes a sentence less clear. Do not break a rule to
sound natural or to save words.

## Check

You overrate your own compliance. Before you hand over a file you wrote, run:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ste/scripts/ste_check.py <file.md>
```

It prints one line for each violation and a count. Exit 1 means there are violations. It checks
the measurable rules: sentence length, paragraph length, passive voice, present perfect, complex
verb groups and trailing -ing clauses. It skips code, tables, headings, frontmatter, HTML
comments and Mermaid blocks. It does not check the STE dictionary of approved words; that part
is your job.

Fix each violation, or keep it on purpose under the 80 % rule. In a report, give the count
before and after (`STE check: 7 → 0`), not the full output.

## Pictures

A picture is often clearer than STE text. In a Markdown file that the campaign dashboard shows:

- Use a Mermaid block (```` ```mermaid ````) for structure: parts and links, data flow, states,
  steps, the options of a decision.
- Put images in the campaign's `assets/` folder and link them with a relative path.
- Write one or two sentences under each picture that tell what it shows. A picture never holds
  a fact alone.
- Do not write SVG or HTML by hand. Do not open your own images to check them; check the source.
