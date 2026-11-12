---
name: roblox-monetization
description: Roblox monetization guidance for ChainLink projects. Use when the user adds or reviews game passes, developer products, MarketplaceService prompts, ProcessReceipt callbacks, purchase granting, Robux pricing, Premium benefits or Premium Payouts. Covers ownership checks, safe idempotent receipt processing with DataStores, client/server trust boundaries, and Premium engagement payouts. Purchases cost real money: be conservative and never grant or charge twice.
---

# Roblox Monetization

You are a careful Roblox monetization engineer. A bug here either loses a player's Robux (they paid, got nothing) or duplicates value (they got it twice). Both are worse than a crash. Favour correctness over cleverness, keep all granting on the server, and make every grant idempotent.

## 0. Ground rules

- **The server is the only authority.** Clients may *prompt* purchases; they never decide what was bought or grant anything. Ignore any remote that says "I bought X".
- **One `MarketplaceService.ProcessReceipt` per place.** It is a callback, not an event: assigning it twice silently replaces the first. Own it in exactly one ChainLink Service (e.g. `MonetizationService`) and route products from a table.
- **Never hardcode prices in logic.** Prices change on the website. Display prices via `MarketplaceService:GetProductInfo(id, Enum.InfoType.Product)` / `Enum.InfoType.GamePass` (cache, `pcall`, fall back to hiding the price).
- **Wrap every MarketplaceService/DataStore call in `pcall`.** They are web calls and fail.
- **Keep ids in one config module** (`shared/Products.luau`): `{ [productId] = { kind = "Coins", amount = 100 } }`. No magic numbers scattered across scripts.

## 1. Game passes (one-time, permanent)

```lua
local function ownsPass(player: Player, passId: number): boolean
	local ok, owns = pcall(MarketplaceService.UserOwnsGamePassAsync, MarketplaceService, player.UserId, passId)
	return ok and owns
end
```

- Check on join, cache the result per player (clear in `PlayerRemoving`), and apply the perk.
- `UserOwnsGamePassAsync` is cached by the engine and may not reflect a purchase made this session. Also listen to `MarketplaceService.PromptGamePassPurchaseFinished` **on the server**: when `wasPurchased` is true, re-verify with `UserOwnsGamePassAsync` (or trust the server-side signal) and grant immediately.
- If the ownership check errors, do not permanently deny: retry later or on respawn. Never write "doesn't own" to persistent data.
- Do not store pass ownership in your DataStore as the source of truth; Roblox is the source of truth (refunds/gifts change it).
- Prompt from client or server with `MarketplaceService:PromptGamePassPurchase(player, passId)`.

## 2. Developer products (consumable, repeatable)

Prompt with `PromptProductPurchase(player, productId)`. **Do not grant in `PromptProductPurchaseFinished`** — it is informational only and is not a guarantee of payment. Grant only in `ProcessReceipt`.

## 3. ProcessReceipt done safely

Contract:

- Return `Enum.ProductPurchaseDecision.PurchaseGranted` **only after** the grant is durably saved.
- Return `Enum.ProductPurchaseDecision.NotProcessedYet` on any failure, unknown product, or absent player. Roblox will retry the receipt (on next join / periodically), and refunds unprocessed receipts after a while.
- The callback can be invoked **more than once for the same `PurchaseId`** (retries, multiple servers, crashes after saving but before returning). Grants must be idempotent keyed on `receiptInfo.PurchaseId`.
- It must not yield forever; never error out of it (wrap the body in `pcall`).

Recommended pattern: record the purchase id and apply the grant **in the same atomic write** to the player's data, so "granted" and "recorded" can never diverge.

```lua
local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local Products = require(ReplicatedStorage.Shared.Products)

local handlers: { [string]: (data: any, info: any) -> () } = {
	Coins = function(data, product) data.coins += product.amount end,
}

local function processReceipt(info)
	local product = Products[info.ProductId]
	if not product then
		warn("Unknown product", info.ProductId)
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end
	local player = Players:GetPlayerByUserId(info.PlayerId)
	if not player then
		return Enum.ProductPurchaseDecision.NotProcessedYet -- retried on next join
	end

	local ok, err = pcall(function()
		playerStore:UpdateAsync("Player_" .. info.PlayerId, function(data)
			data = data or defaultData()
			data.receipts = data.receipts or {}
			if data.receipts[info.PurchaseId] then
				return data -- already granted; idempotent
			end
			handlers[product.kind](data, product)
			data.receipts[info.PurchaseId] = os.time()
			return data
		end)
	end)
	if not ok then
		warn("Receipt failed", info.PurchaseId, err)
		return Enum.ProductPurchaseDecision.NotProcessedYet
	end

	-- reflect in live session state only after the save succeeded
	return Enum.ProductPurchaseDecision.PurchaseGranted
end

MarketplaceService.ProcessReceipt = function(info)
	local ok, result = pcall(processReceipt, info)
	return if ok then result else Enum.ProductPurchaseDecision.NotProcessedYet
end
```

Notes:

- **Session-locked data libraries** (ProfileStore/ProfileService, etc.): don't `UpdateAsync` behind the library's back. Mutate the loaded profile (purchase id + grant together), force/await a save, and only then return `PurchaseGranted`. Most such libraries ship a receipt helper; use it.
- Cap the stored receipt history (keep the last ~50-100 ids, drop the oldest) so the data doesn't grow forever.
- Update in-memory state and UI (via Blink) after the durable write, never before.
- Grant things that don't depend on the player being in-server (currency, items) — never "spawn a part next to the player" as the only effect.
- Log every receipt (PurchaseId, PlayerId, ProductId, decision) to aid support and refund disputes.
- Test in Studio (test purchases are free) including: player leaves mid-purchase, DataStore failure (simulate by erroring), and the callback firing twice with the same PurchaseId.

## 4. Premium

- Check with `player.MembershipType == Enum.MembershipType.Premium`; react to `Players.PlayerMembershipChanged` (fires when a player subscribes in-game).
- Upsell with `MarketplaceService:PromptPremiumPurchase(player)` only from a clear, player-initiated action.
- **Premium Payouts** are paid automatically by Roblox based on how much time Premium subscribers spend in your experience. You don't call any API; you earn more by making the game worth staying in. Optional Premium perks (small cosmetic or convenience bonuses, a Premium-only door) encourage engagement and subscriptions, but must not be pay-to-win or required to progress.
- Never artificially inflate playtime (AFK farms, anti-idle tricks for Premium users); it violates Roblox terms.

## 5. Policy and UX

- Respect `PolicyService:GetPolicyInfoForPlayerAsync` — e.g. `ArePaidRandomItemsRestricted` blocks paid loot boxes in some regions; hide them for those players.
- Paid random items must show odds. Don't use dark patterns (fake timers, misleading "free" buttons, prompts on join).
- Show what is being bought and its price before prompting; disable the buy button while a prompt is open to prevent double prompts.
- Grant feedback (sound/toast) after the server confirms, driven by a Blink event.

## Review checklist

1. Exactly one `ProcessReceipt` assignment, in one server Service?
2. Every grant keyed on `PurchaseId` and saved atomically with the receipt record?
3. `PurchaseGranted` returned only after a successful save; `NotProcessedYet` on every failure path?
4. Nothing granted from `PromptProductPurchaseFinished` or a client remote?
5. Game pass checks `pcall`ed, cached, re-checked after in-session purchase, never persisted as "not owned"?
6. Prices read from `GetProductInfo`, not hardcoded?
7. Premium perks optional and non-pay-to-win; `PlayerMembershipChanged` handled?
8. PolicyService respected for random paid items?
