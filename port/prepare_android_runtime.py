#!/usr/bin/env python3
"""Device-facing compile candidates. Never change the game engine tick or actions."""
from pathlib import Path
from prepare_android_platform import replace_once

def adapt_runtime(src: Path):
    engine = src / "GbaMonoGame" / "MonoGame"
    window = engine / "GameWindowManager.cs"
    original = window.read_text(encoding="utf-8-sig")
    adapter = """#if ANDROID
using Microsoft.Xna.Framework;
using Microsoft.Xna.Framework.Graphics;

namespace GbaMonoGame;

// Android owns the surface dimensions. Do not resize it with saved desktop dimensions.
public class GameWindowManager : IGameWindowManager
{
    private readonly GraphicsDeviceManager graphics;
    public GameWindowManager(GameWindow window, GraphicsDeviceManager graphics)
    {
        this.graphics = graphics;
    }
    public Point GetResolution() => new(
        graphics.GraphicsDevice.PresentationParameters.BackBufferWidth,
        graphics.GraphicsDevice.PresentationParameters.BackBufferHeight);
    public Point WindowResolution { get => GetResolution(); set { } }
    public Point FullscreenResolution { get => GetResolution(); set { } }
    public DisplayMode DisplayMode { get => DisplayMode.Borderless; set { } }
    public bool VSync
    {
        get => graphics.SynchronizeWithVerticalRetrace;
        set { if (graphics.SynchronizeWithVerticalRetrace != value)
            { graphics.SynchronizeWithVerticalRetrace = value; graphics.ApplyChanges(); } }
    }
    public bool IsResizable() => false;
    public void SetTitle(string title) { } // Activity owns title
    public void SetResizeMode(bool allowResize, Point minSize, Point maxSize) { }
    public void SaveState() { }
    public void ApplyState() { } // Android Activity owns orientation and system bars
}
#else
"""
    window.write_text(adapter + original + "\n#endif\n", encoding="utf-8")

    # Input is sampled by the existing fixed-rate game update, not by a second game clock.
    game = engine / "GbaGame.cs"
    text = game.read_text(encoding="utf-8-sig")
    text = replace_once(text, "        Engine.Input.Update();", """#if ANDROID
        AndroidTouchPoller.Update(IsActive, GraphicsDevice);
#endif
        Engine.Input.Update();""")
    game.write_text(text, encoding="utf-8")
    poller = engine / "AndroidTouchPoller.cs"
    if poller.exists(): raise FileExistsError(poller)
    poller.write_text("""#if ANDROID
using Microsoft.Xna.Framework.Graphics;
using Microsoft.Xna.Framework.Input.Touch;

namespace GbaMonoGame;

// One snapshot per original engine update. No injected press/release timers.
internal static class AndroidTouchPoller
{
    internal static void Update(bool active, GraphicsDevice graphics)
    {
        TouchInputBridge.Clear();
        if (!active) return;
        var pp = graphics.PresentationParameters;
        if (pp.BackBufferWidth <= 0 || pp.BackBufferHeight <= 0) return;
        TouchPanel.DisplayWidth = pp.BackBufferWidth;
        TouchPanel.DisplayHeight = pp.BackBufferHeight;
        foreach (TouchLocation location in TouchPanel.GetState())
        {
            if (location.State != TouchLocationState.Pressed &&
                location.State != TouchLocationState.Moved) continue;
            var p = location.Position;
            TouchInputBridge.Set(location.Id, AndroidTouchLayout.Hit(
                p.X / pp.BackBufferWidth, p.Y / pp.BackBufferHeight));
        }
    }
}
#endif
""", encoding="utf-8")
    print("Android window adapter and game-thread multitouch polling installed (device validation pending).")
