#!/usr/bin/env python3
"""Compile/test the actual new C# components against the pinned upstream GbaInput enum."""
import argparse, pathlib, subprocess, tempfile, shutil
from xml.sax.saxutils import escape
from apply_port_input import PIN, git
p=argparse.ArgumentParser();p.add_argument('--checkout',type=pathlib.Path,required=True);a=p.parse_args()
repo=a.checkout.resolve()
if git(repo,'rev-parse','HEAD')!=PIN: raise SystemExit('Wrong upstream commit')
status=git(repo,'submodule','status','--recursive').splitlines()
if not status or any(s.startswith(('-', '+', 'U')) for s in status): raise SystemExit('Submodules not initialized/pinned')
source=repo/'sub-modules/BinarySerializer.Ubisoft.GbaEngine/src/DataTypes/GbaCommon/GbaSdk/Driver/GbaInput.cs'
if not source.is_file(): raise SystemExit('Expected upstream enum missing; inspect pin before changing this script')
base=pathlib.Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='rayman-checks-') as td:
    root=pathlib.Path(td)
    for name in ('TouchInputBridge.cs','AndroidTouchLayout.cs','PrivateRomStore.cs','Stage02Checks.cs'): shutil.copyfile(base/name,root/name)
    shutil.copyfile(source,root/'GbaInput.cs')
    (root/'Checks.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>')
    subprocess.run(['dotnet','run','--project',str(root/'Checks.csproj'),'-c','Release'],check=True)
