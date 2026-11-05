# Contributing

## Skill format

Each skill is a directory containing a `SKILL.md` with YAML frontmatter:

```markdown
---
name: blink
description: What it does. Use when <trigger conditions>.
---

# Title
...
```

- `name` matches the directory name.
- `description` decides when Claude loads the skill. State both the capability and the triggers.
- Keep the body compact: tables for reference, short code samples, explicit rules and pitfalls.

## Guidelines

- Only document what has been verified against the tool's real behavior, including the failure cases ("`"Camel"` is wrong").
- Name the version targeted and say what to do on a mismatch.
- Prefer instructing Claude to copy known-good project code and to compile/lint after edits.
- When a tool changes, update both the skill and its page in `docs/`.

## Building the docs

```sh
pip install mkdocs mkdocs-terminal mkdocs-minify-plugin
mkdocs serve    # live preview
mkdocs build    # outputs ./site
```
