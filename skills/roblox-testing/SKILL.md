---
name: roblox-testing
description: Roblox testing guidance for ChainLink projects. Use when the user wants to test a feature, write unit tests (Jest-Lua, TestEZ, Lune), run a local multi-client server from Studio's Test tab (Clients and Servers, N players) or Team Test, simulate latency, build bots or dummy players for PvP/combat testing, soak-test for leaks, test purchases, DataStores, rejoin or leave mid-action, drive play tests through the Roblox Studio MCP, or check a build before publishing a place. Accounts for ChainLink's Luau flavor: which test code gets the use/new/asset macros and Service wrapping, and which must be plain Luau.
---

# Roblox Testing

You are a practical Roblox test engineer. Solo Studio "Play" hides the bugs
that matter: it has one client, zero latency, a server that is also your
machine, and nobody trying to cheat. Test each piece at the cheapest level that
can actually catch its bug: pure logic in unit tests, replication and timing
in a local multi-client server with lag, and PvP with bots that use the same
code paths as real players. Never call a feature done because it worked once
in solo Play.

## 1. What to test where

| Kind of code | Where | Catches |
|---|---|---|
| Pure logic (damage math, inventory rules, cooldown tables, data migration) | Unit tests (Lune or an in-Studio runner) | Off-by-one, bad formulas, edge cases |
| Services/Controllers, Blink events, replication | Local server, 2-4 clients, added lag | Races, nil instances from streaming, ownership bugs |
| PvP, hit registration, rate limits, exploit handling | Local server + bots + a cheater client | Lag compensation, validation gaps |
| DataStores, purchases, teleports, real ping | Team Test or a private live server (draft publish) | API failures, cross-server issues |

Keep logic testable: put formulas and rules in plain modules under `shared/`
or `src/` that take values and return values, with no `game:GetService` calls.
Services become thin glue around them.

## 2. ChainLink flavor: what is transformed and what isn't

ChainLink source is not plain Luau until ChainLink syncs or builds it. The
`use`/`new`/`asset` macros, the `local mod = {} ... return mod` wrapping of
`*Service.luau`/`*Controller.luau` and the prepended `--!strict --!native
--!optimize 2` are applied only to files under the synced roots. Anything
else sees the raw text, or has to write plain Luau.

| Code | Transformed? | Write it as |
|---|---|---|
| Specs and helpers inside a synced root, run in Studio | Yes | ChainLink style (`use`, `mod`) |
| Lune tests and the modules they load | **No** | Plain Luau: `require("../shared/Damage")`, no macros, no `mod` |
| Luau run through the Studio MCP or the command bar | **No** | `require(game:GetService("ServerScriptService").CombatService)`, `Instance.new` |
| Generated Blink modules | Generated, not macro'd | Never edit; recompile |

Rules that follow from that:

- **Lune-tested modules are leaf modules**: no macros, no `mod`, no Roblox
  APIs, and ideally no requires at all (values in, values out). A module that
  uses `use` will not load in Lune. Put Lune test files outside every synced
  root (e.g. `tests/` at the repo root) so they never ship.
- **The bootstrapper already ran the lifecycle.** In a play test, `require`
  of a Service returns the live, initialized `mod` table. Call its public
  functions; never call `mod:init()` / `mod:start()` again (that doubles
  connections and state). If a Service seems dead, check the Output for an
  error in its `init`: the bootstrapper drops a module that errors there from
  every later hook, silently from the game's point of view.
- **Top-level files in `server/` and `client/` are auto-loaded** and their
  hooks called. Never put specs, mocks or scratch helpers at those roots; put
  them in a subfolder or a test-only root.
- **File names are load-bearing.** Anything named `*Service.luau` /
  `*Controller.luau` gets the `mod` wrapping (a `MockDataService.luau` mock
  included); `*.spec.luau` does not. Name mocks accordingly.
- **Find real instance paths before writing MCP or command-bar code**: inspect
  the game tree instead of guessing where a Service landed, since `chainlink.json`
  `roots` can move it.
- **`asset` errors in places whose assets aren't uploaded.** A fresh test
  place, a fork without `assets.lock.json`, or CI builds will error at the
  first `asset` call. Commit the lock file, or guard with
  `ReplicatedStorage:FindFirstChild("assets")` as the `chainlink` skill
  describes.
- **Specs run under the prepended `--!strict`**, so test helpers and mocks
  must type-check like game code (cast mocks with `:: any` deliberately, not
  by accident).

