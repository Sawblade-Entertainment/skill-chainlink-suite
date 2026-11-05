# Getting started

## Prerequisites

- [Claude Code](https://claude.com/claude-code)
- A Roblox project managed by ChainLink (a `chain.toml` at the root). Create one with `chainlink init`.
- For Blink and Vide: the tools pinned in `chain.toml`.

## Install the skills

A skill is a folder containing `SKILL.md`. Put it in a skills directory:

| Location | Scope |
|---|---|
| `.claude/skills/<name>/` | This project (commit it to share with your team) |
| `~/.claude/skills/<name>/` | All your projects |

```sh
# project-level
mkdir -p .claude/skills
cp -r skills/* .claude/skills/

# or personal, kept in sync with this repo via symlinks
mkdir -p ~/.claude/skills
for s in skills/*/; do ln -s "$PWD/$s" ~/.claude/skills/$(basename "$s"); done
```

Install only the skills you need; they are independent.

## Using a skill

Claude loads a skill when your request matches its `description`:

| Say something like | Skill |
|---|---|
| "Add a DataService that saves coins on leave" | `chainlink` |
| "Add a remote event for boat input" | `blink` |
| "Build a countdown HUD" | `vide` |
| "Make a tree prefab as an .rbxmx" | `roblox-builder` |

You can also invoke one explicitly: `/chainlink`, `/blink`, `/vide`, `/roblox-builder`.

## Pin tool versions

The skills assume versions are pinned in `chain.toml`:

```toml
[Tools]
Blink = "1Axen/blink@0.18.9"

[Packages]
vide = "centau/vide@0.4.1"
```

Add them with `chainlink add`:

```sh
chainlink add 1Axen/blink@0.18.9 --tool
chainlink add centau/vide@0.4.1 --package
chainlink install
```
