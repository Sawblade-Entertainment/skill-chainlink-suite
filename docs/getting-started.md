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

### Install scripts

With no skill names, all skills are installed. The default target is `~/.claude/skills`, so it doesn't matter where you run them from.

```sh
# macOS / Linux
./scripts/install.sh                 # into ~/.claude/skills
./scripts/install.sh --project       # into ./.claude/skills
./scripts/install.sh --link vide     # symlink one skill
```

```powershell
# Windows (PowerShell)
.\scripts\install.ps1                # into ~\.claude\skills
.\scripts\install.ps1 -Project       # into .\.claude\skills
.\scripts\install.ps1 -Link vide     # symlink (needs Developer Mode or admin)
```

| Unix | PowerShell | Meaning |
|---|---|---|
| `-p`, `--project` | `-Project` | Install to `./.claude/skills` instead of `~/.claude/skills` |
| `-t`, `--target DIR` | `-Target DIR` | Install to `DIR` |
| `-l`, `--link` | `-Link` | Symlink instead of copy |
| `-f`, `--force` | `-Force` | Replace existing skills |

With `--project`, the target is relative to the directory you run the script from, so run it from your game project.

### Manually

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
| "Review this shop screen's design" | `roblox-ui-design` |
| "Make a tree prefab as an .rbxmx" | `roblox-builder` |

You can also invoke one explicitly: `/chainlink`, `/blink`, `/vide`, `/roblox-ui-design`, `/roblox-builder`.

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
