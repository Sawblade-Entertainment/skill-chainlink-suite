# Roblox Testing skill

Testing guidance for ChainLink projects: unit tests, local multi-client servers with simulated lag, PvP bots, failure cases, leak soak tests and play tests driven through the Roblox Studio MCP. It pairs with the [Roblox Performance](roblox-performance.md) and [Roblox Monetization](roblox-monetization.md) skills, and with the [Roblox Combat](roblox-combat.md) and [Roblox Security](roblox-security.md) skills for what the bots should exercise.

The skill's stance: solo Studio Play hides the bugs that matter (one client, no latency, no cheaters), so test each piece at the cheapest level that can catch its bug.

## What to test where

| Kind of code | Where |
|---|---|
| Pure logic (formulas, rules, migrations) | Unit tests: Lune or an in-Studio runner |
| Services, Blink events, replication | Local server, 2-4 clients, added lag |
| PvP, hit registration, exploits | Local server + bots + a cheater client |
| DataStores, purchases, real ping | Team Test or a draft-published private server |

## ChainLink flavor

Only files under the synced roots get ChainLink's `use`/`new`/`asset` macros, Service/Controller wrapping and prepended compiler flags. Lune tests and Luau run through the Studio MCP or command bar see plain Luau, so they use `require` and `Instance.new` against real instance paths.

- Lune-tested modules are leaf modules with no macros, no `mod` and no Roblox APIs; Lune tests live outside every synced root.
- Play tests call the live, already-initialized Services; never re-run `init`/`start`.
- Nothing test-only goes at the top level of `server/` or `client/` (the bootstrapper loads it), and mocks named `*Service.luau` get wrapped.
- Bot and cheater code is gated in every hook, or kept out of shipped roots.
- `asset` errors in places without uploaded assets: commit `assets.lock.json` or guard.

## Unit tests

- Match the runner the project already uses; otherwise add one with `chainlink add ... --package` (Jest-Lua, or TestEZ) and pin it.
- Use Lune for modules that never touch Roblox APIs, so they run in a terminal and CI.
- Keep logic in plain modules that take values and return values.

## Multi-client and latency

- Studio → Test → Clients and Servers → Local Server with N players. Catches wrong-player remotes, per-player state bugs and ownership issues; does not simulate real ping, multiple servers or real purchases.
- Add incoming replication lag in Studio's Network settings and test at 100-250 ms, once at ~500 ms.

## Bots for PvP

- Bots call the same public Service API as the Blink handler; combat state is keyed by character, not `Player`.
- Scenarios: dummy, strafer, peeker, spammer (rate limits) and a cheater client that sends invalid, out-of-range and over-rate input.
- Drive bots from `Random.new(seed)` and log the seed so failures replay.
- Gate bots and debug Controllers to Studio only.

## Failure cases and soak

- Leave and rejoin mid-action, die mid-ability, DataStore errors (against test data only), `ProcessReceipt` fired twice.
- Soak 15-30 minutes with bots and join/leave cycles; `Instances` and `PlaceScriptMemory` should plateau.

## Studio MCP

With a Roblox Studio MCP connected, Claude can start play, run Luau to spawn bots and assert on state, read the console, then stop play and clean up.

## Before publishing

Unit tests and lint pass, multi-client with lag works, bots and cheater input cause no errors or accepted bad input, edge cases checked, memory plateaus, debug tools gated off, then `chainlink publish-place --draft` and a private-server check before going live.
