# Roblox Security skill

Guidance for keeping a ChainLink game safe from exploiters: the client/server trust boundary, validating every remote argument, per-player rate limits, server-side movement checks and how to respond to violations without punishing laggy players. It pairs with the [Blink](blink.md) skill (bounded types are the first gate), the [Roblox Combat](roblox-combat.md) skill for hit validation, and the [Roblox Testing](roblox-testing.md) skill for a cheating bot that exercises the checks.

Invoke it with `/roblox-security`, or let Claude load it when you add or review remotes or ask what a cheater could do.

The skill's stance: assume every client runs an exploit executor. Security lives on the server; client checks are UX. Aim for "a cheater gains nothing meaningful", not "cheating is impossible".

## Trust boundary

- Remotes carry **intent** (`requestEquip(slot)`), never results (`addCoins(50)`).
- The server computes everything it can know itself: prices, damage, positions, time.
- Nothing secret replicates: loot tables, admin lists and server logic stay in `server/` and `prefab/`.
- Never `InvokeClient` and wait; an exploiter can hang the server thread.

## Validating arguments

Every handler checks, in order: type and shape (Blink covers this; plain remotes must reject NaN and inf), ownership, state, range against the server-side character, and rate. Rejections are silent. Check-and-mutate happens without yielding in between, so double-fired requests can't both pass.

## Rate limits

A token bucket per player and action, cleared on `PlayerRemoving`. Limits come from real usage with room for bunched packets: weapon fire rate for combat, a few per second for UI actions, about one per second for purchases and trades. Gameplay cooldowns are a separate, exact check.

## Movement checks

Characters are client-owned, so speed, fly, teleport and noclip hacks replicate. The server samples positions about twice a second, allows walk speed plus slack, exempts server teleports, vehicles, knockback and spawns, raycasts for noclip, and responds by moving the player back rather than banning.

## Responding

Strikes with decay; ignore → correct → log → kick on sustained violations → ban (`Players:BanAsync`) only for unambiguous cheats. Thresholds and anti-cheat logic never go in replicated code.

## Review order

1. Any remote that expresses a result instead of intent?
2. Every client-sent field bounded in the `.blink` file?
3. Ownership, state and range checked against server data?
4. Every client → server event rate limited, buckets cleared on leave?
5. Any yield between a check and its write?
6. Any `InvokeClient`, replicated secrets or client-side anti-cheat logic?
7. Movement checks lenient with the right exemptions?
8. Violations corrected and logged before any kick or ban?
