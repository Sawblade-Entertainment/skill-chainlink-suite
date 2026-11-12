# Using the skills together

The three skills map onto the layers of a ChainLink game.

| Layer | Skill | Lives in |
|---|---|---|
| Project structure, lifecycle, packages | `chainlink` | `chain.toml`, `server/*Service.luau`, `client/*Controller.luau` |
| Client/server messaging | `blink` | `connection/*.blink` and generated modules |
| UI | `vide` | `client/views/*.luau` |
| UI look and feel | `roblox-ui-design` | applied to every view |
| 3D art | `chainlink-model` | `tools/*_model.py`, `art/`, `assets/*.fbx` |

## Example: a countdown HUD driven by the server

Ask Claude: *"Show a round countdown on every player's screen."*

1. **Blink** defines the message in `connection/Round.blink`:

    ```blink
    option Casing = Camel
    option ServerOutput = "../server/connection/Round.luau"
    option ClientOutput = "../client/connection/Round.luau"

    event roundTime { From: Server, Type: Reliable, Call: SingleAsync, Data: u16 }
    ```

    Claude compiles it with `blink connection/Round.blink`.

2. **ChainLink** Service fires it on the server:

    ```lua
    -- server/RoundService.luau
    Round = use "./connection/Round"

    function mod:start()
        for t = 60, 0, -1 do
            Round.roundTime.fireAll(t)
            task.wait(1)
        end
    end
    ```

3. **Vide** view renders it (see [Vide](vide.md) for the `Hud` module).

4. **ChainLink** Controller connects them:

    ```lua
    -- client/HudController.luau
    Round = use "./connection/Round"
    Hud = use "./views/Hud"

    function mod:start()
        Hud:show(game.Players.LocalPlayer.PlayerGui)
        Round.roundTime.on(function(t)
            Hud:setRemaining(t)
        end)
    end
    ```

Finally, `chainlink serve` and sync in Studio.

## Version pinning

```toml
[Tools]
Blink = "1Axen/blink@0.18.9"

[Packages]
vide = "centau/vide@0.4.1"
```

If your project pins a different major version of a tool than the skill targets, tell Claude; the skills instruct it to stop and consult upstream docs rather than guess.