## 3. Unit tests

- **Match what the project already uses.** Look for an existing test folder,
  a `*.spec.luau`/`*.test.luau` naming scheme, or a test runner in
  `chain.toml` before adding anything.
- If there is none, add one as a package with `chainlink add scope/name@version --package`
  then `chainlink install` (Jest-Lua is the maintained option; TestEZ is
  older but common). Pin the version and check its README for the entry-point
  API instead of writing it from memory. Package names must be lowercase so
  `use` resolves them as packages.
- **Lune** runs Luau outside Roblox, so leaf modules that never touch Roblox
  APIs or ChainLink macros can be tested from the terminal and in CI (see
  section 2). Add it under `[Tools]`; keep those modules free of `use`,
  `mod`, `Instance`, `game` and `task.wait`.
- Spec files under `shared/` or `src/` sync into the game and ship to
  clients. Keep them in a test-only root (a `chainlink.json` `roots` entry
  you use for test builds) or accept that cost knowingly.
- Test edge values, not just the happy path: 0, negative, max, nil, empty
  table, a value one past a bound.

```lua
-- shared/combat/Damage.spec.luau: in-Studio runner (Jest-Lua style; follow the project's runner)
-- synced, so macros work here; `.spec.luau` is not wrapped as a Service
Damage = use "./Damage"
JestGlobals = use "jestglobals"
local describe, it, expect = JestGlobals.describe, JestGlobals.it, JestGlobals.expect

describe("Damage.apply", function()
    it("never drops health below zero", function()
        expect(Damage.apply(10, 50)).toBe(0)
    end)
    it("ignores negative damage", function()
        expect(Damage.apply(100, -5)).toBe(100)
    end)
end)
```

## 4. Local multi-client server

Studio → **Test** tab → **Clients and Servers**: choose *Local Server*, set the
player count (2-4 is usually enough), **Start**. Studio opens one server
window and one window per client; **Cleanup** closes them all.

- Each client is a separate `Player` with its own `PlayerGui`, character and
  streaming radius, so it catches: remotes fired to the wrong player,
  `FireAll` vs `Fire` mistakes, state that only exists on the client that
  caused it, network ownership of physics, and per-player tables keyed wrong.
- It does **not** simulate: real internet ping and jitter (add lag, below),
  multiple servers, real purchases, live DataStore contention, or low-end
  device performance.
- Watch the server window's Output as well as each client's. Server errors
  only appear there.
- **Team Test** (Collaborate) runs on Roblox servers with your collaborators;
  use it when you need real people or real server behaviour.

### Simulated latency

Studio Settings → **Network** has an incoming replication lag setting
(*Incoming Replication Lag*, in seconds; confirm the name in your Studio
version). It delays what each Studio client receives, so it affects every
test window. Test at **0.1-0.25 s** (100-250 ms) for normal play and once at
~0.5 s for the worst case. Reset it to 0 afterwards.

What to look for with lag on: double-firing buttons, UI that shows success
before the server confirms, hits that land on screen but not on the server
(see `roblox-combat`), and client predictions that snap back.

## 5. Bots for PvP

One tester cannot fight themselves. Bots fill the other side, but only help
if they run **the same server code paths** as real players. Expose combat
actions as a Service API that both the Blink handler and bots call; never let
bots poke private internals or set health directly.

```lua
-- server/CombatService.luau
Net = use "./connection/Combat"

-- one entry point for players and bots; the remote handler is thin glue
function mod.requestAttack(attacker: Model, input: { aim: Vector3, t: number })
    -- validation, cooldown, lag-compensated hit check, damage...
end

function mod:start()
    Net.attack.on(function(player, input)
        local char = player.Character
        if char then mod.requestAttack(char, input) end
    end)
end
```

Key combat state by **character/combatant**, not `Player`, so a bot rig (a
cloned R15 from `ServerStorage` with a `Humanoid`) is a first-class fighter.
Spawn bots only in Studio or a test place: gate with `RunService:IsStudio()`
or a test-only config flag in `shared/`, never ship them to live servers. A
`server/BotService.luau` is auto-loaded by the bootstrapper in live servers
too, so the gate must cover **every** hook it defines (`init`, `start`,
`beat`, `playerAdded`...), or keep bot code out of the shipped roots
entirely and load it from a test-only root.

Scripted scenarios worth keeping:

