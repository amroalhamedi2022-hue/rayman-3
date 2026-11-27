#!/usr/bin/env python3
"""Prepare a disposable checkout for an Android compile-only feasibility probe.

Retarget the existing game and its engine libraries rather than reimplementing them.
This deliberately does not claim Android runtime readiness or create a release APK.
Content building is omitted only in the probe, not in eventual production.
"""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from apply_port_input import PIN, git, apply

PROJECTS = (
    "GbaMonoGame", "GbaMonoGame.AnimEngine", "GbaMonoGame.Engine2d",
    "GbaMonoGame.TgxEngine", "GbaMonoGame.Editor", "GbaMonoGame.Rayman3",
)
ANDROID = "MonoGame.Framework.Android"
DESKTOP = {"MonoGame.Framework.WindowsDX", "MonoGame.Framework.DesktopGL"}
TFM = "net10.0-android"

def save(root, path):
    ET.indent(root, space="  ")
    path.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")

def retarget_project(path):
    root = ET.parse(path).getroot()
    refs = [x for x in root.iter("PackageReference") if x.get("Include") in DESKTOP]
    if len(refs) != 2:
        raise ValueError(f"Unexpected MonoGame references: {path}")
    # Explicit overrides supersede inherited net10.0/x64 settings.
    props = ET.SubElement(root, "PropertyGroup")
    for name, value in (("TargetFrameworks", TFM), ("PlatformTarget", "AnyCPU"),
                        ("OutputType", "Library"), ("SupportedOSPlatformVersion", "23")):
        ET.SubElement(props, name).text = value
    for group in root.findall("ItemGroup"):
        for node in list(group):
            if node.tag == "PackageReference" and node.get("Include") in DESKTOP:
                group.remove(node)
            elif node.tag == "MonoGameContentReference":
                group.remove(node)
    ET.SubElement(ET.SubElement(root, "ItemGroup"), "PackageReference", Include=ANDROID)
    # The desktop entry point cannot run as an Android activity.
    if path.stem == "GbaMonoGame.Rayman3":
        for group in root.findall("PropertyGroup"):
            for node in list(group):
                if node.tag in ("ApplicationManifest", "ApplicationIcon"):
                    group.remove(node)
        ET.SubElement(ET.SubElement(root, "ItemGroup"), "Compile", Remove="Program.cs")
        for target in list(root.findall("Target")):
            if target.get("Name") == "RestoreDotnetTools":
                root.remove(target)
    save(root, path)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    repo = parser.parse_args().checkout.resolve()
    if git(repo, "rev-parse", "HEAD") != PIN or git(repo, "status", "--porcelain"):
        raise SystemExit("Expected clean pinned upstream checkout")
    src = repo / "src"
    packages = src / "Directory.Packages.props"
    paths = [src / name / (name + ".csproj") for name in PROJECTS]
    if not all(p.is_file() for p in [packages, *paths]):
        raise SystemExit("Expected upstream project layout missing")
    root = ET.parse(packages).getroot()
    if any(x.get("Include") == ANDROID for x in root.iter("PackageVersion")):
        raise SystemExit("Android version already exists")
    ET.SubElement(ET.SubElement(root, "ItemGroup"), "PackageVersion", Include=ANDROID, Version="3.8.4.1")
    # Existing input and ROM components are applied once to the disposable checkout.
    apply(repo)
    save(root, packages)
    for path in paths:
        retarget_project(path)
    print("Prepared existing Readvanced libraries for Android compiler diagnostics.")
    print("No content or runtime test has been performed.")

if __name__ == "__main__":
    main()
