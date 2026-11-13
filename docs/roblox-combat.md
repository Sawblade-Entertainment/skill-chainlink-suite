# Roblox Combat skill

Server-authoritative combat for ChainLink games: hitscan, projectile and melee weapons, lag compensation by rewinding position history, weapon state, damage and the exploits each design choice stops. It builds on the [Roblox Security](roblox-security.md) skill (validation and rate limits) and uses [Blink](blink.md) for the fire, confirm and effect events.

Invoke it with `/roblox-combat`, or let Claude load it when you build weapons, abilities or PvP, or report "hits not registering" or "shot behind a wall".

The skill's stance: **the client predicts the feel, the server decides the outcome.** The shooter sees muzzle flash and hears the shot instantly; health, ammo, cooldowns and kills only ever change on the server.

## Flow

1. The client plays effects and sends `fire { shotId, t, origin, dir, target?, hitPos? }`, where `t` is `workspace:GetServerTimeNow()`.
2. The server validates the claim and applies damage.
3. The shooter gets `hitConfirm` (reliable); everyone else gets `shotFx` (unreliable).

## Hit models

| Weapon | Model |
|---|---|
| Hitscan | Client reports hit, server validates with rewind |
| Slow projectiles | Server simulates with raycast steps; clients draw visuals |
| Melee | Server box query at swing time, or client-reported with rewound range checks |
| AoE | Server query at server time |

## Lag compensation

The server records each target's root CFrame about 20 times a second for the last second. A shot is checked against where the target was at the shooter's fire time:

- clamp the timestamp to at most 0.3-0.5 s in the past;
- accept a match anywhere in a short window before it, with a few studs of tolerance;
- check the shot origin is near the shooter, the range and spread are valid, and nothing in the static map blocks line of sight.

The cost is the occasional "shot behind a wall" for the victim when the shooter has high ping; the clamp bounds it.

## Weapon state and damage

Stats come from one `shared/Weapons.luau` config; the server's copy is authoritative. Per-player `lastFire`, ammo, reload state and an increasing `shotId` (no replays) live on the server, with a jitter allowance on fire rate. Damage, falloff, headshots (from the validated hit position, not the part name the client sent), teams and kill credit are server rules.

## Exploits covered

Fire-rate and damage edits, hitbox expanders, shooting through walls, silent aim and teleport kills, replayed shots and kill-all scripts. Aimbots can't be fully prevented; the skill logs per-player accuracy stats for review.

## Review order

1. Only the server changes health, ammo, cooldowns and kills?
2. Damage, fire rate and range from server config?
3. Position history kept and client timestamps clamped?
4. Claimed hits checked for origin, range, line of sight and rewound position?
5. `shotId` replay protection and jitter-tolerant fire rate?
6. Projectiles simulated by raycast steps, not physics parts?
7. History and weapon state cleared on death, unequip and leave?
8. Tested at 150+ ms with bots?
