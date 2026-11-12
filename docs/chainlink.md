# ChainLink skill

Covers [ChainLink](https://github.com/Sawblade-Entertainment/tool-chainlink): tool/package manager, Studio sync server, Open Cloud uploader, and Luau flavor (bootstrapper plus `use`/`new`/`asset` macros). ChainLink is in early development, so the skill restricts Claude to the CLI flags and `chain.toml` keys it documents.

## CLI

| Command | Purpose |
|---|---|
| `chainlink init` | `git init` if needed; scaffold `chain.toml`, `client/`, `server/`, `shared/`, `prefab/`, `assets/`, `.vscode/` |
| `chainlink install [-y]` | Install everything in `chain.toml`; asks before new downloads, `-y` skips the prompt |
| `chainlink add owner/repo@tag --tool` | Add a tool |
| `chainlink add scope/name@version --package` | Add a package |
| `chainlink remove <name>` | Remove a tool or package |
| `chainlink serve` | Live-sync server for the Studio plugin (port 8013) |
| `chainlink build <out>` | Build a place (`.rbxl`/`.rbxlx`) or `src/` as a model (`.rbxm`/`.rbxmx`) |
| `chainlink sourcemap [-o path]` | Sourcemap for luau-lsp |
| `chainlink login [--api URL --token T]` | Registry auth (GitHub device flow, or store a token) |
| `chainlink publish [--token T]` | Publish `src/` and `packages/` as a package (Wally-compatible, under 2 MB) |
| `chainlink login-cloud [--api-key K]` | Save a Roblox Open Cloud API key and print the permissions it needs |
| `chainlink assets [--dry-run] [--api-key K]` | Upload new or changed files in `assets/` to Roblox |
| `chainlink publish-place [--place ID] [--draft] [--api-key K] [file]` | Publish a `.rbxl`/`.rbxlx`, or a build of this project, to `[Roblox] PlaceId` |
| `chainlink self-install` | Install to `~/.chainlink/bin`, add to PATH, install the Studio plugin |

Notes:

- Prefer `add`/`remove` over hand-editing `chain.toml`, and pin exact versions.
- Flags go before positional arguments (`publish-place --draft game.rbxl`).
- Registry tokens and the Open Cloud key live in `~/.chainlink/auth.toml`. Never print or commit them. The Open Cloud key is taken from `--api-key`, then `ROBLOX_API_KEY`, then `auth.toml`.
- `assets` and `publish-place` change live Roblox content, so the skill has Claude dry-run and confirm before running them.
- **Tool proxying:** symlink the binary under a tool's name (`ln -s $(which chainlink) /usr/local/bin/selene`). Running it resolves the version from `[Tools]` and installs it if missing.

## chain.toml

```toml
DisableBootstrap = false   # optional; true disables mod wrapping + bootstrapper

[Package]                  # publishing metadata; Name also maps src/
Name = "..."
Version = "0.1.0"          # optional: License, Description, Website

[Tools]
selene = "Kampfkarren/selene@0.32.0"

[Packages]
razorinput = "vibeonline/razorinput@0.1.0"   # -> ReplicatedStorage.packages.razorinput

[Roblox]                   # only for assets / publish-place
PlaceId = 1234567890
UserId = 12345             # or GroupId = ... (GroupId wins)
```

## Sync layout

Defaults; override with `roots` (and `port`) in `chainlink.json`.

| Directory / file | Roblox target |
|---|---|
| `client/` | `StarterPlayer.StarterPlayerScripts` |
| `server/` | `ServerScriptService` |
| `shared/` | `ReplicatedStorage.shared` |
| `prefab/` | `ServerStorage` |
| `src/` | `ReplicatedStorage.packages.<Package.Name>` when `src/init.luau` exists |
| `assets.lock.json` | `ReplicatedStorage.assets`, read by the `asset` macro |

| File | Becomes |
|---|---|
| `.luau` / `.lua` | ModuleScript |
| `*.server.luau` | Script |
| `*.client.luau` | LocalScript |
| `.json` | ModuleScript |
| `.txt` | StringValue |
| `.rbxm` / `.rbxmx` | Model |

`init.luau` becomes its folder's instance (not allowed at the root of `client/` or `server/`). Every script gets `--!strict`, `--!native` and `--!optimize 2` prepended unless it already starts with `--!strict`. A `chainlink.json` root with `"package": true` maps a directory the same way `src/` is mapped.

## Services and Controllers

Files named `*Service.luau` (server) and `*Controller.luau` (client) are wrapped as `local mod = {} ... return mod`. Never write those lines; attach to `mod`.

| Method | Side | When |
|---|---|---|
| `mod:init()` | both | Synchronous, in priority order, before any `start`. On error the module is dropped from later hooks |
| `mod:start()` | both | After all `init`; each in its own thread |
| `mod:step(time, dt)` | both | `RunService.Stepped` |
| `mod:beat(dt)` | both | `RunService.Heartbeat` |
| `mod:draw(dt)` | client | `RunService.RenderStepped` |
| `mod:input(input, gameProcessed, phase)` | client | Input began/ended/changed; `phase` is `"began"`, `"ended"` or `"changed"` |
| `mod:playerAdded(player)` | server | Join, including players already present; own thread, may yield |
| `mod:playerRemoving(player)` | server | Leave; awaited at shutdown |
| `mod:characterAdded(player, char)` / `mod:characterRemoving(player, char)` | server | Character spawn/remove |
| `mod:close()` | server | `BindToClose`; all run in parallel, 25 s total |

`mod.priority = n`: lower initializes first (default 0), ties broken by name. Keep `init` fast; put cross-module work in `start`.

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

Injected only when assigned from (`x = use ...`). Always assign the result and put `use` lines at the top.

| Call | Resolves to |
|---|---|
| `use "./x"`, `use "../x"`, `use "@x"` | `require(...)` relative to the script / Roblox alias |
| `use "/a/b"` | `require(ReplicatedStorage.a.b)` (`WaitForChild` per segment) |
| `use "lowercase"` | `require(ReplicatedStorage.packages.lowercase)` |
| `use "Capitalized"` | `game:GetService(...)` |
| `use instance` | `require(instance)` |
| `new "Part"` | `Instance.new("Part")` |
| `asset "ui/icon.png"` | `"rbxassetid://<id>"` for a file uploaded from `assets/`; errors if not uploaded |

Package names must be lowercase, otherwise `use` treats them as services. Keep `.vscode/globals.d.luau`; it declares the `mod`, `use`, `new`, `module` and `asset` globals for the LSP.

## Assets

Images (`.png`, `.jpg`, `.bmp`, `.tga`), audio (`.mp3`, `.ogg`, `.wav`, `.flac`), models (`.fbx`, `.gltf`, `.glb`, `.rbxm`, `.rbxmx`) and videos (`.mp4`, `.mov`) in `assets/` are uploaded by `chainlink assets`. Only new or changed files are uploaded, and IDs are kept in `assets.lock.json`, which should be committed. Code references them with `asset "path/under/assets.png"` instead of hard-coded IDs.

## Feature workflow

1. Read `chain.toml` and neighbouring files; match their style.
2. `chainlink add ...`, then `chainlink install`.
3. Server logic in `server/*Service.luau`, client logic in `client/*Controller.luau`, shared code in `shared/`.
4. Clone prefabs from `ServerStorage` in Services; author `.rbxmx` in Studio, not by hand.
5. New images and sounds go in `assets/` and are referenced with `asset`.
6. Lint with the proxied tools, then `chainlink serve` and sync in Studio.
