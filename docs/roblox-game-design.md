# Roblox Game Design skill

Design, launch and iteration guidance for Roblox games: thumbnails and click-through rate, core loop design, using ad spend as a data source, and funnel logging with `AnalyticsService`. It pairs with the [Roblox UI Design](roblox-ui-design.md) skill for the look of the shop and HUD, and the [Roblox Performance](roblox-performance.md) skill for keeping the game within budget once the loop works.

Invoke it with `/roblox-game-design`, or let Claude load it when you are planning a game, deciding what to build next, preparing a launch, evaluating ad spend or instrumenting onboarding and shop funnels.

The skill's stance: Roblox is a discovery-driven, retention-scored platform. The algorithm promotes games that get clicked and that keep players, so every recommendation serves one of those two things.

## Core principles

### 1. The thumbnail is the first feature

Discovery surfaces weight click-through rate (CTR) heavily. A game with a great loop and a bad thumbnail never gets seen.

- Show the core fantasy in one glance, with a single clear focal point and high contrast.
- It must be readable at about 100px wide.
- Treat thumbnails and icons as things to A/B test, not polish once. Roblox supports multiple thumbnails: rotate them and measure.
- When asked "why isn't my game getting players", the skill asks about CTR and the thumbnail before gameplay.

### 2. Build one loop, not ten features

The core loop is **play → earn → upgrade → repeat**. Get it fun with placeholder art before adding anything else.

"Fun" means a 2-5 minute session feels satisfying, the next upgrade is visible and reachable, and the player can say what they are working toward. Extra systems (pets, trading, quests, housing, PvP modes) do not rescue a weak loop; they dilute dev time and hide the real problem.

When you propose a feature list, the skill asks which single loop each feature strengthens, and defers any that strengthen none. You should be able to name the loop in one sentence.

### 3. Ads buy data, not players

A small ad spend (tens of dollars, not hundreds) exists to answer one question: **does the game retain?** Read D1 retention and average session length from the ad cohort.

| D1 retention | Reading |
|---|---|
| Under ~15% | The loop or onboarding is broken |
| 20-30%+ | You can start scaling |

These are guidelines, not rules. If retention is bad, change the game rather than raising the budget; scaling spend on a leaky game just buys more churn.

Sequence: fix thumbnail CTR → small ad test → read retention → change the game → repeat. Scale spend only once retention is stable across two tests.

### 4. Instrument the funnel

Every game should log at minimum: `joined → finished_tutorial → opened_shop → purchased`.

- `AnalyticsService:LogFunnelStepEvent` for ordered funnels.
- `AnalyticsService:LogOnboardingFunnelStepEvent` for the first-session onboarding path.
- `AnalyticsService:LogEconomyEvent` for currency sources and sinks, to see where players stall before the first upgrade.

The biggest drop-off is usually between `joined` and `finished_tutorial`. If that step loses more than half of players, shorten the tutorial or let players skip straight into the loop.

All analytics calls run on the server. Results appear in Creator Hub → Analytics.

## Reading the funnel

| Drop-off between | Likely cause | Fix to try |
|---|---|---|
| `joined` → `finished_tutorial` | Tutorial too long, unclear or blocking | Shorten it; let players skip into the loop |
| `finished_tutorial` → `opened_shop` | Shop not discoverable, or no reason to open it | Prompt the shop after the first earn; show the next upgrade on the HUD |
| `opened_shop` → `purchased` | First upgrade too expensive or unappealing | Make the first upgrade affordable in under 2 minutes |

## Core loop checklist

Answer each in one sentence. Any "no" is the next thing to build, before any new feature.

- **Play:** can a new player start the core action within 10 seconds of spawning? Is it fun to do 20 times in a row with no rewards?
- **Earn:** does the player earn something visible within 30 seconds, and is it obvious what and why?
- **Upgrade:** is the first upgrade affordable within about 2 minutes? Does it visibly change the play step? Is the next upgrade and its cost always visible?
- **Repeat:** after upgrading, is the next goal clear? Is there a reason to return tomorrow (persistent progress, timers, dailies)?

Red flags:

- The pitch lists more than one noun before "and then you...".
- Dev time goes into systems players reach after 30+ minutes while D1 retention is below 15%.
- You cannot describe the loop in one sentence.

## Analytics examples

The skill's `references/analytics.md` contains working Luau for the server side. In a ChainLink project this lives in a Service, with one funnel session per player join so repeat visits count separately:

```lua
-- server/AnalyticsService.luau
local FUNNEL = "CoreFunnel"
local sessionIds: { [Player]: string } = {}

local function logStep(player: Player, step: number, name: string)
    local sessionId = sessionIds[player]
    if not sessionId then return end
    AnalyticsService:LogFunnelStepEvent(player, FUNNEL, sessionId, step, name)
end
```

Call `logStep` from the tutorial completion handler (step 2, `finished_tutorial`), the shop-open remote handler (step 3, `opened_shop`) and the purchase handler (step 4, `purchased`), all server side. Step 1 (`joined`) is logged when the player is added. See the [ChainLink](chainlink.md) and [Blink](blink.md) skills for the Service and remote conventions.

Onboarding steps for the first session (Roblox dedupes per player automatically):

```lua
AnalyticsService:LogOnboardingFunnelStepEvent(player, 1, "spawned")
AnalyticsService:LogOnboardingFunnelStepEvent(player, 2, "moved")
AnalyticsService:LogOnboardingFunnelStepEvent(player, 3, "first_collect")
AnalyticsService:LogOnboardingFunnelStepEvent(player, 4, "first_upgrade")
```

Economy events record a currency source or sink, with the amount, the new balance, a transaction type and an item name:

```lua
AnalyticsService:LogEconomyEvent(
    player,
    Enum.AnalyticsEconomyFlowType.Source,
    "Coins", 50, newBalance,
    Enum.AnalyticsEconomyTransactionType.Gameplay.Name,
    "collect_orb"
)
```

## How Claude responds

- Leads with the diagnosis, then the fix, applying only the relevant principle instead of listing all four.
- Prefers concrete, measurable next steps, such as "rotate in a thumbnail with a single character and a visible reward, check CTR in 48h".
- Writes modern Luau with server-side logging only, and type annotations where they help readability.
- Reviews a game plan in this order:
    1. What is the loop, in one sentence?
    2. What is the thumbnail hook?
    3. What is instrumented?
    4. What should be cut?
