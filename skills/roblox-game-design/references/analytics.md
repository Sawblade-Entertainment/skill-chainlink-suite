# AnalyticsService reference

All analytics calls must run on the server. View results in Creator Hub →
Analytics.

## Funnel: joined → finished_tutorial → opened_shop → purchased

```lua
-- server/AnalyticsService.luau
AnalyticsService = use "AnalyticsService"
Players = use "Players"
HttpService = use "HttpService"

local FUNNEL = "CoreFunnel"

-- One funnel session per player join so repeat visits are counted separately
local sessionIds: { [Player]: string } = {}

local function logStep(player: Player, step: number, name: string)
	local sessionId = sessionIds[player]
	if not sessionId then return end
	AnalyticsService:LogFunnelStepEvent(player, FUNNEL, sessionId, step, name)
end

function mod:playerAdded(player)
	sessionIds[player] = HttpService:GenerateGUID(false)
	logStep(player, 1, "joined")
end)

function mod:playerRemoving(player)
	sessionIds[player] = nil
end

function mod.tutorialFinished(player: Player)
	logStep(player, 2, "finished_tutorial")
end

function mod.shopOpened(player: Player)
	logStep(player, 3, "opened_shop")
end

function mod.purchased(player: Player)
	logStep(player, 4, "purchased")
end
```

Call these from your tutorial completion handler, shop-open RemoteEvent
handler, and purchase handler (server side).

## Onboarding funnel (first session only)

Use this for the tutorial itself, broken into individual steps. Roblox dedupes
per player automatically.

```lua
AnalyticsService:LogOnboardingFunnelStepEvent(player, 1, "spawned")
AnalyticsService:LogOnboardingFunnelStepEvent(player, 2, "moved")
AnalyticsService:LogOnboardingFunnelStepEvent(player, 3, "first_collect")
AnalyticsService:LogOnboardingFunnelStepEvent(player, 4, "first_upgrade")
```

## Economy events (find where the loop stalls)

```lua
-- Player earned 50 Coins from gameplay
AnalyticsService:LogEconomyEvent(
	player,
	Enum.AnalyticsEconomyFlowType.Source,
	"Coins",
	50,
	newBalance,
	Enum.AnalyticsEconomyTransactionType.Gameplay.Name,
	"collect_orb"
)

-- Player spent 200 Coins on an upgrade
AnalyticsService:LogEconomyEvent(
	player,
	Enum.AnalyticsEconomyFlowType.Sink,
	"Coins",
	200,
	newBalance,
	Enum.AnalyticsEconomyTransactionType.Shop.Name,
	"upgrade_speed_2"
)
```

## Reading the data

| Drop-off between…               | Likely cause                                | Fix to try                                              |
|---------------------------------|---------------------------------------------|---------------------------------------------------------|
| joined → finished_tutorial      | Tutorial too long, unclear, or blocking     | Shorten; let players skip into the loop                 |
| finished_tutorial → opened_shop | Shop not discoverable or no reason to open  | Prompt shop after first earn; show next upgrade on HUD  |
| opened_shop → purchased         | First upgrade too expensive or unappealing  | Make first upgrade affordable in <2 minutes             |
