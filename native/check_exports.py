#!/usr/bin/env python3
"""Compare Android ELF exports against every managed import; no fabricated aliases."""
import argparse, pathlib, re, subprocess, json, struct, hashlib
PIN="e82fd32c1f62183922f08c14c814a02b58db1873"
READVANCED="dd8fb6d9ea34decedc4e57d4c5deebc008b8adbd"
KNOWN_HEADER_GAPS={"Soloud_setPanAbsoluteEx","TedSid_loadToMem","TedSid_loadFileToMem"}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("library","wrapper","nm","readelf","report"): p.add_argument("--"+name,type=pathlib.Path,required=True)
    p.add_argument('--source-root',type=pathlib.Path,required=True)
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
    # Explicit conservative scan of the pinned managed sources, excluding only the wrapper.
    # These are the known absent API families; no approximate native aliases are invented.
    forbidden=re.compile(r"\b(?:TedSid|setPanAbsolute|Soloud_setPanAbsoluteEx|TedSid_loadFileToMem|TedSid_loadToMem)\b")
    references=[]
    for path in sorted(a.source_root.rglob("*.cs")):
        if path.resolve()==a.wrapper.resolve() or {"bin","obj"} & set(path.parts): continue
        for num,line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(),1):
            if forbidden.search(line):references.append(str(path.relative_to(a.source_root))+":"+str(num))
    with a.library.open("rb") as f: library_sha256=hashlib.file_digest(f,"sha256").hexdigest()
    platform_dependencies={"liblog.so","libandroid.so","libdl.so","libm.so","libc.so"}
    gate=not (missing-KNOWN_HEADER_GAPS) and not references and set(needed)<=platform_dependencies and bool(load_align) and min(load_align)>=16384
    data={"library_sha256":library_sha256,"known_missing_source_references":references,
          "gba_candidate_gate":gate,"soloud_pin":PIN,"readvanced_pin":READVANCED,"architecture":"AArch64",
          "managed_imports":len(symbols),"exported_imports":len(symbols&exports),
          "missing":sorted(missing),"unexpected_missing":sorted(missing-KNOWN_HEADER_GAPS),
          "load_alignment":load_align,"dynamic_dependencies":needed,
          "full_abi":not missing,"release_ready":False,
          "note":"Symbol presence is not ABI-signature or sound playback proof. Known missing exports remain unresolved, not faked."}
    a.report.write_text(json.dumps(data,indent=2)+"\n")
    print(json.dumps(data,indent=2))
    if not load_align or min(load_align)<16384: raise SystemExit("ELF 16 KiB page compatibility not established")
    if not gate: raise SystemExit("Android GBA candidate gate failed; see ABI report")
    if missing: print("Candidate compiled; full ABI remains blocked by listed known gaps.")
if __name__=="__main__": main()
