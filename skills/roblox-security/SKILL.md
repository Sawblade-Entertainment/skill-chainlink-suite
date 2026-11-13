---
name: roblox-security
description: Roblox anti-exploit and remote-security guidance for ChainLink projects. Use when the user adds or reviews any RemoteEvent/RemoteFunction or Blink event/function, asks about exploiters, cheaters, speed/teleport/noclip hacks, remote spam, rate limiting, validating client input, sanity checks, kicking or banning, or "can a hacker do X". Covers the client/server trust boundary, argument validation, rate limits, ownership/range/cooldown checks, server-side movement checks, and safe responses to violations.
---

# Roblox Security

You are a pragmatic Roblox security engineer. Assume every client is running
an exploit executor: it can read and change every LocalScript, fire any
remote with any arguments at any rate, move its own character anywhere, and
see everything that replicates to it. Security lives on the server. Client
checks are UX, not protection. Aim for "a cheater can't gain anything
meaningful", not "cheating is impossible", and never punish legitimate
players for lag.

## 0. The trust boundary

| The client controls | The server must decide |
|---|---|
| Its own character's physics (position, velocity) | Damage, health, death |
| What it sends over remotes, and how often | Currency, inventory, XP, unlocks |
| Its UI, camera, local effects | Cooldowns, ammo, round state |
| Parts it has network ownership of | Ownership of tools, items, plots |

- **Remotes carry intent, not results.** `requestEquip(slot)`,
  `requestFire(origin, direction, shotId)` — never `addCoins(50)`,
  `setHealth(100)`, `damage(target, 30)`.
- **Never trust client-reported values** for anything the server can know or
  compute itself: prices, damage numbers, positions of other players, time.
- **Don't send secrets to the client.** Anything in `ReplicatedStorage`,
  `Workspace` or a remote payload is readable. Keep loot tables, answers,
  admin lists and server logic in `ServerScriptService`/`ServerStorage`
  (`server/`, `prefab/` in ChainLink).
- **Never invoke the client and wait for an answer** (`RemoteFunction:InvokeClient`).
  An exploiter can yield forever or error; the server thread hangs. Use an
  event and a timeout instead.
- Filtering is always on: client changes to instances don't replicate, *except* physics of parts the client owns
  (its character, and unanchored parts near it unless you `SetNetworkOwner(nil)`).

## 1. Validate every argument

Blink's types are the first gate: bound every field the client sends
(`u8(1..10)`, `string(..32)`, `T[..50]`, `Instance(Tool)?`). Blink rejects
packets that don't decode. It does **not** know your game rules, so every
handler still checks:

1. **Type and shape** (only needed for plain `RemoteEvent`s; Blink covers it).
   Check `typeof`, reject NaN and inf: `x ~= x` is NaN,
   `math.abs(x) == math.huge` is inf. NaN slips through `<`/`>` comparisons.
2. **Ownership**: the tool/item/plot/pet belongs to *this* player.
   `tool.Parent == player.Character or tool.Parent == player.Backpack`.
3. **State**: the player is alive, in a round, not stunned, has the item
   equipped, has the currency.
4. **Range**: the target or position is within reach of the player's
   *server-side* character position (with lag tolerance, section 4).
5. **Cooldown/rate**: section 2.

Reject silently (return early, optionally log). Don't tell the client why.

```lua
-- server/ShopService.luau
Shop = use "./connection/Shop"
Items = use "/shared/Items"
Data = use "./DataService"
RateLimit = use "./RateLimitService"

function mod:start()
    Shop.buyItem.on(function(player: Player, itemId: number)
        local item = Items[itemId]
        if not item or not item.buyable then return end            -- unknown/disabled id
        if not RateLimit.allow(player, "buyItem", 5, 1) then return end
        local data = Data.get(player)
        if not data or data.coins < item.price then return end       -- price from server config
        if data.owned[itemId] then return end                        -- idempotent
        data.coins -= item.price
        data.owned[itemId] = true
        Shop.owned.fire(player, itemId)
    end)
end
```

## 2. Rate limits

Every client → server event gets a per-player limit. Token bucket per
(player, action), cleared on `PlayerRemoving`:

```lua
-- server/RateLimitService.luau
export type Bucket = { tokens: number, last: number }
local buckets: { [Player]: { [string]: Bucket } } = {}
local strikes: { [Player]: number } = {}

function mod.flag(player: Player, reason: string)
    strikes[player] = (strikes[player] or 0) + 1
    -- log and escalate here (section 5)
end

-- `burst` tokens max, refilled at `perSecond`
function mod.allow(player: Player, action: string, burst: number, perSecond: number): boolean
    local byAction = buckets[player]
    if not byAction then
        byAction = {}
        buckets[player] = byAction
    end
    local now = os.clock()
    local b = byAction[action]
    if not b then
        b = { tokens = burst, last = now }
        byAction[action] = b
    end
    b.tokens = math.min(burst, b.tokens + (now - b.last) * perSecond)
    b.last = now
    if b.tokens < 1 then
        mod.flag(player, "rate:" .. action)
        return false
    end
    b.tokens -= 1
    return true
end

function mod:playerRemoving(player: Player)
    buckets[player] = nil
    strikes[player] = nil
end
```

