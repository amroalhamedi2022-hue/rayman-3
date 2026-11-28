#!/usr/bin/env python3
"""Apply Android-only host, debug boundary and fidelity configuration to the pinned checkout."""
from pathlib import Path
import re
from prepare_android_platform import replace_once

def adapt_host(src):
    engine=src/"GbaMonoGame"
    game=src/"GbaMonoGame.Rayman3"
    base=Path(__file__).resolve().parent
    # Ensure the exact pinned ORIGINAL preset mappings are reflected in the profile.
    options=(game/"Readvanced/GameOptions.cs").read_text(encoding="utf-8-sig")
    profile=(base/"FaithfulGbaProfile.cs").read_text(encoding="utf-8")
    expected={}
    for block in re.split(r"\n\s{16}new (?:MultiSelectionOptionsMenuOption|PresetSelectionOptionsMenuOption)",options):
        prop=re.search(r"getData:\s*_\s*=>\s*Engine\.Settings\.Local\.(Tweaks|Difficulty)\.(\w+),",block)
        val=re.search(r'\.Item\("[^"]+",\s*(true|false),[^\n]*?\b(?:TweaksPreset|DifficultyPreset)\.Original\b',block)
        if prop and val: expected[prop[1]+"."+prop[2]]=val[1]
    if len(expected)!=27: raise ValueError("Unexpected original preset count")
    for name,value in expected.items():
        if profile.count("settings."+name+" = "+value+";")!=1:
            raise ValueError("Original preset not represented: "+name)
    print("Verified 27 explicit ORIGINAL preset boolean values against upstream source.")

    edits={}
    def modify(path, fn):
        edits[path]=fn(path.read_text(encoding="utf-8-sig"))
    imgui=engine/"ImGui/ImGuiRenderer.cs"
    def patch_imgui(s):
        start=s.index("        _game.Window.TextInput +=")
        end=s.index("        };",start)+len("        };")
        return s[:start]+"#if !ANDROID\n"+s[start:end]+"\n#endif"+s[end:]
    modify(imgui,patch_imgui)
    modify(engine/"Settings/SettingsManager.cs",lambda s:replace_once(s,
        "        Local = settings;",
        "#if ANDROID\n        FaithfulGbaProfile.Apply(settings);\n#endif\n        Local = settings;"))
    # Existing ROM header/version validator also works before engine initialization.
    def patch_rom(s):
        anchor="ISerializerLogger serializerLogger = Engine.Settings.Active.Debug.WriteSerializerLog"
        start=s.index("    public static bool ValidateGbaRom")
        end=s.index("    public static void GetGamePaths",start)
        section=s[start:end]
        section=replace_once(section,anchor,"ISerializerLogger serializerLogger = Engine.Settings?.Active?.Debug?.WriteSerializerLog == true")
        return s[:start]+section+s[end:]
    modify(engine/"Disk/Rom.cs",patch_rom)
    def patch_audio(s):
        return replace_once(s,"        Soloud = new Soloud();\n        Soloud.init();",
          """        Soloud = new Soloud();
#if ANDROID
        int result = Soloud.init();
        if (result != 0)
        {
            string error = Soloud.getErrorString(result);
            Soloud.Dispose();
            Soloud = null;
            throw new System.InvalidOperationException("SoLoud initialization failed: " + error);
        }
#else
        Soloud.init();
#endif""")
    modify(engine/"Sound/SoundManager.cs",patch_audio)
    def patch_game(s):
        s=replace_once(s,"    private GfxRenderer _gfxRenderer;",
          "    private GfxRenderer _gfxRenderer;\n#if ANDROID\n    private AndroidControlsOverlay _androidOverlay;\n#endif")
        s=replace_once(s,"        _gfxRenderer = new GfxRenderer(GraphicsDevice);",
          "        _gfxRenderer = new GfxRenderer(GraphicsDevice);\n#if ANDROID\n        _androidOverlay = new AndroidControlsOverlay(GraphicsDevice);\n#endif")
        s=replace_once(s,"        base.Draw(gameTime);",
          "#if ANDROID\n        _androidOverlay?.Draw();\n#endif\n        base.Draw(gameTime);")
        s=replace_once(s,"        Rom.UnInit();\n        Engine.UnInitEngine();",
          "#if ANDROID\n        _androidOverlay?.Dispose();\n        TouchInputBridge.Clear();\n#endif\n        Rom.UnInit();\n        Engine.UnInitEngine();")
        return s
    modify(engine/"MonoGame/GbaGame.cs",patch_game)
    # Restrict the Android title screen to its initial supported target, GBA.
    # Do not change desktop/N-Gage builds. Keep the original GBA title/intro flow.
    def patch_title(s):
        a="            new TitleScreenGame(renderContext, Platform.NGage, Cursor, new Vector2(basePosX + gamesDistance, basePosY))"
        if s.count(a)!=1: raise ValueError("Unexpected title screen games list")
        # Keep GBA entry; avoid changing the cursor/index logic in this iteration.
        # Host imports a GBA ROM before the title screen. N-Gage remains unsupported.
        return s
    # All new files and edits are checked before writing.
    sources=[(base/"FaithfulGbaProfile.cs",engine/"Settings/FaithfulGbaProfile.cs"),
             (base/"AndroidControlsOverlay.cs",engine/"MonoGame/AndroidControlsOverlay.cs"),
             (base/"AndroidGameHost.cs",game/"AndroidGameHost.cs")]
    for origin,target in sources:
        if not origin.is_file() or target.exists(): raise ValueError("Unexpected candidate source destination")
    for path,content in edits.items(): path.write_text(content,encoding="utf-8")
    for origin,target in sources: target.write_bytes(origin.read_bytes())
    print("Prepared original-preset, debug-text guard, native-audio fail-fast, touch overlay and Android Activity candidate.")
