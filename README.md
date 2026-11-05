# ChainLink Skill Suite

A collection of [Claude Code](https://claude.com/claude-code) skills for building Roblox games with [ChainLink](https://github.com/Sawblade-Entertainment/ChainLink), Sawblade Entertainment's tool/package manager, Studio sync server and Luau flavor.

Each skill teaches Claude the exact conventions, CLI flags and pitfalls of one tool, so it writes code that compiles and matches the project instead of guessing from memory.

## Skills

| Skill | Covers | Use when |
|---|---|---|
| [`chainlink`](skills/chainlink/SKILL.md) | The `chainlink` CLI, `chain.toml`, sync layout, Services/Controllers, `use`/`new` macros | Editing a project with a `chain.toml` |
| [`blink`](skills/blink/SKILL.md) | [Blink](https://1axen.github.io/blink) v0.18.x `.blink` networking definitions and the generated Luau modules | Adding remote events/functions |
| [`vide`](skills/vide/SKILL.md) | [Vide](https://centau.github.io/vide) reactive UI: sources, derives, effects, mounting | Writing Roblox UI |
| [`roblox-builder`](skills/roblox-builder/SKILL.md) | Generating and validating `.rbxmx` models from a hierarchy or JSON spec, with a Python helper | Creating prefabs, parts or scripts as importable files |

The skills are designed to work together: ChainLink provides the project structure and lifecycle, Blink provides typed networking between `server/` and `client/`, and Vide provides UI driven by Controllers.

## Installation

Skills are folders containing a `SKILL.md`. Copy or symlink the ones you want into a skills directory.

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

Claude loads a skill automatically when your request matches its description, or you can invoke one directly with `/chainlink`, `/blink`, `/vide` or `/roblox-builder`.

## Repository layout

```
skills/
  chainlink/         ChainLink skill
  blink/             Blink skill
  vide/              Vide skill
  roblox-builder/    Roblox Model XML skill + build_rbxmx.py helper
docs/                Documentation site source (MkDocs)
mkdocs.yml           Documentation site config
```

## Documentation

Full documentation lives in [`docs/`](docs/index.md):

- [Getting started](docs/getting-started.md)
- [ChainLink skill](docs/chainlink.md)
- [Blink skill](docs/blink.md)
- [Vide skill](docs/vide.md)
- [Roblox Model XML skill](docs/roblox-builder.md)
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

## License

Add a license before publishing.
