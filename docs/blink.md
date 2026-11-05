# Blink skill

Covers [Blink](https://1axen.github.io/blink) **v0.18.x**: `.blink` IDL files compiled into server and client Luau modules that send events and functions over buffers.

!!! warning "v0 only"
    `1.0.0-pre.*` syntax (`event x = {...}`, `@export`, `union`) is incompatible. Check the version pinned in `chain.toml`; for 1.x see the [v1 examples](https://github.com/1Axen/blink/tree/v1.0.0-pre.10/examples).

## Rules Claude follows

1. Check the pinned version (`Blink = "1Axen/blink@0.18.9"` under `[Tools]`).
2. Copy existing `.blink` files, which are known to compile, rather than writing syntax from memory.
3. Compile after every edit and fix the errors: `blink connection/Feature.blink` from the project root. `--watch` recompiles on change.
4. Never hand-edit generated output. Edit the source, recompile, commit both.

## File layout

One file per feature in `connection/`. Output paths are relative to the `.blink` file.

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

Field keys are case-insensitive, trailing commas are allowed, comments are `--`.

## Options

| Option | Default | Notes |
|---|---|---|
| `Casing` | `Pascal` | Bare `Pascal`, `Camel` or `Snake` (`"Camel"` is wrong) |
| `ServerOutput` / `ClientOutput` / `TypesOutput` | none | Quoted paths |
| `Typescript` | `false` | Also emit `.d.ts` |
| `UsePolling` | `false` | Polling API for all events |
| `SyncValidation` | `true` | Detect yields in sync calls |
| `WriteValidations` | `false` | Type-check on fire (dev only) |
| `ManualReplication` | `false` | Exposes `StepReplication` |
| `RemoteScope` | `""` | Prefix remote names (use in packages) |

Generated method names by casing:

| Casing | Methods |
|---|---|
| Pascal | `Fire FireAll FireList FireExcept On Iter Invoke Read Write StepReplication` |
| Camel | `fire fireAll fireList fireExcept on iter invoke read write` |
| Snake | `fire fire_all fire_list fire_except on iter invoke read write step_replication` |

Event and field names keep their declared case.

## Events and functions

- **`From`**: `Server` or `Client` (`Both` is v1 only). Server events are fired by the server and handled on the client. Functions always go client to server.
- **`Type`**: `Reliable` or `Unreliable`. Unreliable packets may drop or reorder and are limited to 1000 bytes; include a timestamp and drop stale ones.
- **`Call`**: `SingleAsync`/`ManyAsync` (may yield; preferred), `SingleSync`/`ManySync` (handler must never yield or error), `Polling`.
- **`Data`**: optional; type packs are allowed, e.g. `Data: (u8, Instance?, u8[8])`.

```blink
function GetCoins { Yield: Coroutine, Data: u8, Return: u32 }
```

Use `Yield: Coroutine` always; `Future` and `Promise` are not supported.

```lua
-- Pascal casing; use dot calls, not colon
Net.MyEvent.Fire(5)                                          -- client -> server
Net.MyEvent.Fire(player, 5)                                  -- server -> one client
Net.MyEvent.FireAll(5)
Net.MyEvent.FireList({ p }, 5)
Net.MyEvent.FireExcept(p, 5)
local disconnect = Net.MyEvent.On(function(player, value) end)  -- server handler gets player first
for i, player, value in Net.MyEvent.Iter() do end               -- polling
local coins = Net.GetCoins.Invoke(1)                             -- client
Net.GetCoins.On(function(player, n) return n * 2 end)            -- server
```

## Types

```blink
type Health = u8(0..100)          -- u8 u16 u32 i8 i16 i32 f16 f32 f64; ranges a..b, a.., ..b, n
type Name = string(3..20)         -- also boolean, buffer, buffer(..950)
type Pos = vector                 -- vector(0..1), vector<i16>, CFrame, CFrame<i16, f16>
type MaybeName = string(3..20)?   -- ? goes after the whole type
type Ids = f64[1..50]             -- arrays: T[], T[n], T[a..b], u8[][]
map Names = { [f64]: string }     -- bound: { ... }[1..100]  ((1..100) fails)
set Flags = { A, B, C }
enum State = { Idle, Walk, Run }
enum Click = "Type" { Left { Pos: vector }, Right { Pos: vector } }   -- tagged enum (union)
struct Entity { Health: u8, Pos: vector, Anim: struct { First: u8? } }
struct Merged { ..A, ..B }
struct Fragment<T> { Index: u8, Data: T }   -- inline use only: Data: Fragment<u8>
type Plr = Instance(Player)       -- Instance, Instance?, Instance(Sound)[10]
type C = Color3                   -- BrickColor, DateTime, DateTimeMillis; avoid `unknown`
export struct Snap { f: u8 }      -- generates Net.Snap.Write(v) -> buffer / Read(buf)

scope Combat { event Hit { From: Client, Type: Reliable, Call: SingleAsync, Data: u8 } }
import "./Common" as Common       -- `as` takes a bare identifier
```

In Luau a scoped event is `Net.Combat.Hit.Fire(1)` and its types are `Net.Combat_Type`.

## Pitfalls

- A non-optional `Instance` that arrives nil (streaming) errors and drops the rest of the packet. Use `Instance?`.
- Bound everything that comes from clients (`u8(0..100)`, `string(..20)`, `T[..50]`). Ownership and cooldown checks still belong in server code.
- `f16` loses integer precision above 2048.
- `type X = Fragment<u8>` fails; use generics inline.
