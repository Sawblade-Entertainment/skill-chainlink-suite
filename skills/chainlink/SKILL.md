---
name: chainlink
description: Build Roblox games with ChainLink (Sawblade Entertainment's tool/package manager, Studio sync server and Luau flavor). Use when editing a Roblox project with a chain.toml, writing Services/Controllers, using the `use`/`new`/`asset` macros, uploading assets or publishing places with Open Cloud, or running the `chainlink` CLI.
---

# ChainLink

Tool/package manager, Studio sync server, Open Cloud uploader and Luau flavor (bootstrapper + `use`/`new`/`asset` macros). Source: `Sawblade-Entertainment/tool-chainlink`. Early development: back up before risky changes. Use only the CLI flags and `chain.toml` keys listed here.

## CLI

| Command | Purpose |
|---|---|
| `chainlink init` | `git init` if needed; scaffold `chain.toml`, `client/`, `server/`, `shared/`, `prefab/`, `assets/`, `.vscode/` |
| `chainlink install [-y]` | Install everything in `chain.toml`; asks before new downloads, `-y` skips (required without a terminal) |
| `chainlink add owner/repo@tag --tool` | Add a tool |
| `chainlink add scope/name@version --package` | Add a package |
| `chainlink remove <name>` | Remove a tool or package |
| `chainlink serve` | Live-sync server for the Studio plugin (port 8013) |
| `chainlink build <out>` | Build a place (`.rbxl`/`.rbxlx`) or `src/` as a model (`.rbxm`/`.rbxmx`) |
| `chainlink sourcemap [-o path]` | Sourcemap for luau-lsp |
| `chainlink login [--api URL --token T]` | Registry auth (GitHub device flow, or store a token) |
| `chainlink publish [--token T]` | Publish `src/` + `packages/` as a package (Wally-compatible, < 2 MB) |
| `chainlink login-cloud [--api-key K]` | Save a Roblox Open Cloud API key; prints the permissions it needs |
| `chainlink assets [--dry-run] [--api-key K]` | Upload new/changed files in `assets/` to Roblox |
| `chainlink publish-place [--place ID] [--draft] [--api-key K] [file]` | Publish a `.rbxl`/`.rbxlx` (or, with no file, a build of this project) to `[Roblox] PlaceId` |
| `chainlink self-install` | Install to `~/.chainlink/bin`, add to PATH, install Studio plugin |

- Prefer `add`/`remove` over hand-editing; pin exact versions.
- Flags go before positional arguments (`publish-place --draft game.rbxl`); flags after a file are treated as extra files.
- Registry tokens and the Open Cloud key live in `~/.chainlink/auth.toml`; never print or commit them. Key order: `--api-key`, then `ROBLOX_API_KEY` (use in CI), then `auth.toml`.
- `assets` and `publish-place` change live Roblox content: run `assets --dry-run` first and confirm with the user before uploading or publishing (`--draft` saves without publishing).
- **Tool proxying:** symlink the binary under a tool's name (`ln -s $(which chainlink) /usr/local/bin/selene`); running it resolves the version from `[Tools]` and auto-installs it.

## chain.toml

```toml
DisableBootstrap = false   # optional; true disables mod wrapping + bootstrapper

[Package]                  # publishing metadata; Name also maps src/ (below)
Name = "..."
Version = "0.1.0"          # optional: License, Description, Website

[Tools]
selene = "Kampfkarren/selene@0.32.0"

[Packages]
razorinput = "vibeonline/razorinput@0.1.0"   # -> ReplicatedStorage.packages.razorinput

[Roblox]                   # only for assets / publish-place
PlaceId = 1234567890       # publish-place target
UserId = 12345             # asset owner, or GroupId = ... (GroupId wins)
```

Packages sync to `ReplicatedStorage.packages.<last part of scope/name>`; names containing `.` are skipped.

## Sync layout

Defaults; override with `roots` (and `port`) in `chainlink.json`. Keep whatever folder names the project already uses.

| Dir / file | Roblox target |
|---|---|
| `client/` | `StarterPlayer.StarterPlayerScripts` (client bootstrapper) |
| `server/` | `ServerScriptService` (server bootstrapper) |
| `shared/` | `ReplicatedStorage.shared` |
| `prefab/` | `ServerStorage` |
| `src/` | `ReplicatedStorage.packages.<Package.Name>` when `src/init.luau` exists |
| `assets.lock.json` | `ReplicatedStorage.assets` (path → `rbxassetid://` map) |

File types: `.luau`/`.lua` → ModuleScript, `*.server.luau` → Script, `*.client.luau` → LocalScript, `.json` → ModuleScript, `.txt` → StringValue, `.rbxm`/`.rbxmx` → Model. `init.luau` becomes its folder's instance (not allowed at the root of `client/` or `server/`).

Every script gets `--!strict`, `--!native`, `--!optimize 2` prepended unless it already starts with `--!strict`, so write strict-typed Luau and don't add the flags yourself.

A `chainlink.json` root with `"package": true` makes the directory itself the target instance, like `src/`: `{ "roots": [{ "dir": "lib", "target": "ReplicatedStorage.lib", "package": true }] }`. Changing roots, `[Package] Name` or adding `src/init.luau` needs a `serve` restart.

## Services and Controllers

Files named `*Service.luau` / `*Controller.luau` are wrapped as `local mod = {} ... return mod`. Never write those lines or compiler flags; just attach to `mod`. The bootstrapper requires the top-level ModuleScripts in `server/`/`client/` and calls:

| Method | Side | When |
|---|---|---|
| `mod:init()` | both | Sync, in priority order, before any `start`; on error the module is dropped from all later hooks |
| `mod:start()` | both | After all `init`; each in its own thread |
| `mod:step(time, dt)` | both | `RunService.Stepped` |
| `mod:beat(dt)` | both | `RunService.Heartbeat` |
| `mod:draw(dt)` | client | `RunService.RenderStepped` |
| `mod:input(input, gameProcessed, phase)` | client | `UserInputService` Began/Ended/Changed; phase is `"began"`, `"ended"` or `"changed"` |
| `mod:playerAdded(player)` | server | Join (also players already present); own thread, may yield |
| `mod:playerRemoving(player)` | server | Leave; awaited at shutdown |
| `mod:characterAdded(player, char)` / `mod:characterRemoving(player, char)` | server | Character spawn/remove |
| `mod:close()` | server | `BindToClose`; all closes run in parallel, 25 s total |

`mod.priority = n`: lower inits first (default 0), ties by name. Keep `init` fast; cross-module work goes in `start`. `mod` may also hold state and plain functions (`mod.speed = 16`, `function mod.reset() end`).

```lua
-- server/DataService.luau
DataStoreService = use "DataStoreService"

function mod:playerAdded(player: Player)
    -- yielding is fine
end

function mod:close()
end
```

## Macros

Injected only when assigned from (`x = use ...`, `x.Texture = asset ...`), so always assign the result and put `use` lines at the top.

| Call | Resolves to |
|---|---|
| `use "./x"`, `use "../x"`, `use "@x"` | `require(...)` (relative to the script / Roblox alias) |
| `use "/a/b"` | `require(ReplicatedStorage.a.b)` (WaitForChild per segment) |
| `use "lowercase"` | `require(ReplicatedStorage.packages.lowercase)` |
| `use "Capitalized"` | `game:GetService(...)` |
| `use instance` | `require(instance)` |
| `new "Part"` | `Instance.new("Part")` |
| `asset "ui/icon.png"` | `"rbxassetid://<id>"` from `ReplicatedStorage.assets`; errors if not uploaded yet |

Package names must be lowercase, otherwise `use` treats them as services. LSP globals (`mod`, `use`, `new`, `module`, `asset`) are declared in `.vscode/globals.d.luau`; keep that file.

## Assets

Put files under `assets/` and reference them with `asset "<path under assets/, forward slashes, with extension>"`. Supported: `.png .jpg .jpeg .bmp .tga` (Image), `.mp3 .ogg .wav .flac` (Audio), `.fbx .gltf .glb .rbxm .rbxmx` (Model), `.mp4 .mov` (Video); others are skipped, hidden files ignored.

`chainlink assets` uploads only new or changed files and records `{ id, hash }` per path in `assets.lock.json`; a changed file gets a new ID. Commit the lock file. Never hard-code IDs that `asset` can supply. If an asset may not be uploaded yet, guard with `ReplicatedStorage:FindFirstChild("assets")` before calling `asset`.

## Feature workflow

1. Read `chain.toml` and neighbouring files; match their style (`local` vs bare globals, folder names).
2. `chainlink add ...`, then `chainlink install`.
3. Server logic in `server/*Service.luau`, client logic in `client/*Controller.luau`, shared code/data in `shared/`.
4. Clone prefabs from `ServerStorage` in Services; author `.rbxmx` in Studio, not by hand.
5. New images/sounds go in `assets/` and are referenced with `asset`; ask before running `chainlink assets`.
6. Lint with the proxied tools, then `chainlink serve` and sync in Studio.
