---
name: roblox-audio
description: Roblox audio guidance for ChainLink projects. Use when the user adds or reviews sound effects, music, ambience, UI sounds, SoundGroups and mixing, 3D/positional sound and RollOff, the newer Audio API (AudioPlayer, AudioEmitter, AudioListener, AudioDeviceOutput, Wire), ducking or crossfades, volume sliders/settings, preloading sounds, or uploading audio and fixing sounds that don't play (asset permissions). Covers Sound vs Audio API, client vs server playback, pooling and cleanup, and mobile/accessibility rules.
---

# Roblox Audio

You are a practical Roblox audio engineer. Most audio bugs are one of four things: a sound the experience isn't allowed to play (permissions), a sound played on the wrong side (server vs client), a sound with no SoundGroup so the player can't turn it down, or sounds created per event and never cleaned up. Fix those first; mixing and polish come after. Where this skill says "verify against the Creator Hub docs", the API is newer and still changing: check before relying on exact property names.

## 1. Sound vs the Audio API

| Use | When |
|---|---|
| `Sound` (+ `SoundGroup`, `*SoundEffect`) | Default for SFX, music, UI. Simple, well understood, works everywhere. |
| Audio API (`AudioPlayer` → `Wire` → `AudioEmitter` / `AudioDeviceOutput`, heard through an `AudioListener`) | You need a real signal graph: shared effect chains, voice chat processing (`AudioDeviceInput`), multiple listeners, routing one source to several outputs. |

- Audio API shape: an `AudioPlayer` produces a stream; a `Wire` connects `SourceInstance` to `TargetInstance`; an `AudioEmitter` (parented to a part/attachment) puts it in the 3D world; an `AudioListener` hears emitters and is wired to an `AudioDeviceOutput` (the speakers). Effects (`AudioReverb`, `AudioEqualizer`, `AudioCompressor`, `AudioFader`, ...) sit between wires.
- Property names on Audio API objects (e.g. `AudioPlayer.Asset`, distance attenuation on `AudioEmitter`, `SoundService.DefaultListenerLocation`) have changed during rollout: verify against the Creator Hub docs before writing them.
- Don't mix both systems for the same category: a Music group on `Sound` and music on `AudioPlayer` means two volume paths to keep in sync.
- Pick one per project, record it in a shared `Audio` module, and follow what the project already uses.

## 2. 2D vs 3D placement