- Set limits from real usage: fire rate for weapons, ~2-5/s for UI actions,
  ~1/s for purchases/trades. Allow a burst for network jitter (packets arrive
  bunched).
- Gameplay cooldowns (ability recharge) are a separate, exact check against
  server time — a rate limit only stops spam.
- Expensive handlers (DataStore calls, pathfinding, raycasts over large
  areas) get the tightest limits, or a per-server global limit too.
- Blink queues reliable events; an exploiter can still send thousands per
  second. Dropping over-limit calls early keeps the server's frame time safe.

## 3. Common exploit patterns and the fix

| Exploit | Server-side fix |
|---|---|
| Fire "give/add/set" remote | Remove it; remotes only express intent |
| Buy with negative/huge quantity | Bound with Blink (`u8(1..99)`), recheck price × qty server-side |
| Buy/claim twice by double-firing | Idempotency: check-and-set in one step, no yield in between |
| Use an item they don't own | Ownership check on every use |
| Interact from across the map | Range check against server character position |
| Instance arg pointing at someone else's object | Check the instance is a descendant of something the player owns |
| Spam to lag the server | Rate limits; drop before doing work |
| Auto-clicker farming | Server cooldowns; diminishing returns; this is a design problem too |
| Touch any part (`firetouchinterest`) | Treat `Touched` as a hint: re-check distance/state server-side |
| `ProximityPrompt`/`ClickDetector` from far away | Re-check distance and state in the server handler; don't trust activation alone |
| Read hidden data | Don't replicate it; send only what this player may see |

Yields between a check and a write are race windows: `if data.coins >= price then task.wait() data.coins -= price`
lets two concurrent calls both pass. Do check-and-mutate synchronously.

## 4. Movement sanity checks

The client owns its character's physics, so speed, fly, teleport and noclip
hacks replicate. Check on the server, loosely:

- Sample `HumanoidRootPart.Position` every ~0.5 s (on `beat`, throttled;
  not per frame for every player). Flag when horizontal distance exceeds
  `WalkSpeed * elapsed * 1.5 + slack` (slack ~8-10 studs for jitter).
- Exempt legitimate movers: server teleports (record a "moved by server"
  timestamp and skip the next check), vehicles/seats, knockback, launch pads,
  respawn, and the first few seconds after join.
- Flying: track time airborne with no ground below (raycast down) beyond
  what your jump/fall allows.
- Noclip: raycast from the last good position to the new one against map
  collision; a hit through a wall means they phased.
- **Respond by correcting, not banning**: move the player back to the last
  valid position. Escalate only on repeated, large violations.

Never rely on a client-side anti-cheat LocalScript; exploiters delete or hook
it. A client check can catch lazy scripts, but treat its reports as
untrusted hints, never as the only signal.

## 5. Responding to violations

- Keep a per-player strike counter with decay (`RateLimitService.flag` above
  is the hook; decay it over time).
  Lag, packet loss and low frame rates produce occasional false positives.
- Ladder: ignore the request → correct the state (rubber-band, refund,
  rollback) → log → kick after sustained violations → ban only for
  unambiguous cheats (impossible values, not borderline speeds).
- Kick with `player:Kick("reason")`. For bans use `Players:BanAsync` (the
  Ban API, which also catches alt accounts when enabled) rather than a
  homemade DataStore list; confirm the exact config fields against the
  Creator Hub docs before writing it.
- Log flags with `userId`, reason, values and server time (AnalyticsService
  custom events or your own logging) so you can tune thresholds from data.
- Never put the anti-cheat's thresholds or logic in replicated code.

## How to respond

- When the user adds a remote, write the server handler with validation and
  a rate limit as part of the same change, not as a follow-up.
- When reviewing, read every client → server handler and ask: "if a cheater
  fires this 1000 times a second with any arguments they like, what do they
  get?" Report the worst answer first.
- Prefer fixing the design (server computes the value) over adding a check
  to a client-supplied value.
- For combat and hit validation, load the `roblox-combat` skill; for
  purchases, `roblox-monetization`; to test with a cheating bot,
  `roblox-testing`.

## Review checklist

1. Does any remote express a result ("give", "set", "damage") instead of intent?
2. Is every client-sent field bounded in the `.blink` file?
3. Does every handler check ownership, state and range against server data?
4. Is every client → server event rate limited, with buckets cleared on leave?
5. Any yield between a check and the write it guards?
6. Any `InvokeClient`, secrets in `ReplicatedStorage`, or anti-cheat logic on the client?
7. Are movement checks lenient, exempting server teleports, vehicles and knockback?
8. Do violations correct and log first, and only kick/ban on clear evidence?
