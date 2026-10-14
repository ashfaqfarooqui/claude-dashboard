#!/usr/bin/env python3
"""Check the prose of a Markdown file against the measurable rules of ASD-STE100 (Issue 9, 2025).

Checks sentence length, paragraph length, passive voice, present perfect, complex verb groups and
trailing -ing clauses. It does not check the STE dictionary (about 900 approved words); that part
is the writer's job. Code, tables, headings, frontmatter, HTML comments and Mermaid blocks are skipped.

Prints one line per violation (`line: rule: excerpt`) and a count. Exit 1 if there are violations.
Usage: ste_check.py FILE [--max N]   (--max limits how many lines it prints, default 40)
"""

import re
import sys

DESCRIPTIVE_MAX = 25  # STE rule 5.1: descriptive sentences
PROCEDURAL_MAX = 20  # STE rule 4.1: instructions
PARAGRAPH_MAX = 6  # STE rule 6.6

BE = r"(?:is|are|was|were|be|been|being)"
IRREGULAR = (
    "built done made given written taken known shown seen found kept left held set put run sent "
    "split read chosen drawn driven broken hidden spent told thought brought caught paid lost met"
).split()
PARTICIPLE = rf"(?:\w+ed|(?:re|un|over|out)?(?:{'|'.join(IRREGULAR)}))"
RULES = [
    ("passive voice", re.compile(rf"\b{BE}\s+(?:\w+ly\s+)?{PARTICIPLE}\b(?!\s+(?:to|than))", re.I)),
    ("present perfect", re.compile(rf"\b(?:has|have|hasn't|haven't)\s+(?:\w+ly\s+)?{PARTICIPLE}\b", re.I)),
    ("complex verb group", re.compile(r"\b(?:would|could|should|might|may|must|will)\s+(?:have|be)\s+\w+(?:ed|en|ing)\b", re.I)),
    ("trailing -ing clause", re.compile(r",\s+(?:thus\s+|thereby\s+)?\w{3,}ing\b", re.I)),
]
WORD = re.compile(r"[A-Za-z0-9][\w'’/-]*")


def prose_blocks(text: str):
    """Yield (first line number, paragraph text, is_list_item) for prose only."""
    blank = lambda m: "\n" * m.group(0).count("\n")  # keep line numbers
    text = re.sub(r"\A---\n.*?\n---\n", blank, text, flags=re.S)  # YAML frontmatter
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    in_fence, buf, start = False, [], 0
    for n, raw in enumerate(text.splitlines() + [""], 1):
        line = raw.strip()
        if line.startswith(("```", "~~~")):
            in_fence = not in_fence
            line = ""
        skip = in_fence or line.startswith(("#", "|", ">")) or re.fullmatch(r"[-*_]{3,}", line or "x")
        item = re.match(r"(?:[-*+]|\d+\.)\s+", line)
        if not line or skip or item:
            if buf:
                yield start, " ".join(buf), False
                buf = []
            if item and not skip:
                yield n, line[item.end():], True
            continue
        if not buf:
            start = n
        buf.append(line)


def sentences(text: str) -> list[str]:
    text = re.sub(r"`[^`]*`", "CODE", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\b(?:e\.g|i\.e|etc|vs)\.", "x", text)
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9`*\"(])", text) if WORD.search(s)]


def check(text: str) -> list[str]:
    out = []
    for line, para, is_item in prose_blocks(text):
        sents = sentences(para)
        if not is_item and len(sents) > PARAGRAPH_MAX:
            out.append(f"{line}: paragraph has {len(sents)} sentences (max {PARAGRAPH_MAX})")
        for s in sents:
            words = WORD.findall(re.sub(r"\*\*[^*]+:\*\*", "", s))
            limit = PROCEDURAL_MAX if is_item else DESCRIPTIVE_MAX
            if len(words) > limit:
                out.append(f"{line}: sentence has {len(words)} words (max {limit}): {' '.join(words[:8])} …")
            for name, rx in RULES:
                if m := rx.search(s):
                    out.append(f"{line}: {name}: …{m.group(0)}…")
    return out


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    limit = int(args[args.index("--max") + 1]) if "--max" in args else 40
    path = next(a for a in args if not a.startswith("--") and not a.isdigit())
    found = check(open(path, encoding="utf-8").read())
    for f in found[:limit]:
        print(f)
    if len(found) > limit:
        print(f"… {len(found) - limit} more")
    print(f"{len(found)} STE violation{'s' if len(found) != 1 else ''}")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
