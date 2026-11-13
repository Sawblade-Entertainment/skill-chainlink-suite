---
name: roblox-performance
description: Roblox performance guidance for ChainLink projects. Use when the user asks about lag, frame rate, memory growth, StreamingEnabled, part/instance budgets, profiling with the MicroProfiler, leaking connections or tables, or how often to fire remotes / replicate state. Covers streaming setup, part counts, MicroProfiler habits, memory-leak patterns (connections never cleaned up), network update rates, and mobile quality tiers (low-end phones, thermal throttling, scaling effects down).
---

# Roblox Performance

You are a pragmatic Roblox performance advisor. Most "lag" reports are one of
five things: a streaming misconfiguration, too many instances, an unmeasured
hot path, a leak that grows every join, or remotes fired too often. Diagnose
first, then fix the one thing that matters. Never recommend micro-optimising
Luau until the MicroProfiler shows that script time is actually the problem.

## 1. Streaming (`Workspace.StreamingEnabled`)

Streaming is on by default for new places. Treat it as always on and write
code that tolerates parts not existing on the client yet.

- Set `StreamingMinRadius` (what is always loaded, ~64-128) and
  `StreamingTargetRadius` (what the engine tries to keep, ~512-1024).
  Min must be comfortably less than Target. Lower both on mobile-heavy games.
- Leave `StreamOutBehavior = Default` unless you have a reason; `Opportunistic`
  streams out more aggressively on low-memory devices.
- Use `ModelStreamingMode` per model:
  - `Atomic`: the whole model arrives at once. Use for things scripts index
    by path (vehicles, NPC rigs, interactive props).
  - `Persistent`: never streamed out. Use sparingly (spawn area, global
    lobby geometry). Each persistent model eats the always-loaded budget.
  - `PersistentPerPlayer` + `Player:AddReplicationFocus` / `RequestStreamAroundAsync`
    for teleport destinations before moving a character.
- Client code must not assume `workspace.Map.Zone3.Door` exists. Use
  `CollectionService` tags with `GetInstanceAddedSignal` /
  `GetInstanceRemovedSignal`, or `WaitForChild` with a timeout and a nil check.
  Never `WaitForChild` without a timeout on streamed geometry.
- Before teleporting a player, call `player:RequestStreamAroundAsync(position)`
  so they don't fall through unloaded floor.
- Anything the server references by instance over a remote (Blink `Instance`
  fields) may arrive as `nil` on the client if it isn't streamed in. Send an
  id or position instead, or mark the model `Atomic`/`Persistent`.
- Symptoms of a streaming problem: "it works in Studio but not live",
  nil-index errors in client Controllers, players falling through the map,
  LocalScripts that find half a model.

## 2. Part and instance counts

The cost of a part is not just the triangle. Every instance costs memory,
replication, physics bookkeeping and raycast/query work.

Rough budgets (always-loaded, i.e. inside `StreamingMinRadius` or Persistent):

| Target | Comfortable | Investigate above |
|---|---|---|
| Mobile | 5k-10k parts | 20k |
| Desktop | 20k-40k parts | 60k |
| Instances total (incl. non-parts) | < 100k | 250k |

Check live numbers with `Stats` in the Developer Console (F9 → Memory →
`Instances`, `PhysicsParts`, `GraphicsParts`) and the `Rendering` tab's
draw-call count.

Rules of thumb:

- **Anchor everything that doesn't move.** Unanchored parts are simulated
  every physics step even when at rest-ish.
- **Turn off what you don't use** on decorative parts: `CanCollide = false`,
  `CanQuery = false`, `CanTouch = false`. `CanQuery=false` removes the part
  from raycasts and spatial queries entirely.
- **Prefer MeshParts over unions and over stacks of parts.** Unions keep their
  original geometry and are expensive to replicate; stacks of 30 parts for a
  fence are 30 instances when one MeshPart would do.
- **Set `RenderFidelity = Automatic`** and `CollisionFidelity = Box` or `Hull`
  on meshes unless precise collision is required. `PreciseConvexDecomposition`
  is the expensive one.
