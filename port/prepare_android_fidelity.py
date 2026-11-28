#!/usr/bin/env python3
"""Android GBA startup and opt-in diagnostics. The existing game Intro is retained."""
from pathlib import Path
from prepare_android_platform import replace_once

def adapt_fidelity(src):
    path=src/"GbaMonoGame.Rayman3/Rayman3GbaGame.cs"
    target=path.parent/"FaithfulTraceRecorder.cs"
    if target.exists(): raise FileExistsError(target)
    text=path.read_text(encoding="utf-8-sig")
    text=replace_once(text,
      "    protected override Frame CreateInitialFrame() => new TitleScreen(false);",
      """#if ANDROID
    protected override Frame CreateInitialFrame()
    {
        // The Android host has already validated and imported the GBA ROM.
        // Initialize on the game thread, rather than the desktop selector's Task.Run.
        Rom.Init(Game.Rayman3, Platform.GBA);
        Engine.Settings.Local.General.LastPlayedPlatform = Platform.GBA;
        GameTime.Reset();
        return new Intro();
    }
#else
    protected override Frame CreateInitialFrame() => new TitleScreen(false);
#endif""")
    text=replace_once(text,
      "            Dictionary<int, string> songTable = Rayman3SoundTables.GbaSongTable;",
      "            Dictionary<int, string> songTable = new(Rayman3SoundTables.GbaSongTable);")
    text=replace_once(text,"    protected override void InitGame()",
      "#if ANDROID\n    private FaithfulTraceRecorder _faithfulTrace;\n#endif\n\n    protected override void InitGame()")
    text=replace_once(text,
      "            localizationManager: new LocalizationManager(Rom.Loader.ReadTextBanks()));",
      "            localizationManager: new LocalizationManager(Rom.Loader.ReadTextBanks()));\n#if ANDROID\n        _faithfulTrace = FaithfulTraceRecorder.TryStart();\n#endif")
    text=replace_once(text,"        Engine.UnInitGame();\n        Rayman3.UnInitGame();",
      "#if ANDROID\n        _faithfulTrace?.Dispose();\n        _faithfulTrace = null;\n#endif\n        Engine.UnInitGame();\n        Rayman3.UnInitGame();")
    source=Path(__file__).with_name("FaithfulTraceRecorder.cs")
    target.write_bytes(source.read_bytes())
    path.write_text(text,encoding="utf-8")
    print("Prepared original GBA intro startup and optional game-thread trace.")
