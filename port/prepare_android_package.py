#!/usr/bin/env python3
"""Create the private Android app shell from the already adapted game library.
Requires a real ARM64 SoLoud and staged, verified Android content.
Never fetches or packages a ROM and never uploads a package.
"""
import argparse,hashlib,json,pathlib,shutil,struct
from apply_port_input import PIN,git

PROJECT="""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>net10.0-android</TargetFrameworks>
    <PlatformTarget>AnyCPU</PlatformTarget>
    <OutputType>Exe</OutputType>
    <SupportedOSPlatformVersion>23</SupportedOSPlatformVersion>
    <ApplicationId>org.readvanced.rayman3.androidtest</ApplicationId>
    <ApplicationTitle>Rayman 3 (Private Test)</ApplicationTitle>
    <ApplicationVersion>1</ApplicationVersion>
    <ApplicationDisplayVersion>0.1.0</ApplicationDisplayVersion>
    <RuntimeIdentifiers>android-arm64</RuntimeIdentifiers>
    <AndroidPackageFormats>apk</AndroidPackageFormats>
    <AndroidManifest>Properties/AndroidManifest.xml</AndroidManifest>
    <PublishTrimmed>false</PublishTrimmed>
    <AndroidKeyStore>false</AndroidKeyStore>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="MonoGame.Framework.Android" />
    <ProjectReference Include="../GbaMonoGame.Rayman3/GbaMonoGame.Rayman3.csproj" />
    <AndroidAsset Remove="Assets/**/*" />
    <AndroidAsset Include="Assets/**/*" />
    <AndroidNativeLibrary Include="Native/arm64-v8a/libsoloud.so" Abi="arm64-v8a" />
  </ItemGroup>
</Project>
"""
MANIFEST="""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-feature android:glEsVersion="0x00020000" android:required="true" />
  <application android:allowBackup="false" android:usesCleartextTraffic="false" />
</manifest>
"""
ALLOWED={".xnb",".wav",".sf2",".jsonc",".json",".manifest"}
def digest(path):
    with path.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()

def validate_inputs(assets,library,report):
    info=json.loads(report.read_text(encoding="utf-8"))
    if info.get("readvanced_pin")!=PIN or info.get("architecture")!="AArch64":
        raise ValueError("Wrong native provenance")
    if info.get("unexpected_missing")!=[] or info.get("managed_imports")!=423:
        raise ValueError("Unexpected ABI mismatch")
    if info.get("library_sha256")!=digest(library):
        raise ValueError("Native candidate hash does not match ABI report")
    if not info.get("load_alignment") or min(info["load_alignment"])<16384:
        raise ValueError("Native alignment missing")
    header=library.read_bytes()[:64]
    if header[:6]!=b"\x7fELF\x02\x01" or struct.unpack_from("<H",header,18)[0]!=183:
        raise ValueError("Not Android ARM64 ELF")
    manifest=assets/"Assets/raw-assets.manifest"
    if not manifest.is_file():raise ValueError("No staged raw content manifest")
    files={}
    for p in assets.rglob("*"):
        if p.is_symlink(): raise ValueError("Symlink in asset staging")
        if not p.is_file(): continue
        rel=p.relative_to(assets).as_posix()
        if not rel.startswith("Assets/") or p.suffix.lower() not in ALLOWED:
            raise ValueError("Disallowed asset: "+rel)
        files[rel]=digest(p)
    expected={}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        sha,sep,rel=line.partition("  ")
        if sep!="  " or rel in expected or len(sha)!=64 or rel not in files or files[rel]!=sha:
            raise ValueError("Invalid raw asset manifest")
        if pathlib.PurePosixPath(rel).suffix.lower() not in {".wav",".sf2",".jsonc",".json"}:
            raise ValueError("Unexpected manifest entry")
        expected[rel]=sha
    raw={k:v for k,v in files.items() if pathlib.PurePosixPath(k).suffix.lower() in {".wav",".sf2",".jsonc",".json"}}
    if raw!=expected or not raw:raise ValueError("Raw content inventory mismatch")
    for name in ("DefaultShader","PaletteShader","PaletteVertexShader","VertexShader"):
        if "Assets/GbaMonoGame/Gfx/"+name+".xnb" not in files:raise ValueError("Missing original renderer effect")
    return {"files":files,"native_sha256":digest(library),"native_full_abi":info.get("full_abi",False)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("checkout","assets","native-library","abi-report","inventory"):
        p.add_argument("--"+n,type=pathlib.Path,required=True)
    a=p.parse_args()
    repo=a.checkout.resolve()
    if git(repo,"rev-parse","HEAD")!=PIN:raise SystemExit("Wrong upstream revision")
    inv=validate_inputs(a.assets,a.native_library,a.abi_report)
    src=repo/"src"
    app=src/"GbaMonoGame.Rayman3.Android"
    host=src/"GbaMonoGame.Rayman3/AndroidGameHost.cs"
    if app.exists() or not host.is_file():raise SystemExit("Expected freshly adapted checkout")
    app.mkdir()
    (app/"Properties").mkdir()
    (app/"Native/arm64-v8a").mkdir(parents=True)
    (app/"GbaMonoGame.Rayman3.Android.csproj").write_text(PROJECT,encoding="utf-8")
    (app/"Properties/AndroidManifest.xml").write_text(MANIFEST,encoding="utf-8")
    # Move the public Activity to the executable project, not a duplicate Activity.
    shutil.move(host,app/"AndroidGameHost.cs")
    shutil.copytree(a.assets,app/"Assets")
    shutil.copyfile(a.native_library,app/"Native/arm64-v8a/libsoloud.so")
    a.inventory.write_text(json.dumps(inv,indent=2)+"\n",encoding="utf-8")
    print("Prepared app project with",len(inv["files"]),"verified assets; no ROM. Full audio ABI:",inv["native_full_abi"])
if __name__=="__main__":main()