- **Reuse assets.** Identical MeshParts/Textures are instanced by the renderer;
  a hundred different mesh ids are a hundred draw calls.
- **Decals, SurfaceGuis, Beams, ParticleEmitters, Lights** are not free:
  lights (especially shadows) and particle rate are common mobile killers.
  Cap `ParticleEmitter.Rate`, keep `Light.Shadows` off except for the sun.
- **Avoid `Transparency` between 0 and 1** on large numbers of parts; partial
  transparency breaks batching and causes overdraw.
- When a build is over budget, the fix order is: delete, then merge into
  meshes, then stream, then LOD. Not "optimise scripts".

## 3. MicroProfiler habits

Measure before guessing. The MicroProfiler is the only tool that tells you
whether a frame is render-, physics-, or script-bound.

- Open with `Ctrl+F6` (Studio or client), pause with `Ctrl+P`, and look at
  the **main** thread's frame. Everything above ~16.6 ms (60 fps) is a
  problem; above 33 ms on mobile is a severe one.
- Read the lanes: `Render` / `Prepare` / `Perform` = rendering,
  `physicsSteppedTotal` = physics, `Heartbeat` / `RunService.Stepped` /
  `BindToRenderStep` = your scripts. Fix whichever lane dominates.
- Wrap suspect code so it shows up by name:

  ```lua
  debug.profilebegin("InventoryController.rebuild")
  -- work
  debug.profileend()
  ```

  Every `profilebegin` must be matched by `profileend` on every return path.
  Label with `Service.method` so the lane is searchable.
- Profile on the **lowest-end device you support**, not your dev machine.
  Dump a capture from a real client with the MicroProfiler web server
  (Settings → MicroProfiler → enable, then open the shown address on the
  same network) or `Ctrl+P` then save.
- Per-frame scripts are the usual culprit. Audit every `RenderStepped`,
  `Heartbeat` and `BindToRenderStep` callback: it should do constant,
  cheap work. Move anything that iterates all players/parts/NPCs to a
  throttled loop (every 0.1-0.5 s) or an event.
- Instance property reads/writes and `FindFirstChild` in hot loops are
  expensive relative to table access. Cache instances once at setup.
- Don't trust Studio's `Script Performance` tab for frame timing; use it
  only to spot which script is burning CPU overall.

## 4. Memory leaks

Memory that climbs every time a player joins, a round starts or a UI opens is
a leak. Check Developer Console → Memory → `PlaceScriptMemory` and
`Instances` after 20 minutes of play; they should plateau.

### Connections that never get cleaned up (the #1 cause)

An `RBXScriptConnection` keeps alive every upvalue its callback captures. A
connection to a long-lived signal (`RunService.Heartbeat`, `Players.PlayerAdded`,
`UserInputService.InputBegan`, `CollectionService` signals, a Service's own
signal) made per player / per round / per UI open is a leak unless it is
explicitly `:Disconnect()`ed.

- `Instance:Destroy()` disconnects connections **on that instance's own
  signals** (`part.Touched`) and clears its parent. It does not disconnect
  connections your code made to other objects (`Heartbeat`) inside a callback.
- Connections to a `Player`'s signals and a `Character` die with the instance,
  but tables you keyed by player (`state[player] = {...}`) do not. Clear them
  in `PlayerRemoving`.
- A `while true do task.wait() end` loop started per player is a leak: break
  out of it on `PlayerRemoving` or check `player.Parent`.
- `BindToRenderStep` must be paired with `UnbindFromRenderStep`.
- `Tween`s and `Sound`s created ad hoc should be destroyed when finished
  (`tween.Completed:Once(function() tween:Destroy() end)`).

Always attach cleanup to a lifetime. Use a Trove/Janitor/Maid-style cleaner
owned by the thing with the shorter lifetime:

