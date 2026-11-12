# ChainLink Skill Suite

A collection of [Claude Code](https://claude.com/claude-code) skills for building Roblox games with [ChainLink](https://github.com/Sawblade-Entertainment/tool-chainlink), Sawblade Entertainment's tool/package manager, Studio sync server and Luau flavor.

Each skill teaches Claude the exact conventions, CLI flags and pitfalls of one tool, so it writes code that compiles and matches the project instead of guessing from memory.

## Skills

| Skill | Covers | Use when |
|---|---|---|
| [`chainlink`](skills/chainlink/SKILL.md) | The `chainlink` CLI, `chain.toml`, sync layout, Services/Controllers, `use`/`new`/`asset` macros, Open Cloud asset upload and place publishing | Editing a project with a `chain.toml` |
| [`blink`](skills/blink/SKILL.md) | [Blink](https://1axen.github.io/blink) v0.18.x `.blink` networking definitions and the generated Luau modules | Adding remote events/functions |
| [`vide`](skills/vide/SKILL.md) | [Vide](https://centau.github.io/vide) reactive UI: sources, derives, effects, mounting | Writing Roblox UI |
| [`roblox-ui-design`](skills/roblox-ui-design/SKILL.md) | UX/UI design guidance: layout, spacing, color, motion, accessibility, cross-platform rules, review checklist | Designing or reviewing any Roblox UI (pairs with `vide`) |
| [`roblox-builder`](skills/roblox-builder/SKILL.md) | Generating and validating `.rbxmx` models from a hierarchy or JSON spec, with a Python helper | Creating prefabs, parts or scripts as importable files |
| [`chainlink-model`](skills/chainlink-model/SKILL.md) | 3D modeling in Blender (via the Blender MCP or headless): generator scripts, baked textures and PBR, rigid and skinned rigs, FBX export into `assets/`, upload and a Studio import check | Creating or changing characters, props, stage pieces or VFX meshes |

The skills are designed to work together: ChainLink provides the project structure and lifecycle, Blink provides typed networking between `server/` and `client/`, and Vide provides UI driven by Controllers, and Roblox UI Design guides how that UI should look and behave. ChainLink Model produces the 3D art that `chainlink assets` uploads and the `asset` macro references.
| [`roblox-performance`](skills/roblox-performance/SKILL.md) | Streaming, part/instance budgets, MicroProfiler habits, memory leaks (undisconnected connections), network update rates | Diagnosing lag, memory growth, ping, or reviewing code for performance |
| [`roblox-monetization`](skills/roblox-monetization/SKILL.md) | Game passes, developer products, idempotent `ProcessReceipt`, Premium benefits and payouts | Adding or reviewing anything that takes Robux |

The skills are designed to work together: ChainLink provides the project structure and lifecycle, Blink provides typed networking between `server/` and `client/`, and Vide provides UI driven by Controllers, and Roblox UI Design guides how that UI should look and behave. Roblox Performance keeps all of it within frame, memory and bandwidth budgets, and Roblox Monetization makes sure purchases are granted exactly once.

## Installation

Skills are folders containing a `SKILL.md`. Copy or symlink the ones you want into a skills directory.

**Install scripts** (copy all skills, or name the ones you want):

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
.\scripts\install.ps1 -Link vide     # symlink one skill (needs Developer Mode or admin)
```

Options: `--project`/`-Project`, `--target DIR`/`-Target DIR`, `--link`/`-Link`, `--force`/`-Force` (replace existing). Existing skills are skipped unless forced.

Or copy manually:

**Per project** (shared with your team via version control):

```sh
mkdir -p .claude/skills
cp -r skills/* .claude/skills/
```

**Personal** (available in every project):

```sh
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/
```

Symlink instead of copying (`ln -s "$PWD/skills/chainlink" ~/.claude/skills/chainlink`) to keep them up to date with this repository.

<<<<<<< HEAD
Claude loads a skill automatically when your request matches its description, or you can invoke one directly with `/chainlink`, `/blink`, `/vide`, `/roblox-ui-design`, `/roblox-builder` or `/chainlink-model`.
=======
Claude loads a skill automatically when your request matches its description, or you can invoke one directly with `/chainlink`, `/blink`, `/vide`, `/roblox-ui-design`, `/roblox-builder`, `/roblox-performance` or `/roblox-monetization`.
>>>>>>> bdb1406d678b1c780d643ebc479a9de16e9118d2

## Repository layout

```
skills/
<<<<<<< HEAD
  chainlink/         ChainLink skill
  blink/             Blink skill
  vide/              Vide skill
  roblox-ui-design/  Roblox UI design guidance
  roblox-builder/    Roblox Model XML skill + build_rbxmx.py helper
  chainlink-model/   Blender modeling skill + clmodel.py helper, example and references
scripts/             install.sh / install.ps1
docs/                Documentation site source (MkDocs)
mkdocs.yml           Documentation site config
=======
  chainlink/            ChainLink skill
  blink/                Blink skill
  vide/                 Vide skill
  roblox-ui-design/     Roblox UI design guidance
  roblox-builder/       Roblox Model XML skill + build_rbxmx.py helper
  roblox-performance/   Roblox performance guidance
  roblox-monetization/  Roblox monetization guidance
scripts/              install.sh / install.ps1
docs/                 Documentation site source (MkDocs)
mkdocs.yml            Documentation site config
>>>>>>> bdb1406d678b1c780d643ebc479a9de16e9118d2
```

## Documentation

Full documentation lives in [`docs/`](docs/index.md):

- [Getting started](docs/getting-started.md)
- [ChainLink skill](docs/chainlink.md)
- [Blink skill](docs/blink.md)
- [Vide skill](docs/vide.md)
- [Roblox UI Design skill](docs/roblox-ui-design.md)
- [Roblox Model XML skill](docs/roblox-builder.md)
<<<<<<< HEAD
- [ChainLink Model skill](docs/chainlink-model.md)
=======
- [Roblox Game Design](docs/roblox-game-design.md)
- [Roblox Performance skill](docs/roblox-performance.md)
- [Roblox Monetization skill](docs/roblox-monetization.md)
>>>>>>> bdb1406d678b1c780d643ebc479a9de16e9118d2
- [Using the skills together](docs/workflow.md)
- [Contributing](docs/contributing.md)

Preview locally:

```sh
pip install mkdocs mkdocs-terminal mkdocs-minify-plugin
mkdocs serve
```

## Version compatibility

| Tool | Version targeted |
|---|---|
| ChainLink | early development; use only documented flags and keys |
| Blink | 0.18.x (v1 pre-releases use incompatible syntax) |
| Vide | 0.4.x |
<<<<<<< HEAD
| Blender (`chainlink-model`) | verified on 5.3; helper written for 4.2+ |

## License

Add a license before publishing.
=======
>>>>>>> bdb1406d678b1c780d643ebc479a9de16e9118d2
