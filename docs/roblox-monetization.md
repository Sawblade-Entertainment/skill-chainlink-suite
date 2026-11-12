# Roblox Monetization skill

Guidance for game passes, developer products, safe `ProcessReceipt` handling and Premium payouts in ChainLink projects. Getting purchases wrong costs players (and you) real money, so the skill is conservative: the server is the only authority, and every grant is idempotent.

It pairs with the [ChainLink](chainlink.md) skill (one `MonetizationService` owns purchases) and the [Blink](blink.md) skill (confirming purchases to the client).

## Game passes

- `UserOwnsGamePassAsync` in `pcall`, checked on join and cached per player.
- Re-check after `PromptGamePassPurchaseFinished` on the server so in-session purchases apply immediately.
- Roblox is the source of truth; never persist "not owned".

## Developer products

- Grant **only** in `ProcessReceipt`, never in `PromptProductPurchaseFinished` or from a client remote.
- Product ids and grant definitions live in one shared config module.

## ProcessReceipt done safely

- Exactly one assignment per place.
- Record `PurchaseId` and apply the grant in the same atomic write (`UpdateAsync` or the session-locked profile), so retries are no-ops.
- Return `PurchaseGranted` only after the save succeeds; `NotProcessedYet` for unknown products, absent players and any error.
- Cap receipt history; log every decision.

## Premium

- `MembershipType` + `PlayerMembershipChanged`; `PromptPremiumPurchase` only on player action.
- Premium Payouts are automatic and engagement-based; optional, non-pay-to-win perks help. No playtime inflation.

## Review order

1. One `ProcessReceipt`?
2. Idempotent on `PurchaseId`, saved atomically?
3. `PurchaseGranted` only after a durable save?
4. No client- or prompt-finished-based granting?
5. Prices from `GetProductInfo`, PolicyService respected?