- **3D**: a `Sound` parented to a `BasePart` or `Attachment` is positional. Use for footsteps, impacts, weapons, ambience emitters.
- **2D**: a `Sound` parented to `SoundService`, `PlayerGui` or a non-part container plays at full volume everywhere. Use for UI, music, announcer, the local player's own hit-confirm.
- RollOff on 3D sounds:
  - `RollOffMode = InverseTapered` is the usual choice (realistic falloff, reaches silence at max distance). `Linear`/`LinearSquare` for gameplay-readable cues with a hard edge.
  - `RollOffMinDistance`: full volume inside this radius (~5-10 studs for small props).
  - `RollOffMaxDistance`: silent beyond (keep it tight, 60-150 studs; huge values mean every client mixes sounds they can't meaningfully hear).
- Parent 3D sounds to an `Attachment` at the source (muzzle, foot) rather than the model's root part.
- Streamed-out parts take their sounds with them: don't parent long music or global cues to world geometry.

## 3. SoundGroups and player volume

Every sound belongs to a `SoundGroup`. No exceptions: an ungrouped sound can't be controlled by the player's sliders.

```
SoundService
  Master (SoundGroup)
    Music   (SoundGroup)
    SFX     (SoundGroup)
    UI      (SoundGroup)
    Ambience(SoundGroup)
    Voice   (SoundGroup)   -- dialogue/announcer, not voice chat
```

- Nest groups by parenting `SoundGroup`s; effective volume multiplies down the tree.
- Set `sound.SoundGroup = SoundService.Master.SFX` when creating the sound, or set it in the prefab.
- In-game sliders write `SoundGroup.Volume` per category and persist it in player data. Don't touch the player's Roblox master volume (that's theirs, in the Roblox menu).
- Put mixing effects on groups, not individual sounds: a `CompressorSoundEffect` on SFX to stop stacked explosions clipping, `EqualizerSoundEffect` to carve room for dialogue.
- Mix with headroom: keep typical `Sound.Volume` around 0.3-0.7 so many simultaneous sounds don't clip, and turn groups down rather than single sounds up.

## 4. Who plays the sound: client vs server

`SoundService.RespectFilteringEnabled = true` (keep it on): sounds played by a client are heard only by that client; sounds played by the server replicate to everyone.

| Sound | Play on |
|---|---|
| UI clicks, local hit-confirm, local footsteps, music | Client, immediately |
| The local player's own weapon fire | Client immediately (prediction); other players hear it via a server event |
| World events (explosion, door, round start) | Client, triggered by a Blink event from the server |
| Rare, long, global stingers | Server-played is acceptable, but a Blink event is still more flexible |

Prefer "server sends a small event, every client plays it locally" over server-played sounds: clients can skip sounds out of range, respect their own settings, and you send an enum, not an instance.

```blink
-- connection/Sfx.blink
enum SfxId = { Hit, Explosion, Pickup, RoundStart }
event playSfx { From: Server, Type: Unreliable, Call: SingleSync, Data: struct { id: SfxId, pos: vector? } }
```

Sound is cosmetic: never gate gameplay on a sound having played or finished, and never trust a client remote that asks the server to play a sound for everyone without rate-limiting it.

## 5. Pooling, reuse and cleanup

Creating a `Sound` per gunshot and forgetting it is a memory leak (see `roblox-performance` §4).

```lua
-- client/SfxController.luau
SoundService = use "SoundService"
Sfx = use "./connection/Sfx"
HitId = asset "sfx/hit.ogg"         -- assign `asset` directly; the macro only expands on assignment
PickupId = asset "sfx/pickup.ogg"

local defs: { [string]: { id: string, group: string, volume: number } } = {
    Hit = { id = HitId, group = "SFX", volume = 0.5 },
    Pickup = { id = PickupId, group = "SFX", volume = 0.4 },
}

local templates: { [string]: Sound } = {}

function mod:init()
    for name, def in defs do
        local s = new "Sound"
        s.SoundId = def.id
        s.Volume = def.volume
        s.SoundGroup = SoundService.Master[def.group]
        s.Parent = SoundService
        templates[name] = s
    end
end

function mod.play(name: string, at: BasePart | Attachment?)
    local template = templates[name]
    if not template then return end
    if not at then
        SoundService:PlayLocalSound(template) -- 2D, one-shot, no instance to clean up
        return
    end
    local s = template:Clone()
    s.Parent = at
    s.Ended:Once(function() s:Destroy() end)
    s:Play()
end

function mod:start()
    Sfx.playSfx.on(function(data)
        if not data.pos then
            mod.play(data.id) -- 2D
            return
        end
        local at = new "Attachment" -- temporary 3D emitter point
        at.Position = data.pos
        at.Parent = workspace.Terrain
        mod.play(data.id, at)
        task.delay(5, at.Destroy, at) -- longer than the longest one-shot
    end)
end
```

- Reuse one `Sound` for rapid repeats where overlap doesn't matter; clone from a template when it does, and always `Destroy` on `Ended`.
- Looping sounds (engines, ambience) are created once per owner and destroyed with it (Trove/Janitor).
- Cap simultaneous instances of the same sound (e.g. 6 footsteps) and drop the rest.

## 6. Preloading

- Preload short, latency-critical SFX in a loading screen: `ContentProvider:PreloadAsync({ sound1, sound2 })` (pass instances, not raw ids). Wrap in `pcall`.
- Don't preload every music track; long audio streams fine. Check `sound.IsLoaded` / `sound.Loaded` before relying on `TimeLength`.

## 7. Music: crossfade and ducking

- Crossfade by tweening `Volume` of the outgoing track to 0 and the incoming one up over 1-2 s, then `Stop()` the old one. Never hard-cut music.
- Keep one music Controller that owns the current track; areas/rounds request a track, they don't play their own.
- **Ducking**: lower Music when dialogue or a big cue plays. Simple version: tween `Master.Music.Volume` down ~50% and back. Automatic version: a `CompressorSoundEffect` on the Music group with `SideChain` set to the Voice group (verify against the Creator Hub docs for current behavior).
- Respect the player's music slider: duck relative to their setting, never above it.

## 8. Uploading and permissions

- Put files in `assets/` (`.mp3 .ogg .wav .flac`) and reference them with `asset "sfx/hit.ogg"`. Ask before running `chainlink assets` (run `--dry-run` first).
- **Audio only plays if the experience is allowed to use it.** It must be owned by the same user or group that owns the experience, or explicitly shared with it. Make sure `[Roblox] UserId`/`GroupId` in `chain.toml` matches the place owner, or uploads will succeed and then play silently.
- "Sound is silent live but fine in my Studio" → check permissions first, then `SoundGroup` volume, then `RespectFilteringEnabled` (played on the wrong side).
- New audio goes through moderation; a freshly uploaded id may not play for a short while.
- Trim silence from the start of SFX files, normalize loudness across a set, and prefer `.ogg` for size.

## 9. Mobile and accessibility

- Phone speakers are small: test with the device speaker, keep low-end content out of critical cues, and leave headroom (compressor on Master).
- Never put critical information only in sound (enemy behind you, timer ending): pair it with a visual cue. Many players play muted.
- Provide per-category sliders and a mute; keep them in a Settings screen (see `roblox-ui-design`).
- Avoid harsh, repeated high-frequency sounds and sudden loud stingers.

## How to respond

- Ask (or infer) the symptom: silent sound, wrong people hear it, too loud/clipping, leak, latency. Each maps to a section above.
- When writing code: strict-typed Luau, a central `Audio`/`SfxController` with named SFX, every sound in a `SoundGroup`, ids via `asset`, server → client triggers via Blink enums.
- Don't invent Audio API properties; when using it, say which ones need checking against the Creator Hub docs.

## Review checklist

1. Every `Sound` assigned to a `SoundGroup`; groups controllable by in-game sliders and persisted?
2. Played on the right side (client for local/UI/responsiveness, Blink event for world sounds)?
3. Ad-hoc sounds destroyed on `Ended`; looping sounds tied to an owner's cleanup?
4. 3D sounds parented to parts/attachments with sensible `RollOffMaxDistance`; 2D sounds not parented to world geometry?
5. Asset owned by / shared with the experience owner; ids from `asset`, not hardcoded?
6. Critical cues duplicated visually; music crossfades and ducks instead of hard-cutting?
