#!/usr/bin/env python3
"""Compare Android ELF exports against every managed import; no fabricated aliases."""
import argparse, pathlib, re, subprocess, json, struct
PIN="e82fd32c1f62183922f08c14c814a02b58db1873"
READVANCED="dd8fb6d9ea34decedc4e57d4c5deebc008b8adbd"
KNOWN_HEADER_GAPS={"Soloud_setPanAbsoluteEx","TedSid_loadToMem","TedSid_loadFileToMem"}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("library","wrapper","nm","readelf","report"): p.add_argument("--"+name,type=pathlib.Path,required=True)
    a=p.parse_args()
    h=a.library.read_bytes()[:64]
    if h[:6]!=b"\x7fELF\x02\x01" or struct.unpack_from("<H",h,18)[0]!=183: raise SystemExit("Expected AArch64 64-bit little-endian ELF")
    symbols=set(re.findall(r'internal static extern\s+\S+\s+(\w+)\s*\(',a.wrapper.read_text(encoding="utf-8-sig")))
    if len(symbols)!=423: raise SystemExit(f"Unexpected managed symbol set: {len(symbols)}")
    nm=subprocess.check_output([str(a.nm),"--dynamic","--defined-only",str(a.library)],text=True)
    exports={line.split()[-1] for line in nm.splitlines() if line.split()}
    missing=symbols-exports
    elf=subprocess.check_output([str(a.readelf),"-lW","-dW",str(a.library)],text=True)
    load_align=[int(line.split()[-1],16) for line in elf.splitlines() if line.strip().startswith("LOAD ")]
    needed=re.findall(r'Shared library: \[([^\]]+)\]',elf)
    data={"soloud_pin":PIN,"readvanced_pin":READVANCED,"architecture":"AArch64",
          "managed_imports":len(symbols),"exported_imports":len(symbols&exports),
          "missing":sorted(missing),"unexpected_missing":sorted(missing-KNOWN_HEADER_GAPS),
          "load_alignment":load_align,"dynamic_dependencies":needed,
          "full_abi":not missing,"release_ready":False,
          "note":"Symbol presence is not ABI-signature or sound playback proof. Known missing exports remain unresolved, not faked."}
    a.report.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data,indent=2))
    if not load_align or min(load_align)<16384: raise SystemExit("ELF 16 KiB page compatibility not established")
    if missing-KNOWN_HEADER_GAPS: raise SystemExit("Unexpected missing native exports")
    if missing: print("Candidate compiled; full ABI remains blocked by listed known gaps.")
if __name__=="__main__": main()
