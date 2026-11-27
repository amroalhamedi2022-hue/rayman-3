#!/usr/bin/env python3
"""Stage Android XNB and raw content privately from real MGCB outputs.
No ROM, game saves, proprietary project art, or packaged binaries are uploaded by CI.
"""
import argparse, hashlib, pathlib, shutil, json
from apply_port_input import PIN, git
PROJECTS=("GbaMonoGame","GbaMonoGame.TgxEngine","GbaMonoGame.Rayman3")
RAW={".wav",".sf2",".jsonc",".json"}
def digest(path):
    with path.open("rb") as f: return hashlib.file_digest(f,"sha256").hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("checkout","content-root","output"):p.add_argument("--"+n,type=pathlib.Path,required=True)
    a=p.parse_args()
    if git(a.checkout,"rev-parse","HEAD")!=PIN:raise SystemExit("Wrong upstream pin")
    if a.output.exists():raise SystemExit("Use a fresh output directory")
    entries={}
    def add(source,relative,kind):
        key=("Assets/"+relative.as_posix())
        if key in entries:raise ValueError("Content collision: "+key)
        if source.is_symlink():raise ValueError("Symlink in content source")
        entries[key]=(source,kind,digest(source))
    for project in PROJECTS:
        built=a.content_root/("content-"+project)
        files=list(built.rglob("*.xnb"))
        if not files:raise ValueError("Missing compiled content: "+project)
        for f in files:add(f,f.relative_to(built),"xnb")
        raw=a.checkout/"src"/project/"Assets"
        for f in raw.rglob("*"):
            rel=f.relative_to(raw)
            if f.is_file() and f.suffix.lower() in RAW and not {"bin","obj"}&set(rel.parts):
                add(f,rel,"raw")
    for name in ("DefaultShader","PaletteShader","PaletteVertexShader","VertexShader"):
        if "Assets/GbaMonoGame/Gfx/"+name+".xnb" not in entries:raise ValueError("Missing renderer effect: "+name)
    a.output.mkdir()
    for key,(source,kind,sha) in sorted(entries.items()):
        target=a.output/key
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        if digest(target)!=sha:raise IOError("Content copy mismatch")
    raw_manifest=a.output/"Assets/raw-assets.manifest"
    raw_manifest.write_text("".join(sha+"  "+key+"\n" for key,(_,kind,sha) in sorted(entries.items()) if kind=="raw"),encoding="utf-8")
    report={"xnb":sum(k=="xnb" for _,k,_ in entries.values()),"raw":sum(k=="raw" for _,k,_ in entries.values()),"raw_manifest_sha256":digest(raw_manifest),"source":PIN}
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
