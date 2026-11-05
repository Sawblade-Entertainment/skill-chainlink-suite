---
name: chainlink
description: Build Roblox games with ChainLink (Sawblade Entertainment's tool/package manager, Studio sync server and Luau flavor). Use when editing a Roblox project with a chain.toml, writing Services/Controllers, using the `use`/`new` macros, or running the `chainlink` CLI.
---

# ChainLink

Tool/package manager, Studio sync server and Luau flavor (bootstrapper + `use`/`new` macros). Source: `Sawblade-Entertainment/ChainLink`. Early development: back up before risky changes. Use only the CLI flags and `chain.toml` keys listed here.

## CLI

| Command | Purpose |
|---|---|
| `chainlink init` | Scaffold `chain.toml`, `client/`, `server/`, `shared/`, `.vscode/` |
| `chainlink install [-y]` | Install everything in `chain.toml` |
| `chainlink add owner/repo@tag --tool` | Add a tool |
| `chainlink add scope/name@version --package` | Add a package |
| `chainlink remove <name>` | Remove a tool or package |
| `chainlink serve` | Live-sync server for the Studio plugin (port 8013) |
| `chainlink build <out>` | Build a place (`.rbxl`/`.rbxlx`) or `src/` as a model (`.rbxm`/`.rbxmx`) |
| `chainlink sourcemap [-o path]` | Sourcemap for luau-lsp |
| `chainlink login` / `publish` | Registry auth / publish (Wally-compatible) |
| `chainlink self-install` | Install to `~/.chainlink/bin`, add to PATH, install Studio plugin |

- Prefer `add`/`remove` over hand-editing; pin exact versions.
- Tokens live in `~/.chainlink/auth.toml`; never print or commit them.
- **Tool proxying:** symlink the binary under a tool's name (`ln -s $(which chainlink) /usr/local/bin/selene`); running it resolves the version from `[Tools]` and auto-installs it.

## chain.toml

```toml
DisableBootstrap = false   # optional; true disables mod wrapping + bootstrapper

[Package]                  # only for publishing
Name = "..."
Version = "0.1.0"

[Tools]
selene = "Kampfkarren/selene@0.32.0"

[Packages]
razorinput = "vibeonline/razorinput@0.1.0"   # -> ReplicatedStorage.packages.razorinput
```

## Sync layout

Defaults; override with `roots` in `chainlink.json`. Keep whatever folder names the project already uses.

| Dir | Roblox target |
|---|---|
| `client/` | `StarterPlayer.StarterPlayerScripts` (client bootstrapper) |
| `server/` | `ServerScriptService` (server bootstrapper) |
| `shared/` | `ReplicatedStorage.shared` |
| `prefab/` | `ServerStorage` |

File types: `.luau` → ModuleScript, `*.server.luau` → Script, `*.client.luau` → LocalScript, `.json` → ModuleScript, `.txt` → StringValue, `.rbxm`/`.rbxmx` → Model. `init.luau` becomes its folder's instance (not allowed at the root of `client/` or `server/`).

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

Injected only when assigned from (`x = use ...`), so always assign the result and put `use` lines at the top.

| Call | Resolves to |
|---|---|
| `use "./x"`, `use "../x"`, `use "@x"` | `require(...)` (relative to the script / Roblox alias) |
| `use "/a/b"` | `require(ReplicatedStorage.a.b)` (WaitForChild per segment) |
| `use "lowercase"` | `require(ReplicatedStorage.packages.lowercase)` |
| `use "Capitalized"` | `game:GetService(...)` |
| `use instance` | `require(instance)` |
| `new "Part"` | `Instance.new("Part")` |

Package names must be lowercase, otherwise `use` treats them as services. LSP globals (`mod`, `use`, `new`, `module`) are declared in `.vscode/globals.d.luau`; keep that file.

## Feature workflow

1. Read `chain.toml` and neighbouring files; match their style (`local` vs bare globals, folder names).
2. `chainlink add ...`, then `chainlink install`.
3. Server logic in `server/*Service.luau`, client logic in `client/*Controller.luau`, shared code/data in `shared/`.
4. Clone prefabs from `ServerStorage` in Services; author `.rbxmx` in Studio, not by hand.
5. Lint with the proxied tools, then `chainlink serve` and sync in Studio.