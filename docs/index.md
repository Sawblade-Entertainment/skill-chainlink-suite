# ChainLink Skill Suite

Claude Code skills for building Roblox games with [ChainLink](https://github.com/Sawblade-Entertainment/tool-chainlink).

Each skill is a single `SKILL.md` that gives Claude accurate, version-pinned knowledge of one tool: the commands that exist, the syntax that compiles, and the mistakes to avoid.

## The skills

| Skill | Purpose | Page |
|---|---|---|
| `chainlink` | CLI, `chain.toml`, sync layout, Services/Controllers, macros, assets and place publishing | [ChainLink](chainlink.md) |
| `blink` | Typed networking with Blink v0.18.x | [Blink](blink.md) |
| `vide` | Reactive Roblox UI with Vide | [Vide](vide.md) |
| `roblox-ui-design` | UX/UI design rules and review checklist for Roblox interfaces | [Roblox UI Design](roblox-ui-design.md) |
| `roblox-builder` | Generate and validate `.rbxmx` models | [Roblox Model XML](roblox-builder.md) |
| `chainlink-model` | Model, texture, rig and export 3D assets with Blender, then verify the import in Studio | [ChainLink Model](chainlink-model.md) |

## Where to start

1. [Install the skills](getting-started.md).
2. Read the page for the skill you need, or [how they combine](workflow.md).
3. Ask Claude for what you want; the matching skill loads automatically.

## Design principles

- **Verified over remembered.** Skills tell Claude to copy existing working code and compile or lint after every change.
- **Version-pinned.** Each skill names the version it targets and says what to do when the project pins something else.
- **Compact.** Skills are short reference sheets, not tutorials, so they load cheaply into context.
