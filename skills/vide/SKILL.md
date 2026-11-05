---
name: vide
description: Build Roblox UI with Vide (centau/vide), a reactive Luau UI library. Use when writing or editing Vide views, components, sources/derives/effects, or mounting UI.
---

# Vide UI

Reactive Luau UI library (`centau/vide`, package pin e.g. `vide = "centau/vide@0.4.1"`). Docs: https://centau.github.io/vide. Match the pinned version; verify any API not listed below against the docs/source before using it.

## Core API
| Call | Purpose |
|---|---|
| `create("Class")({ props, children })` | Create an instance; function-valued props are reactive |
| `source(v)` | State: read `s()`, write `s(v)` |
| `derive(fn)` | Cached computed source |
| `effect(fn)` | Re-runs when sources it reads change |
| `cleanup(fn)` | Runs on scope teardown |
| `mount(fn, parent)` | Mount a root; returns an unmount function |

## View module pattern
Views are plain modules (e.g. `client/views/`) owned and driven by a client controller — not lifecycle modules themselves.

```lua
local Hud = {}

vide = use "vide" -- or require(...) outside ChainLink
local create, source, derive, mount = vide.create, vide.source, vide.derive, vide.mount

local remaining = source(0)
local unmount: (() -> ())? = nil

local function view()
	return create("TextLabel")({
		Size = UDim2.fromScale(1, 0.1),
		BackgroundTransparency = 1,
		Text = derive(function()
			return `{remaining()}s`
		end),
	})
end

function Hud:show(parent: Instance)
	unmount = mount(view, parent)
end

function Hud:setRemaining(n: number)
	remaining(n)
end

function Hud:destroy()
	if unmount then
		unmount()
		unmount = nil
	end
end

return Hud
```

## Rules
- Keep state in module-scope sources updated from events (network handlers, input); views never poll.
- Pass functions (sources/derives) as props for reactivity; plain values are set once.
- Keep the unmount function and call it on teardown.