```lua
local Trove = require(ReplicatedStorage.Packages.Trove)

local function onPlayerAdded(player: Player)
    local trove = Trove.new()
    perPlayer[player] = trove

    trove:Connect(RunService.Heartbeat, function(dt)
        -- per-player tick
    end)
    trove:Connect(player.CharacterAdded, function(char)
        local charTrove = trove:Extend()
        charTrove:Connect(char.Humanoid.Died, function()
            charTrove:Destroy()
        end)
    end)
end

Players.PlayerRemoving:Connect(function(player)
    local trove = perPlayer[player]
    if trove then
        trove:Destroy()
        perPlayer[player] = nil
    end
end)
```

In ChainLink projects, a Service or Controller that creates per-player or
per-view resources must expose the matching teardown and call it from
`PlayerRemoving` / the view's unmount. Vide views: create connections inside
`vide.effect`/`vide.cleanup` scope so they are released when the view is
destroyed; never connect from a bare function in a component body.

### Other common leaks

- Instances parented to `nil` but still referenced (`part.Parent = nil` is
  not `part:Destroy()`).
- Caches that only grow: dictionaries keyed by userId, asset id, or session
  that never evict. Use weak tables (`setmetatable({}, { __mode = "k" })`)
  for instance-keyed caches, or evict on `PlayerRemoving`.
- Client-side: cloned UI templates that are hidden instead of destroyed;
  `ContentProvider:PreloadAsync` on huge lists (that's memory, not a leak,
  but it looks like one).
- `Debris:AddItem` is fine for parts but doesn't disconnect anything.

Diagnose by joining/leaving with alt accounts or Studio's multi-client test
server and watching `Instances` and `PlaceScriptMemory`. If either climbs by a
fixed amount per join and never recovers, grep for `:Connect(` inside
`PlayerAdded`/`CharacterAdded` callbacks.

## 5. Network update rates

The server has a replication budget of roughly **50 KB/s per player** before
the client falls behind and `Ping`/incoming-data rises. Remote events are
queued, not dropped, so spamming them causes latency that grows over time.

| Data | Rate | Channel |
|---|---|---|
| Player input (aim, movement intent) | 10-20 Hz, client → server | Blink `unreliable` |
| Server-authoritative positions for custom entities | 10-20 Hz, delta-only | Blink `unreliable` |
| Visual-only effects (hit sparks, footsteps) | on event, fire-and-forget | `unreliable` |
| State that must arrive (inventory, currency, round state) | on change, never per-frame | reliable |
| Leaderboard / stats | 1-2 Hz or on change | reliable |

Rules:

- **Never fire a remote from `RenderStepped`/`Heartbeat` without a throttle.**
  Accumulate and send on a fixed tick (`if now - last >= 1/15`).
- **Batch.** One event carrying an array of 30 updates is far cheaper than 30
  events. Blink structs/arrays make this free.
- **Send deltas, not snapshots.** Only include fields that changed; quantise
  with Blink's sized numbers (`u8`, `i16`, `f32`) instead of `f64`.
- **Let the engine replicate what it already replicates.** Character
  position, physics-owned parts and Humanoid state are already synced; don't
  re-send them.
- **Server → all clients fan-out multiplies cost by player count.** 20 Hz ×
  50 players × 200 bytes = 200 KB/s outbound from one event. Scope
  broadcasts to players who need them (nearby, same team, same zone).
- **Use `unreliable` for anything where a newer packet makes the old one
  worthless**; use reliable only for state transitions.
- Rate-limit on the server: drop or kick clients that exceed ~60 remote calls
  per second on any single event. Never trust a client-supplied rate.
- Watch Developer Console → Network → `Data Received`/`Data Sent` per client
  and the `Remotes` section of Memory. Above ~30 KB/s sustained per client is
  a warning sign.

## 6. Mobile and quality tiers

Design for a low-end phone first; desktop gets the headroom for free. Phones
run out of memory and get killed rather than slowing down, and they
throttle after 10-15 minutes of heat, so a game that is smooth for the first
minute can still fail on mobile.

- **Detect the device class on the client**, not by screen size alone:
  touch-only = `UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled`,
  console = `GuiService:IsTenFootInterface()`. Tablets have desktop-like
  resolutions with phone-like hardware.
