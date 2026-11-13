---
name: roblox-combat
description: Server-authoritative combat for Roblox games built with ChainLink. Use when the user builds or reviews guns, hitscan or projectile weapons, melee/swords, abilities, hitboxes, damage, health, kill credit, headshots, fire rate/ammo/reload, PvP or PvE combat, or asks about lag compensation, "hits not registering", "I got shot behind a wall", hitbox expanders, reach, silent aim or other combat exploits. Covers client prediction vs server authority, hit detection models, lag compensation by rewinding position history, projectiles, melee hitboxes, weapon state and exploit-proofing.
---

# Roblox Combat

You are a multiplayer combat engineer. Combat has to feel instant for the
shooter and be fair for the target, while an exploiter controls the
shooter's client. The model that achieves all three: **the client predicts
the feel, the server decides the outcome.** The client plays animations,
muzzle flash and sound immediately and reports what it hit; the server
validates that claim against its own rewound history and is the only thing
that changes health. Generic remote validation and rate limiting live in the
`roblox-security` skill; this skill builds on it.

## 1. Who does what

| Step | Client (shooter) | Server | Other clients |
|---|---|---|---|
| Input | Plays anim, muzzle flash, sound, local tracer at once | — | — |
| Report | Sends `fire { shotId, t, origin, dir, hit? }` | Validates (sections 3-6) | — |
| Outcome | — | Applies damage, ammo, kill credit | — |
| Confirm | Hit marker / damage number on confirm | Sends `hitConfirm` to shooter | Gets `shotFx` to draw tracer, impact |

- Health, ammo, cooldowns and kills exist only on the server. The client keeps
  a *predicted* copy of ammo/cooldown for UI and corrects to server values.
- `t` is `workspace:GetServerTimeNow()` at the moment of firing, read on the
  client. It is the timestamp lag compensation rewinds to.
- `shotId` is a per-player increasing counter. The server rejects any id it has
  seen or that is not greater than the last, which kills replays.

Blink definition sketch (`connection/Combat.blink`):

```blink
event fire {
    From: Client, Type: Reliable, Call: SingleAsync,
    Data: struct {
        ShotId: u32, T: f64, Weapon: u8,
        Origin: vector, Dir: vector,
        Target: Instance(Model)?, HitPos: vector?,
    },
}
event hitConfirm { From: Server, Type: Reliable, Call: SingleAsync, Data: struct { ShotId: u32, Damage: u16, Kill: boolean } }
event shotFx { From: Server, Type: Unreliable, Call: SingleAsync, Data: struct { Shooter: u8, Origin: vector, HitPos: vector } }
```

Shots are `Reliable` (a dropped shot is lost damage); cosmetic `shotFx` to
other clients is `Unreliable`. Send player slots or ids, not
`Instance(Player)`, in high-rate events.

## 2. Pick the hit model per weapon

| Weapon | Hit model | Why |
|---|---|---|
| Hitscan (rifles, pistols) | Client reports hit, server validates with rewind | Feels instant; server still decides |
| Slow projectiles (rockets, arrows, grenades) | Server simulates by raycast steps; clients draw visuals | Travel time hides latency; no need to trust client |
| Fast projectiles | Treat as hitscan, or client-reported with rewind | Simulation would arrive too late |
| Melee | Server spatial query at swing time against rewound targets, or client-reported with range validation | Short range makes reach checks tight |
| AoE abilities | Server query at server time | Usually no need for rewind |

Pure server-side raycasting at receive time (no rewind) is the simplest and
is fine for PvE and slow PvP, but at 150 ms ping players must lead moving
targets, and "I was on him" reports follow.

## 3. Lag compensation (rewind)

Record every combat target's root position on the server ~20 times a
second for the last second, then validate a shot against where the target
was at the shooter's fire time.

```lua
-- server/HitHistoryService.luau
export type Sample = { t: number, cf: CFrame }
local HISTORY = 1.0       -- seconds kept
local RATE = 1 / 20
local history: { [Model]: { Sample } } = {}
local acc = 0

function mod:beat(dt: number)
    acc += dt
    if acc < RATE then return end
    acc = 0
    local now = workspace:GetServerTimeNow()
    for model, samples in history do
        local root = model:FindFirstChild("HumanoidRootPart") :: BasePart?
        if root then
            table.insert(samples, { t = now, cf = root.CFrame })
            while samples[1] and now - samples[1].t > HISTORY do
                table.remove(samples, 1)
            end
        end
    end
end

function mod.track(model: Model) history[model] = {} end
function mod.untrack(model: Model) history[model] = nil end -- on death/removal; no leaks

-- Was `pos` within `radius` of the target at any sample in [t - window, t]?
function mod.wasNear(model: Model, t: number, window: number, pos: Vector3, radius: number): boolean
    local samples = history[model]
    if not samples then return false end
    for _, s in samples do
        if s.t >= t - window and s.t <= t + RATE and (s.cf.Position - pos).Magnitude <= radius then
            return true
        end
    end
    return false
end
```

Validation rules:

- **Clamp the client's timestamp**: `t = math.clamp(clientT, now - MAX_REWIND, now)`
  with `MAX_REWIND` 0.3-0.5 s. Higher-ping players get less compensation
  rather than an unlimited rewind window an exploiter could abuse.
- **Check a window, not a single instant.** What the shooter saw of another
  player was already old by that player's upload latency plus interpolation,
  so accept a match anywhere in `[t - 0.25, t]`. A window with tolerance
  is more robust than trying to compute the exact delay.
- **Tolerance**: test against a sphere/box around the rewound root sized to
  the character plus ~2-3 studs. Tight enough to defeat hitbox expanders,
  loose enough for animation and jitter.
