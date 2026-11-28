#!/usr/bin/env python3
"""Static rendering code-path census, NOT counts of unique textures."""
import argparse,pathlib,re,json,subprocess
PIN="dd8fb6d9ea34decedc4e57d4c5deebc008b8adbd"
PATTERNS={
 "indexed_sprite":r"\bIndexedSpriteTexture2D\b",
 "indexed_tiles":r"\bIndexedTiledTexture2D\b",
 "tile_map":r"\b(?:TileMapScreenRenderer|GfxTileKitManager|AnimatedTilekitManager)\b",
 "direct_content":r"\.Load\s*<\s*Texture2D\s*>",
 "direct_texture":r"\bnew\s+Texture2D\s*\(",
 "texture_loader":r"\bTexture2D\.From(?:Stream|File)\s*\(",
 "custom_replacement":r"\bReplaceSpriteTexture\s*\(",
 "palette":r"\b(?:PaletteTexture2D|PaletteCycleAnimation)\b",
 "mesh_or_mode7":r"\b(?:BeginMeshRender|Mode7ScreenRenderer|WorldViewProj)\b",
 "screen_renderer":r"\b(?:TextureScreenRenderer|MultiScreenRenderer|MultiSelectableScreenRenderer)\b"
}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--checkout",type=pathlib.Path,required=True);p.add_argument("--out",type=pathlib.Path,required=True)
 a=p.parse_args();root=a.checkout.resolve()
 if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:raise SystemExit("Wrong source pin")
 groups={k:[] for k in PATTERNS}
 for f in sorted((root/"src").rglob("*.cs")):
  if {"bin","obj"}&set(f.parts):continue
  for i,l in enumerate(f.read_text(encoding="utf-8-sig").splitlines(),1):
   for k,pat in PATTERNS.items():
    if re.search(pat,l):groups[k].append({"path":f.relative_to(root).as_posix(),"line":i})
 out={"upstream":PIN,"meaning":"static code-path candidates, not complete runtime inventory","groups":{k:{"hits":len(v),"files":len(set(x["path"] for x in v)),"locations":v} for k,v in groups.items()}}
 with a.out.open("x",encoding="utf-8") as f:json.dump(out,f,indent=2)
 print(json.dumps({k:{"hits":len(v),"files":len(set(x["path"] for x in v))} for k,v in groups.items()},indent=2))
if __name__=="__main__":main()