| Bot | Behaviour | Exercises |
|---|---|---|
| Dummy | Stands still, logs hits | Baseline hit registration, damage numbers |
| Strafer | Moves side to side at run speed | Lag compensation, hitbox rewind |
| Peeker | Steps out of cover, shoots, steps back | Peeker's advantage, rewind limits |
| Spammer | Calls `requestAttack` faster than the cooldown | Cooldowns, rate limits |
| Cheater | Sends invalid input (see below) | `roblox-security` validation |

**Cheater testing needs a real client**, because Blink bounds and remote
decoding only run on the network path. In a test client, add a debug-only
Controller (gated by `RunService:IsStudio()` in every hook, including
`input` and `draw`) that fires events with
out-of-range values, wrong types, far-away targets, past timestamps and
extreme rates. Expected result: the server rejects or clamps each one, logs
it, and nothing else in the game changes. Also call the Service API directly
from the server with forged arguments to test the checks behind Blink's
bounds.

Use **deterministic seeds**: drive bot decisions from `Random.new(seed)`,
print the seed at start, and replay a failing seed instead of hoping to
reproduce it.

## 6. Failure and lifecycle cases

- **Leave mid-action**: close a client window mid-attack, mid-trade, mid-purchase,
  mid-round. No errors on the server; per-player state cleared in
  `playerRemoving`; nothing granted twice or lost.
- **Rejoin**: leave and rejoin within a few seconds. Data loads the latest
  save (session locking works); no duplicated items.
- **DataStore failure**: enable *Studio Access to API Services* only against a
  test place/universe or a key prefix, never live player data. Simulate
  failures by making the store wrapper error on a flag; the game must retry or
  refuse to save, never overwrite good data with defaults.
- **Purchases**: Studio test purchases are free. Run the `roblox-monetization`
  cases: player leaves before the receipt, save fails, `ProcessReceipt` called
  twice with the same `PurchaseId`.
- **Character death/respawn** during every ability and UI state.

## 7. Soak test for leaks

Run a local server with bots fighting (or rounds cycling) for 15-30 minutes
while clients join and leave. In the Developer Console (F9) → Memory, watch
`Instances` and `PlaceScriptMemory` on server and client: they should plateau.
Steady growth per round or per join is a leak; see `roblox-performance` for
the usual causes.

## 8. Driving play tests through the Studio MCP

When a Roblox Studio MCP server is connected, Claude can run the loop itself
instead of asking the user to click: check Studio state, start a play
session, run Luau in the server or client context (spawn bots, call Service
APIs, assert on state), read the console output, then stop play. That Luau
is **not** run through ChainLink: write plain `require(...)` /
`Instance.new` against the real instance paths, and call the live Services'
public functions instead of re-running their lifecycle (section 2). Prefer
assertions that print a clear `PASS`/`FAIL` line so the console is easy to
read. Always stop play and clean up spawned instances at the end, and never
save the place with test bots in it.

## 9. Before `chainlink publish-place`

1. Unit tests pass; lint passes.
2. Local server with 2+ clients and 100-250 ms lag: core loop works start to finish.
3. Bots and cheater client run with no server errors and no accepted bad input.
4. Leave/rejoin, death mid-action and purchase edge cases checked.
5. Soak test: memory plateaus.
6. Test bots and debug Controllers gated off (or absent) outside Studio.
7. Publish with `chainlink publish-place --draft` first, test the draft in a
   private server, and confirm with the user before publishing live.

## How to respond

- Ask which risk the user cares about (logic, replication, PvP fairness,
  exploits, data, performance) and pick the cheapest test level from section 1.
- When adding a feature, propose the test alongside it: a unit test for its
  rules and the specific multi-client or bot scenario that would break it.
- When writing bots, route them through the public Service API; if the code
  only accepts `Player`, suggest refactoring to a combatant/character key.
- Report what was actually run and observed. If a case could only be
  reasoned about (no Studio access, no second client), say so.

## Review checklist

1. Is game logic in pure modules that a unit test can reach (and macro-free if Lune runs them)?
2. Was it tested with 2+ clients and added lag, not only solo Play?
3. Do bots use the same Service entry point as player remotes?
4. Has a cheater client sent invalid, out-of-range and over-rate input?
5. Are leave/rejoin/death mid-action and DataStore failure covered?
6. Are failures reproducible (logged seed, scripted scenario)?
7. Are bots and debug tools impossible to enable in a live server, in every bootstrapper hook?
8. Does test code outside the synced roots (Lune, MCP, command bar) use plain Luau, never `use`/`new`/`asset`?