- **Origin check**: the shot's `origin` must be within ~5-8 studs of the
  shooter's own (rewound) position. Otherwise it is a teleport/silent-aim
  shot from somewhere else.
- **Line of sight**: raycast from `origin` to the claimed hit position
  against the static map only (exclude characters via `RaycastParams`
  filtering). A wall in between = reject. Use the map as it is now; map
  geometry doesn't move.
- **Range and direction**: distance ≤ weapon range; `dir` is unit length;
  the hit position lies along `dir` within the weapon's spread cone.
- The cost: "shot behind a wall" for the victim when the shooter has high
  ping. The clamp bounds how far behind. That trade-off is normal; say so to
  the user rather than promising zero.

## 4. Weapon state on the server

- Weapon stats live in one config module (`shared/Weapons.luau`): damage,
  falloff, fire interval, magazine, reload time, range, spread, headshot
  multiplier. The client reads it for prediction; the server's copy is the
  authority. Never take damage or fire rate from the remote.
- Per combatant (character model, so bots work too) per weapon, track
  `lastFire`, `ammo`, `reloadingUntil`, `lastShotId` on the server. Clear on
  death, unequip and `playerRemoving`.
- Fire-rate check against server time with a jitter allowance:
  `now - lastFire >= interval * 0.8`, and a per-second burst cap from the
  `roblox-security` rate limiter. Packets arrive bunched; exact intervals
  reject honest players.
- Reject shots while dead, stunned, reloading, out of ammo, or holding a
  different weapon than `Weapon` claims.
- Spread: if the weapon has random spread, derive it from a seed both sides
  know (e.g. `Random.new(shotSeed + shotId)`), so the server can recompute
  the allowed direction instead of trusting `dir`.

## 5. Damage and outcomes

- Apply damage only on the server: `humanoid:TakeDamage(n)` (respects
  `ForceField`) or your own health attribute. Never let the client set
  `Humanoid.Health`.
- Compute falloff, headshots and multipliers on the server. For headshots,
  check the validated hit position against the rewound head height (root
  CFrame × head offset), not the part name the client sent.
- Team check, spawn protection, self-damage and friendly fire are server
  rules.
- Kill credit: record the last damager and time on the victim; credit on
  death if within a few seconds. Don't trust "I killed X".
- One hit per target per melee swing / projectile: keep a hit set for the
  action.
- Feedback: the shooter's hit marker and damage number fire on
  `hitConfirm`. If you show them optimistically for feel, keep them
  subtle and correct them on reject.

## 6. Projectiles and melee

**Projectiles** (server-authoritative):

- Server owns `{ id, origin, velocity, spawnT }` and steps it on `beat`:
  raycast from the previous position to the next each step (no physics
  parts). Gravity and drag are in the step.
- Broadcast spawn once (`projectileSpawn { id, origin, velocity, spawnT }`).
  Clients render their own visual and fast-forward it by
  `GetServerTimeNow() - spawnT`. The shooter spawns its visual immediately
  and reconciles on the server's spawn.
- Broadcast impact (`projectileHit { id, pos }`) so clients end the visual
  at the authoritative point.
- Cap live projectiles per player and per server.

**Melee**:

- At the swing's active frame (server time, from the weapon config, not the
  client's animation event), query a box in front of the attacker with
  `workspace:GetPartBoundsInBox(cframe, size, overlapParams)` and filter to
  characters.
- For PvP feel, let the client report candidate targets and validate each:
  `HitHistoryService.wasNear(target, t, 0.25, attackerPos, reach + tolerance)`.
- Reach = config value + small tolerance. Reach exploits show up as
  distances just over that line, so log them.

## 7. Exploits and what stops them

| Exploit | Stopped by |
|---|---|
| Fire-rate / no-reload hacks | Server `lastFire`, ammo, reload state |
| Damage edits | Damage from server config only |
| Hitbox expanders | Validation against server-side rewound positions with tight tolerance |
| Shoot through walls | Server line-of-sight raycast against the map |
| Silent aim from elsewhere / teleport-kill | Origin check + movement checks (`roblox-security`) |
| Replay or duplicate shots | Increasing `shotId` |
| Kill-all scripts | Per-target validation + rate limits; one shot, one target |
| Aimbot (perfect aim) | Cannot be fully prevented; log headshot rate, snap speed and hit rate per player for review; spread and recoil limit its value |

## How to respond

- Ask (or infer) the weapon type and whether it's PvP, then pick the hit
  model from section 2 before writing code.
- Write the server validation in the same change as the client weapon. A
  weapon whose client works and whose server trusts it is a bug.
- When the complaint is about feel ("hits don't register"), check in order:
  is there rewind at all, is the window/tolerance too tight, is the fire-rate
  check exact instead of jittered, is feedback waiting on a slow round trip.
- When the complaint is about fairness ("shot behind a wall"), explain the
  rewind trade-off and tune `MAX_REWIND`, don't remove compensation.
- Test with simulated latency, several clients and PvP bots (`roblox-testing`).

## Review checklist

1. Does only the server change health, ammo, cooldowns and kills?
2. Are damage, fire rate and range read from server config, never the remote?
3. Is there a position history, and is the client timestamp clamped?
4. Is every claimed hit checked for origin, range, line of sight and rewound target position?
5. Does `shotId` reject replays, and is fire rate checked with jitter allowance?
6. Are projectiles simulated by raycast steps, not replicated physics parts?
7. Are history, weapon state and hit sets cleared on death, unequip and leave?
8. Have hits been tested at 150+ ms with the `roblox-testing` bots?
