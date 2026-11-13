# Roblox UI Design skill

UX/UI design guidance for Roblox interfaces: layout, hierarchy, spacing, color, typography, motion, feedback, accessibility and cross-platform rules. It is the companion to the [Vide](vide.md) skill: Vide covers *how* to build UI, this covers *what good looks like*. Apply it before writing a view, and use the checklist when reviewing one.

## Design principles

In priority order:

1. **Clarity over decoration.** A player should know what a screen is for in under a second.
2. **One primary action per screen.** Exactly one visually dominant button.
3. **Don't block play.** HUD stays out of the center; modals only for decisions that require a stop.
4. **Consistency.** Same component, same look, same behavior. Build a small kit and reuse it.
5. **Feedback for every input.** Hover, press, success, failure, loading.
6. **Progressive disclosure.** Show the basics; reveal detail on demand.

## Layout

- Use scale (`UDim2.fromScale`) for containers. Use offset only for fixed things like strokes and icons, paired with `UIAspectRatioConstraint` / `UISizeConstraint`.
- Use layouts (`UIListLayout`, `UIGridLayout`) plus `UIPadding`; set `Padding` on the layout.
- Anchor to edges with matching `AnchorPoint` and `Position`.
- Respect safe areas: `ScreenGui.ScreenInsets = CoreUISafeInsets`, keep interactive elements 2-3% from edges, avoid the top-left and top-right corners.
- Reserve the screen center for gameplay.
- Use `AutomaticSize` for text containers and lists, with a `UISizeConstraint` for max width.
- Set `ScreenGui.DisplayOrder` per layer:

| Layer | DisplayOrder |
|---|---|
| HUD | 1 |
| Menus | 10 |
| Modals | 20 |
| Toasts | 30 |

- Breakpoints on `Camera.ViewportSize.X`: phone < 700, tablet 700-1200, desktop > 1200. Expose an `isSmall` source and use it in views.

## Spacing and sizing

- Multiples of 4px: 4 tight, 8 default, 12, 16 section, 24 panel, 32+ page.
- Hit targets at least 44x44px; at least 56px on mobile for frequent actions.
- Corner radius: 6-8px buttons and inputs, 12-16px cards and panels, `UDim.new(1, 0)` for pills. Inner radius = outer radius minus padding.

## Visual hierarchy

- Three tiers per panel: **primary** (filled accent), **secondary** (outlined/ghost), **tertiary** (text-only, muted).
- Group related controls with space before reaching for divider lines.
- Change at most two of size, weight, color and position at once.
- At most two font families. Prefer `BuilderSans`, `GothamSSm`/`Montserrat`, and `FredokaOne` for playful titles. Use `FontFace` weights.
- Type scale (desktop px): caption 12, body 14-16, label 18, subtitle 20-24, title 28-36, display 48+. Scale down 15-20% on phone. Use `TextScaled` only inside constrained containers with a `UITextSizeConstraint`.
- Line length up to about 60 characters; `TextWrapped = true`.

## Color

- Define a `Theme` module once; never hardcode colors in views.
- Roles: `background`, `surface`, `surfaceRaised`, `border`, `text`, `textMuted`, `accent`, `accentText`, `success`, `warning`, `danger`, `info`.
- Dark surfaces by default with about three elevation steps (for example `#141518`, `#1E2024`, `#2A2D33`).
- One accent for primary actions; semantic colors only for their meaning.
- Contrast at least 4.5:1 for body text, 3:1 for large text and icons.
- Overlays: `BackgroundTransparency` 0.2-0.5 with a 1px `UIStroke` at 10-20% white. Avoid pure black and pure white.
- Gradients: subtle, vertical, on primary buttons or headers only.

## Components

