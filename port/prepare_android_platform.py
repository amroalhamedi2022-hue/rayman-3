#!/usr/bin/env python3
"""Android-only platform compatibility, no changes to gameplay logic."""
from pathlib import Path

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Unexpected upstream platform adapter anchor: " + old[:80])
    return text.replace(old, new, 1)

def adapt(src: Path):
    engine = src / "GbaMonoGame"
    paths = {
        "storage": engine / "Disk/UserDataManager.cs",
        "dialog": engine / "Disk/FileDialogManager.cs",
        "presence": engine / "DiscordRichPresenceManager.cs",
    }
    original = {key: path.read_text(encoding="utf-8-sig") for key, path in paths.items()}
    storage = replace_once(original["storage"], "        return Paths.UserDataDirectoryName;", """#if ANDROID
        string root = Path.Combine(Android.App.Application.Context.FilesDir.AbsolutePath, Paths.UserDataDirectoryName);
        Directory.CreateDirectory(root);
        return root;
#else
        return Paths.UserDataDirectoryName;
#endif""")
    dialog = original["dialog"]
    # Desktop native file-dialog packages have no Android backend.
    # Fail explicitly rather than pretending an import/export succeeded.
    # Actual asynchronous Storage Access Framework integration is a separate gate.
    dialog = "#if ANDROID\nusing System;\n\nnamespace GbaMonoGame;\n\npublic class FileDialogManager\n{\n    public string OpenFile(string title, FileFilter filter) => throw new PlatformNotSupportedException(\"Android file selection must use the asynchronous Storage Access Framework.\");\n    public string OpenFolder(string title) => throw new PlatformNotSupportedException(\"Android folder selection must use the asynchronous Storage Access Framework.\");\n    public readonly struct FileFilter(string fileExtension, string description)\n    {\n        public string FileExtension { get; } = fileExtension;\n        public string Description { get; } = description;\n    }\n}\n#else\n" + dialog + "\n#endif\n"
    presence = "#if ANDROID\nnamespace GbaMonoGame;\n\n// Android stays offline; rich presence is optional, not game state.\npublic class DiscordRichPresenceManager : IRichPresenceManager\n{\n    public void SetIdlePresence() { }\n    public void SetPresence(string presence) { }\n    public void Dispose() { }\n}\n#else\n" + original["presence"] + "\n#endif\n"
    for key, content in (("storage", storage), ("dialog", dialog), ("presence", presence)):
        paths[key].write_text(content, encoding="utf-8")
    print("Android platform boundaries adapted: private storage, explicit SAF gate, offline rich presence.")
