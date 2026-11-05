---
name: blink
description: Write Blink (1Axen/blink v0.18.x) .blink networking definitions for Roblox and use the generated Luau modules. Use when creating or editing .blink files, adding remote events/functions, or calling Blink-generated networking code.
---

# Blink networking (v0.18.x)

Blink compiles `.blink` IDL files into a server module and a client module returning tables of events/functions over buffers. Docs: https://1axen.github.io/blink

## Rules
1. **Check the pinned version** (`Blink = "1Axen/blink@0.18.9"` in `chain.toml` `[Tools]`). This skill is v0 only. `1.0.0-pre.*` syntax is incompatible (`event x = {...}`, `@export`, `union`); for 1.x read https://github.com/1Axen/blink/tree/v1.0.0-pre.10/examples.
2. **Copy existing `.blink` files** in the project; they are known to compile. Never write syntax from memory.
3. **Compile after every edit**, fix errors, don't guess: `blink connection/Feature.blink` from project root (or `blink Feature` inside `connection/`; `--watch` recompiles).
4. **Never hand-edit generated output.** Edit source, recompile, commit both.

## Layout
One file per feature in `connection/`; output paths are relative to the `.blink` file:

```blink
option Casing = Camel
option ServerOutput = "../server/connection/Boat.luau"
option ClientOutput = "../client/connection/Boat.luau"

export struct PlayerInput { Move: f16[2], Jump: boolean }

event boatInput { From: Client, Type: Reliable, Call: SingleSync, Data: PlayerInput }
event boatState {
    From: Server, Type: Unreliable, Call: SingleSync,
    Data: struct { t: f64, x: f32, z: f32, yaw: f32 },
}
```
Field keys are case-insensitive, trailing commas OK, comments are `--`.

## Options (`option NAME = VALUE`)
| Option | Default | Notes |
|---|---|---|
| `Casing` | `Pascal` | **Bare** `Pascal`/`Camel`/`Snake` (`"Camel"` is wrong) |
| `ServerOutput` / `ClientOutput` / `TypesOutput` | none | Quoted paths |
| `Typescript` | `false` | Also emit `.d.ts` |
| `UsePolling` | `false` | Polling API for all events |
| `SyncValidation` | `true` | Detect yields in sync calls |
| `WriteValidations` | `false` | Type-check on fire (dev only) |
| `ManualReplication` | `false` | Exposes `StepReplication` |
| `RemoteScope` | `""` | Prefix remote names (use in packages) |

Method names by Casing — Pascal: `Fire FireAll FireList FireExcept On Iter Invoke Read Write StepReplication`; Camel: `fire fireAll fireList fireExcept on iter invoke read write`; Snake: `fire fire_all fire_list fire_except on iter invoke read write step_replication`. Event/field names keep declared case.

## Events and functions
- `From`: `Server` | `Client` (`Both` is v1 only). `From: Server` events are fired by server code, handled on client; functions are always client -> server.
- `Type`: `Reliable` | `Unreliable` (may drop/reorder, max 1000 bytes; carry a timestamp, drop stale packets).
- `Call`: `SingleAsync`/`ManyAsync` (may yield, prefer), `SingleSync`/`ManySync` (handler must never yield or error), `Polling`.
- `Data`: optional; type packs allowed: `Data: (u8, Instance?, u8[8])`.

```blink
function GetCoins { Yield: Coroutine, Data: u8, Return: u32 }  -- always Coroutine; no Future/Promise
```

```lua
-- Pascal casing; dot calls, not colon
Net.MyEvent.Fire(5)                                  -- client -> server
Net.MyEvent.Fire(player, 5)                          -- server -> one client
Net.MyEvent.FireAll(5) / FireList({p}, 5) / FireExcept(p, 5)
local disconnect = Net.MyEvent.On(function(player, value) end)  -- server gets player first
for i, player, value in Net.MyEvent.Iter() do end               -- polling
local coins = Net.GetCoins.Invoke(1)                             -- client
Net.GetCoins.On(function(player, n) return n * 2 end)            -- server
```

## Types
```blink
type Health = u8(0..100)          -- u8 u16 u32 i8 i16 i32 f16 f32 f64; ranges a..b, a.., ..b, n
type Name = string(3..20)         -- also boolean, buffer, buffer(..950)
type Pos = vector                 -- vector(0..1), vector<i16>, CFrame, CFrame<i16, f16>
type MaybeName = string(3..20)?   -- ? after the whole type
type Ids = f64[1..50]             -- arrays: T[], T[n], T[a..b], u8[][]
map Names = { [f64]: string }     -- bound: { ... }[1..100]  ((1..100) fails)
set Flags = { A, B, C }
enum State = { Idle, Walk, Run }
enum Click = "Type" { Left { Pos: vector }, Right { Pos: vector } }   -- tagged enum = union
struct Entity { Health: u8, Pos: vector, Anim: struct { First: u8? } }
struct Merged { ..A, ..B }
struct Fragment<T> { Index: u8, Data: T }   -- inline only: Data: Fragment<u8>; `type X = Fragment<u8>` fails
type Plr = Instance(Player)       -- Instance, Instance?, Instance(Sound)[10]
type C = Color3                   -- BrickColor, DateTime, DateTimeMillis; avoid `unknown`
export struct Snap { f: u8 }      -- generates Net.Snap.Write(v) -> buffer / Read(buf)

scope Combat { event Hit { From: Client, Type: Reliable, Call: SingleAsync, Data: u8 } }
import "./Common" as Common       -- `as` takes a bare identifier
```
Luau: `Net.Combat.Hit.Fire(1)`; types are `Net.Combat_Type`.

## Pitfalls
- Non-optional `Instance` arriving nil (streaming) errors and drops the rest of the packet; use `Instance?`.
- Bound everything from clients (`u8(0..100)`, `string(..20)`, `T[..50]`); ownership/cooldown checks still belong in server code.
- `f16` loses integer precision above 2048.