- **The engine's graphics level belongs to the player.** It auto-adjusts
  rendering (draw distance, shadows, some effects), and scripts cannot
  reliably read the effective level. Don't fight it; add your own tiers for
  the things the engine doesn't scale: your particles, lights, post-processing,
  ambient NPCs, client effects and custom update rates.
- **Pick the tier from measured frame time plus device class**, with
  hysteresis so it doesn't flap, and let a settings toggle override it
  (persist the choice).

```lua
-- client/QualityController.luau
UserInputService = use "UserInputService"
GuiService = use "GuiService"

export type Tier = "Low" | "Medium" | "High"
local tiers: { Tier } = { "Low", "Medium", "High" }

local touchOnly = UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled
mod.tier = (if touchOnly or GuiService:IsTenFootInterface() then "Medium" else "High") :: Tier
mod.override = nil :: Tier? -- set from the settings menu
mod.changed = Instance.new("BindableEvent")

local sum, frames, lowSince = 0, 0, 0.0

function mod:beat(dt: number)
    sum += dt
    frames += 1
    if sum < 5 or mod.override then return end
    local avg = sum / frames
    sum, frames = 0, 0
    local index = table.find(tiers, mod.tier) :: number
    if avg > 1 / 40 and index > 1 then
        mod.tier = tiers[index - 1] -- step down fast
        mod.changed:Fire(mod.tier)
    elseif avg < 1 / 58 and index < #tiers then
        lowSince += 5
        if lowSince >= 120 then -- step up only after 2 minutes of headroom
            lowSince = 0
            mod.tier = tiers[index + 1]
            mod.changed:Fire(mod.tier)
        end
    else
        lowSince = 0
    end
end
```

What each tier changes (effects code reads `QualityController.tier`; never
branch on device type deep in feature code):

| Lever | Low | Medium | High |
|---|---|---|---|
| `ParticleEmitter.Rate` / burst counts | x0.25-0.5 | x0.5-0.75 | x1 |
| Decorative `PointLight`/`SpotLight` | off | no shadows | no shadows except key lights |
| Post-processing (`Bloom`, `DepthOfField`, `SunRays`) | off | Bloom only | on |
| `Beam`/`Trail` lifetime and segments | halved | reduced | full |
| Ambient NPCs, client-only props, decals | culled or nearest few | reduced | full |
| Client effect pools / custom update rates | small / 10 Hz | medium / 15 Hz | full / 20 Hz |

Other mobile rules:

- Keep the always-loaded part budget at the mobile row of section 2, and
  keep `StreamingMinRadius` low; streaming is the biggest memory lever.
- Textures: 1024 px is the ceiling for hero assets; most props are fine at
  512 or 256. Every unique texture and preloaded sound is resident memory.
- Preload only the current area's assets; don't `PreloadAsync` the whole
  catalogue on join.
- Watch client memory in Developer Console → Memory on a real phone: a
  steady climb on mobile is a crash later, not just a leak.
- Profile on a real low-end Android device after 10+ minutes of play.
  Studio's Device Emulator checks resolution and touch layout, not
  performance.
- UI-side mobile rules (safe areas, touch controls, target sizes) live in
  the `roblox-ui-design` skill.

## How to respond

- Ask for (or infer) the symptom first: frame time, memory growth, ping,
  load time, or "only on mobile". Each maps to a different section above.
- Lead with the single highest-impact change, then a measurement to confirm
  it worked ("add `profilebegin` around the loop, re-capture, expect the
  `Heartbeat` lane under 2 ms").
- When writing code, use modern Luau with type annotations, always pair
  connections with a cleanup owner, always throttle per-frame remotes, and
  prefer Blink `unreliable` events for high-frequency data.
- When reviewing code for performance, check in order:
  1. Any `:Connect(` inside a callback without a matching disconnect?
  2. Any remote fired per frame or per input event unthrottled?
  3. Any loop over all players/parts in a per-frame callback?
  4. Any client code that assumes streamed geometry exists?
  5. Is there a MicroProfiler capture, or is this a guess?
  6. Do effects scale down with a quality tier, and has it been run on a
     real low-end phone?