| Component | Key rules |
|---|---|
| Button | States: idle, hover (lighten 8%), pressed (scale 0.96, darken), disabled (40% opacity), loading. Verb-first labels |
| Icon button | Icon plus 44px hit area; tooltip on hover or long-press |
| Panel / card | Surface color, radius 12-16, padding 16, optional header with title and close |
| Modal | 50-60% black backdrop, centered card up to about 480x600, primary action right. Closes on backdrop click, Escape and gamepad B |
| Toast | Top-center or bottom-right, 3-5s, stack of at most 3, slide and fade |
| List / grid | `UIGridLayout` driven by breakpoint; `ScrollingFrame` with `AutomaticCanvasSize = Y` |
| Progress bar | Track plus accent fill; animate, never jump |
| Tabs | Underline or pill; at most 5 visible |
| Input | Clear focus ring, muted placeholder, at least 40px tall |
| Currency / numbers | Icon plus separators; abbreviate above 10k (12.4K, 1.2M) |

## Motion and feedback

| Kind | Duration |
|---|---|
| Micro (hover, press) | 80-120ms |
| Standard (open, close, slide) | 180-250ms |
| Large (page transitions) | 300-400ms |

Nothing over 500ms unless it's a celebration.

- Easing: `Quad`/`Quint` Out to enter, In to exit, `Back` Out for pop-ins and rewards, `Linear` only for progress and spinners.
- Animate transparency and scale or position together. Use springs (for example `vide.spring`) so motion is interruptible; never queue tweens.
- Every async action shows a loading state and disables its trigger; every result confirms.
- Use short, distinct SFX for click, confirm, error and reward, fired together with the visual.
- Respect `UserGameSettings.ReducedMotion` and never flash more than 3 times per second.

## Game-specific UX

- **HUD:** minimal, edge-anchored, mostly non-interactive; fade elements that haven't changed.
- **Onboarding:** teach by doing, one highlighted element and one sentence at a time; persist completion.
- **Shops:** show value, price and discount; one primary "Buy"; confirm Robux spends; no dark patterns.
- **Rewards:** motion, sound and a clear "Claim"; scale with rarity.
- **Errors:** say what happened and what to do ("Not enough coins - need 50 more").
- **Empty states:** friendly message plus an action.
- **Settings:** group logically and show current values.

## Cross-platform and accessibility

- Detect input via `UserInputService` (`TouchEnabled`, `GamepadEnabled`, `KeyboardEnabled`, `LastInputType`) and expose it as a source.
- **Mobile:** see below.
- **Gamepad:** set `Selectable` and `NextSelection*` (or `GuiService.SelectedObject`), show a visible selection style, B closes, A confirms.
- **Keyboard:** Escape closes the top modal, Enter confirms, Tab moves between inputs.
- Never rely on color alone. Support `GuiService.PreferredTransparency`. Stay readable at 100% UI scale on 720p.
- Localization-ready: no text in images, allow about 30% string growth.

## Mobile

- **Safe areas:** `ScreenInsets = CoreUISafeInsets` for HUD and menus (clears notches, the home indicator and the Roblox top bar); `None` only for full-bleed backgrounds. Align top-bar buttons with `GuiService.TopbarInset`.
- **Touch controls:** keep UI off the thumbstick (bottom-left) and jump button (bottom-right); arc action buttons around the jump button.
- **Touch targets:** at least 48px, 56px for frequent or combat actions, 8px apart, enforced with `UISizeConstraint.MinSize`.
- Panels set `Active = true` so drags don't turn the camera; no hover-only information; body text at least 14px; text inputs in the top half, above the on-screen keyboard.
- Check layouts in the Device Emulator; check frame rate on a real phone (quality tiers are in [Roblox Performance](roblox-performance.md)).

## Review checklist

- [ ] One obvious primary action; the rest visually subordinate.
- [ ] Sizes in scale or constrained offset; layouts and padding, no hand placement.
- [ ] Hit targets at least 44px (48-56px on touch); safe areas respected; center clear.
- [ ] Nothing under the thumbstick or jump button; inputs stay above the on-screen keyboard.
- [ ] Colors from `Theme` only; contrast at least 4.5:1.
- [ ] 4-pt spacing, consistent radii, at most 2 fonts.
- [ ] Hover, press, disabled and loading states; every action gives feedback.
- [ ] Transitions 100-300ms, interruptible, reduced motion respected.
- [ ] Works on phone, desktop and gamepad.
- [ ] Error, empty and loading states designed.
- [ ] Text wraps, doesn't clip, and survives longer strings.
