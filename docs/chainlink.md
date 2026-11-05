# ChainLink skill

Covers ChainLink: tool/package manager, Studio sync server, and Luau flavor (bootstrapper plus `use`/`new` macros). ChainLink is in early development, so the skill restricts Claude to the CLI flags and `chain.toml` keys it documents.

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
| `chainlink login` / `publish` | Registry auth and publishing (Wally-compatible) |
| `chainlink self-install` | Install to `~/.chainlink/bin`, add to PATH, install the Studio plugin |

Notes:

- Prefer `add`/`remove` over hand-editing `chain.toml`, and pin exact versions.
- Tokens live in `~/.chainlink/auth.toml`. Never print or commit them.
- **Tool proxying:** symlink the binary under a tool's name (`ln -s $(which chainlink) /usr/local/bin/selene`). Running it resolves the version from `[Tools]` and installs it if missing.

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

Defaults; override with `roots` in `chainlink.json`.

| Directory | Roblox target |
|---|---|
| `client/` | `StarterPlayer.StarterPlayerScripts` |
| `server/` | `ServerScriptService` |
| `shared/` | `ReplicatedStorage.shared` |
| `prefab/` | `ServerStorage` |

| File | Becomes |
|---|---|
| `.luau` | ModuleScript |
| `*.server.luau` | Script |
| `*.client.luau` | LocalScript |
| `.json` | ModuleScript |
| `.txt` | StringValue |
| `.rbxm` / `.rbxmx` | Model |

`init.luau` becomes its folder's instance (not allowed at the root of `client/` or `server/`).

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

Package names must be lowercase, otherwise `use` treats them as services. Keep `.vscode/globals.d.luau`; it declares the `mod`, `use`, `new` and `module` globals for the LSP.

## Feature workflow

1. Read `chain.toml` and neighbouring files; match their style.
2. `chainlink add ...`, then `chainlink install`.
3. Server logic in `server/*Service.luau`, client logic in `client/*Controller.luau`, shared code in `shared/`.
4. Clone prefabs from `ServerStorage` in Services; author `.rbxmx` in Studio, not by hand.
5. Lint with the proxied tools, then `chainlink serve` and sync in Studio.
