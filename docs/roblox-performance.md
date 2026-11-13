# Roblox Performance skill

Performance guidance for ChainLink projects: streaming, part and instance budgets, MicroProfiler habits, memory leaks (especially connections that are never disconnected) and how often to send network updates. It pairs with the [Blink](blink.md) skill for the networking side and the [ChainLink](chainlink.md) skill for Service/Controller lifetimes.

The skill's stance: diagnose with the MicroProfiler and Developer Console before changing anything, then fix the one dominant cost.

## Streaming

- Treat `StreamingEnabled` as always on. Client code must tolerate missing geometry: `CollectionService` signals, `WaitForChild` with a timeout, nil checks.
- `StreamingMinRadius` is what is always loaded, `StreamingTargetRadius` is what the engine keeps around; lower both for mobile.
- `ModelStreamingMode`: `Atomic` for models scripts index by path, `Persistent` sparingly, `PersistentPerPlayer` plus `RequestStreamAroundAsync` before teleports.
- Instances sent through remotes can arrive as `nil` on the client if not streamed in; send ids or positions instead.

## Part counts

| Target | Comfortable | Investigate above |
|---|---|---|
| Mobile | 5k-10k parts | 20k |
| Desktop | 20k-40k parts | 60k |
| Instances total | < 100k | 250k |

Anchor static parts; set `CanCollide`, `CanQuery` and `CanTouch` to false on decoration; prefer MeshParts over unions and part stacks; use `Box`/`Hull` collision fidelity; reuse mesh and texture ids; cap particle rates and shadowed lights; avoid partial transparency at scale. Fix order: delete → merge → stream → LOD.

## MicroProfiler habits

- `Ctrl+F6` to open, `Ctrl+P` to pause. Read which lane dominates the main thread: render, physics or scripts.
- Label hot paths with `debug.profilebegin("Service.method")` / `debug.profileend()`, matched on every return path.
- Profile on the lowest-end device you support; capture from a real client.
- Audit every `RenderStepped`/`Heartbeat`/`BindToRenderStep` callback; move whole-world iteration to a throttled loop or an event.

## Memory leaks

The most common leak is a connection to a long-lived signal (`Heartbeat`, `PlayerAdded`, `InputBegan`, a Service signal) created per player, per round or per UI open and never disconnected. `Instance:Destroy()` only disconnects that instance's own signals.

The skill prescribes a Trove/Janitor/Maid-style cleaner owned by the shorter-lived object, with teardown in `PlayerRemoving` or the view's unmount. It also covers per-player tables that never clear, `BindToRenderStep` without unbind, ad-hoc tweens, nil-parented instances, and ever-growing caches.

Diagnose by joining and leaving repeatedly and watching `Instances` and `PlaceScriptMemory` in the Developer Console.

## Network update rates

Budget around 50 KB/s per player. Remotes queue rather than drop, so spam becomes latency.

| Data | Rate | Channel |
|---|---|---|
| Input / custom entity positions | 10-20 Hz, deltas | Blink `unreliable` |
| Visual effects | on event | `unreliable` |
| Inventory, currency, round state | on change | reliable |
| Leaderboards | 1-2 Hz or on change | reliable |

Never fire remotes per frame without a throttle; batch into arrays; send deltas with sized Blink numbers; don't re-send what the engine already replicates; scope broadcasts; rate-limit clients on the server.

## Mobile and quality tiers

Design for a low-end phone first: phones get killed for memory rather than slowing down, and they throttle after 10-15 minutes of heat.

- Detect touch-only devices with `UserInputService` and consoles with `GuiService:IsTenFootInterface()`, not by screen size.
- The engine's graphics level belongs to the player. Add your own Low/Medium/High tiers for what the engine doesn't scale: particles, decorative lights, post-processing, beams and trails, ambient NPCs and client update rates.
- Choose the tier from measured frame time plus device class, step down fast and up slowly, and let a setting override it.
- Keep hero textures at 1024 px or less and most props at 512 or 256; preload only the current area.
- Profile on a real low-end Android device after 10+ minutes; the Device Emulator checks layout, not performance.

## Review order

1. Any `:Connect(` inside a callback without a matching disconnect?
2. Any remote fired per frame or per input unthrottled?
3. Any loop over all players/parts in a per-frame callback?
4. Any client code assuming streamed geometry exists?
5. Is there a MicroProfiler capture, or is this a guess?
6. Do effects scale with a quality tier, and has it run on a real low-end phone?
