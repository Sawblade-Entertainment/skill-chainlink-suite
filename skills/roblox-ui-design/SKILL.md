---
name: roblox-ui-design
description: UX/UI design guidance for Roblox interfaces — layout, hierarchy, spacing, color, typography, motion, feedback, accessibility, and cross-platform (PC/mobile/console) rules. Use alongside the vide skill whenever designing, reviewing, or restyling any Roblox UI so it is intuitive, engaging, and modern.
---

# Roblox UI Design

Companion to the `vide` skill: `vide` covers *how* to build; this covers *what good looks like*. Apply before writing a view, and use the checklist when reviewing one.

## Design principles (in priority order)
1. **Clarity over decoration** — a player should know what a screen is for in under 1 second.
2. **One primary action per screen** — exactly one visually dominant button; everything else is secondary/tertiary.
3. **Don't block play** — HUD stays out of the center; modals only for decisions that truly require a stop.
4. **Consistency** — same component, same look, same behavior everywhere. Build a small kit and reuse it.
5. **Feedback for every input** — hover, press, success, failure, loading. Silence feels broken.
6. **Progressive disclosure** — show the basics; reveal detail on demand (expand, tooltip, tab).

## Layout
- **Use scale, not offset** for positions/sizes of containers (`UDim2.fromScale`). Use offset only for fixed things like 1px strokes or icon sizes, and pair with `UIAspectRatioConstraint` / `UISizeConstraint` so they don't balloon on 4K or crush on phones.
- **Always use layouts** (`UIListLayout`, `UIGridLayout`) + `UIPadding` instead of hand-placed children. Set `Padding` on the layout, not margins on items.
- **Anchor to screen edges/corners** with `AnchorPoint` matching `Position` (e.g. `AnchorPoint = (1,1)`, `Position = fromScale(1,1)` for bottom-right).
- **Respect safe areas**: enable `ScreenGui.ScreenInsets = CoreUISafeInsets` and keep interactive elements ≥ 2–3% of screen away from edges; avoid the top-left (Roblox menu button) and top-right (chat/leaderboard) corners.
- **Reserve the center** of the screen for gameplay. HUD goes to edges; prompts/dialogs center only when they demand attention.
- **Use `AutomaticSize`** for text containers and lists so content never clips; combine with `UISizeConstraint` for max width.
- **Z-order**: `ScreenGui.DisplayOrder` per layer (HUD 1, menus 10, modals 20, toasts 30). Never fight with `ZIndex` across ScreenGuis.
- Common breakpoints by `Camera.ViewportSize.X`: phone < 700, tablet 700–1200, desktop > 1200. Derive a `isSmall` source from this and use it in views (fewer columns, larger hit targets, collapsed labels).

## Spacing & sizing (4-pt grid)
- Use multiples of 4px for padding/gaps: 4 (tight), 8 (default), 12, 16 (section), 24 (panel), 32+ (page).
- **Hit targets ≥ 44×44px** on all platforms, ≥ 56px on mobile for frequent actions. Pad invisibly if the visual is smaller.
- Corner radius: 6–8px for buttons/inputs, 12–16px for cards/panels, 24px+ or `UDim.new(1,0)` for pills/avatars. Keep one radius per component tier.
- Nested radii: inner = outer − padding.

## Visual hierarchy
- Three tiers max per panel: **Primary** (filled accent button, largest text), **Secondary** (outlined/ghost, medium), **Tertiary** (text-only, small, muted).
- Group related controls visually (shared container, shared background) and separate groups with space before you reach for divider lines.
- Size + weight + color + position all signal importance; change at most two at once.
- Limit to 2 font families (one display, one body). Prefer modern Roblox fonts: `BuilderSans`, `GothamSSm`/`Montserrat`, `FredokaOne` for playful titles. Use `FontFace` with weights, not separate fonts.
- Type scale (desktop px): caption 12, body 14–16, label 18, subtitle 20–24, title 28–36, display 48+. Scale down ~15–20% on phone. Set `TextScaled` only inside size-constrained containers (always add `UITextSizeConstraint` with Min/Max).
- Line length ≤ ~60 characters; `TextWrapped = true`; `TextXAlignment` left for paragraphs, center only for short labels/titles.

