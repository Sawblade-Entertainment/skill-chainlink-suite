# Vide skill

Covers [Vide](https://centau.github.io/vide) (`centau/vide`), a reactive Luau UI library. The skill targets the version pinned in your project (e.g. `vide = "centau/vide@0.4.1"`) and tells Claude to verify any API it is unsure of against the docs or source.

## Core API

| Call | Purpose |
|---|---|
| `create("Class")({ props, children })` | Create an instance; function-valued props are reactive |
| `source(v)` | State: read with `s()`, write with `s(v)` |
| `derive(fn)` | Cached computed source |
| `effect(fn)` | Re-runs when the sources it reads change |
| `cleanup(fn)` | Runs on scope teardown |
| `mount(fn, parent)` | Mount a root; returns an unmount function |

## View module pattern

Views are plain modules (for example in `client/views/`) owned and driven by a client Controller. They are not lifecycle modules themselves.

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

!!! tip
    Pair this skill with [Roblox UI Design](roblox-ui-design.md) for layout, color, motion and accessibility guidance.

## Rules

- Keep state in module-scope sources updated from events (network handlers, input). Views never poll.
- Pass functions (sources or derives) as props for reactivity; plain values are set once.
- Keep the unmount function and call it on teardown.
