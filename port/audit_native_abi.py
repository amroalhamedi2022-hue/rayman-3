#!/usr/bin/env python3
"""Inventory native interop dependencies without copying or publishing game assets."""
import argparse, pathlib, re, json, struct
from apply_port_input import PIN, git

def elf_info(p):
    with p.open("rb") as f: h=f.read(64)
    if h[:4] != b"\x7fELF" or len(h)<20: return None
    order = "<" if h[5]==1 else ">" if h[5]==2 else None
    if order is None: return None
    return {"elf_class": h[4], "machine": struct.unpack_from(order+"H", h,18)[0]}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout",type=pathlib.Path,required=True)
    a=parser.parse_args()
    repo=a.checkout.resolve()
    if git(repo,"rev-parse","HEAD") != PIN: raise SystemExit("Wrong upstream pin")
    native=repo/"src/GbaMonoGame.Native"
    libraries=[]
    for p in sorted((native/"runtimes").rglob("*")):
        if p.is_file() and (p.suffix.lower() in (".dll",".so",".dylib") or ".so." in p.name):
            libraries.append({"path":p.relative_to(native).as_posix(),"elf":elf_info(p)})
    imports={}
    for p in sorted(native.rglob("*.cs")):
        if "obj" in p.parts or "bin" in p.parts: continue
        for lib in re.findall(r'DllImport\(\s*"([^"]+)"',p.read_text(encoding="utf-8-sig")):
            imports[lib]=imports.get(lib,0)+1
    android_arm64=[x["path"] for x in libraries if x["elf"] and x["elf"]["machine"]==183 and x["elf"]["elf_class"]==2 and "android" in x["path"].lower()]
    print(json.dumps({"upstream":PIN,"libraries":libraries,"managed_import_counts":imports,"android_arm64_candidates":android_arm64,
      "note":"Presence is not ABI proof. Native exports, dependencies and actual audio playback require a device test."},indent=2))
if __name__=="__main__": main()