## Color
- Define a palette once (a `Theme` module of Color3s) and only reference it. Never hardcode colors in views.
- Roles: `background`, `surface`, `surfaceRaised`, `border`, `text`, `textMuted`, `accent`, `accentText`, `success`, `warning`, `danger`, `info`. Dark surfaces are the modern default for game UI; keep ~3 elevation steps (e.g. #141518 → #1E2024 → #2A2D33).
- One accent color for primary actions; semantic colors only for their meaning (red = danger/destroy, green = success/buy confirm, yellow = warning/currency).
- Text contrast ≥ 4.5:1 for body, ≥ 3:1 for large text and icons. Muted text should still be readable (~60–70% opacity of text color, not 30%).
- Use `BackgroundTransparency` 0.2–0.5 on overlays plus a subtle `UIStroke` (1px, 10–20% white) for "glass" panels; avoid pure black panels and pure white text — use near-black/near-white.
- Gradients: subtle (≤ 10–15% luminance shift), vertical, on primary buttons or headers only. No rainbow.

## Components (build these once, reuse)
- **Button**: states idle / hover / pressed / disabled / loading. Hover = lighten 8%, pressed = scale 0.96 + darken, disabled = 40% opacity + no hover. Label is verb-first ("Buy for 100", "Equip", "Close").
- **Icon button**: icon + invisible 44px hit area + tooltip/label on hover (desktop) or long-press (mobile).
- **Panel/Card**: surface color, radius 12–16, padding 16, optional header row with title (left) and close ×(right).
- **Modal**: dim backdrop (black @ 50–60%), centered card max ~480×600px, title, body, action row (primary right, cancel left/secondary). Close on backdrop click, Escape, and gamepad B.
- **Toast/notification**: top-center or bottom-right, auto-dismiss 3–5s, stack max 3, slide + fade in.
- **List/inventory grid**: `UIGridLayout` with `FillDirectionMaxCells` driven by breakpoint; `ScrollingFrame` with `CanvasSize = 0` + `AutomaticCanvasSize = Y`, `ScrollBarThickness` 4–6, thin custom scrollbar color.
- **Progress bar**: track (border color) + fill (accent) + optional label; animate fill, never jump.
- **Tabs**: underline or pill style, active uses accent, never more than 5 visible.
- **Input**: clear focus ring (accent stroke), placeholder in muted text, ≥ 40px tall.
- **Currency/number display**: icon + formatted number (thousands separators, abbreviations above 10k: 12.4K, 1.2M).

## Motion & feedback
- Durations: micro (hover/press) 80–120ms, standard (open/close, slide) 180–250ms, large (page transitions) 300–400ms. Nothing in UI should exceed 500ms unless it's a celebration.
- Easing: `Quad`/`Quint` Out for entering, In for exiting, `Back` Out (small overshoot) for pop-ins and rewards, `Linear` only for progress/spinners.
- Animate **transparency + scale/position** together for open/close (e.g. scale 0.92→1 with fade). Use a spring/tween source (e.g. `vide.spring`) so values are interruptible — never queue tweens.
- Every clickable element has hover (desktop) and press feedback; every async action shows a loading state and disables the trigger; every result confirms (color flash, check icon, sound).
- Use sound sparingly: distinct short SFX for click, confirm, error, reward. Sound and visual feedback fire together.
- Respect `UserGameSettings.ReducedMotion` (fall back to instant transitions) and never flash > 3 times/sec.

## Game-specific UX
- **HUD**: minimal, edge-anchored, mostly non-interactive. Health/resources bottom-left or top-left; objectives top-right/top-center; hotbar bottom-center; minimap top-right. Fade HUD elements that haven't changed in a while.
- **Onboarding**: teach by doing — one highlighted element + one sentence at a time, dismissable, never a wall of text. Persist completion.
- **Shops/monetization**: show value clearly (what you get, price, discount vs. original), make "Buy" the single primary action, confirmation for Robux spends, never dark patterns (fake timers, hidden costs, trick buttons).
- **Rewards**: celebrate with motion + sound + a clear "Claim"/"Continue"; scale celebration with rarity.
- **Errors**: say what happened and what to do ("Not enough coins — need 50 more"), never raw codes.
- **Empty states**: friendly message + action ("No items yet — visit the shop").
- **Settings**: group logically (Audio, Controls, Graphics, Accessibility); every control shows its current value.

## Cross-platform & accessibility
- Detect input type via `UserInputService` (`TouchEnabled`, `GamepadEnabled`, `KeyboardEnabled`, `LastInputType`) and expose it as a source; views adapt (hide hover-only hints on touch, show button glyphs on gamepad).
- **Mobile**: bigger targets, thumb zones (bottom corners easiest), no hover-dependent info, avoid tiny close ×s, keep critical buttons off the top edge.
- **Gamepad**: set `Selectable`, `NextSelectionUp/Down/Left/Right` or use `GuiService.SelectedObject` + auto-selection; provide a visible selection style (`SelectionImageObject` or custom accent stroke); B closes, A confirms.
- **Keyboard**: Escape closes top-most modal; Enter confirms; Tab moves between inputs.
- Never rely on color alone — pair with icon or text. Support `GuiService.PreferredTransparency` for panels. Keep text readable at 100% UI scale on a 720p screen.
- Localize-ready: no text baked into images, allow ~30% string growth, use `AutomaticSize` for labels.

## Review checklist
- [ ] One obvious primary action; secondary/tertiary visually subordinate.
- [ ] All sizes in scale (or constrained offset); layouts + padding, no hand placement.
- [ ] Hit targets ≥ 44px; safe areas respected; center of screen clear for HUD.
- [ ] Colors from Theme only; text contrast ≥ 4.5:1; semantic colors used correctly.
- [ ] 4-pt spacing; consistent radii; ≤ 2 fonts; type scale respected.
- [ ] Hover/press/disabled/loading states exist; every action gives feedback.
- [ ] Transitions 100–300ms, interruptible, respect reduced motion.
- [ ] Works on phone, desktop, and gamepad (tested or reasoned through breakpoints).
- [ ] Error/empty/loading states designed, not just the happy path.
- [ ] Text wraps, doesn't clip, and survives longer strings.