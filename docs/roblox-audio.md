# Roblox Audio skill

Audio guidance for ChainLink projects: sound effects, music, mixing with SoundGroups, 3D placement, the newer Audio API, uploads and permissions. It pairs with the [ChainLink](chainlink.md) skill (an `SfxController` and the `asset` macro), the [Blink](blink.md) skill (server → client sound triggers), [Roblox Performance](roblox-performance.md) (cleanup and leaks) and [Roblox UI Design](roblox-ui-design.md) (volume settings and feedback sounds).

The skill's stance: check permissions, playback side, SoundGroup and cleanup before mixing or polish.

## Sound vs the Audio API

- `Sound` + `SoundGroup` is the default for SFX, music and UI.
- The Audio API (`AudioPlayer` → `Wire` → `AudioEmitter`/`AudioDeviceOutput`, heard by an `AudioListener`) is for real signal graphs: shared effect chains, voice processing, multiple listeners. Its property names are still settling, so the skill verifies them against the Creator Hub docs.
- One system per category; follow what the project already uses.

## Placement

- 3D: parent to a part or attachment. `InverseTapered` roll-off, tight `RollOffMaxDistance` (60-150 studs).
- 2D: parent to `SoundService` or `PlayerGui` for UI, music and announcer. Don't parent global sounds to streamed geometry.

## SoundGroups

Every sound belongs to a group under a `Master` group (Music, SFX, UI, Ambience, Voice). In-game sliders set group volumes and persist them; effects (compressor, EQ) live on groups. Keep per-sound volume around 0.3-0.7 for headroom.

## Client vs server

With `RespectFilteringEnabled` on, client-played sounds stay local and server-played sounds replicate.

| Sound | Plays on |
|---|---|
| UI, local hit-confirm, music | Client |
| Own weapon fire | Client immediately; others via server event |
| World events | Client, from a Blink event (enum + position) |

Sound is cosmetic: never gate gameplay on it.

## Pooling and preloading

Templates created once, cloned for overlapping 3D sounds and destroyed on `Ended`; `PlayLocalSound` for 2D one-shots; looping sounds tied to an owner's cleanup; caps on simultaneous copies. Preload short critical SFX with `ContentProvider:PreloadAsync`, not every music track.

## Music

One music Controller owns the track. Crossfade over 1-2 s; duck music under dialogue by tweening the group or a sidechained compressor, relative to the player's slider.

## Uploads and permissions

Audio files go in `assets/` and are referenced with `asset`. Audio only plays if it is owned by or shared with the experience owner, so `[Roblox] UserId`/`GroupId` must match the place owner. "Silent live, fine in Studio" means permissions first.

## Review order

1. Every sound in a SoundGroup with persisted sliders?
2. Played on the right side?
3. Ad-hoc sounds destroyed; loops tied to cleanup?
4. Sensible 3D roll-off; 2D sounds not on world geometry?
5. Assets owned by the experience owner, ids from `asset`?
6. Critical cues also visual?
