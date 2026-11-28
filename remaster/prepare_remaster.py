#!/usr/bin/env python3
"""Install only visual hooks into the exact pinned upstream checkout."""
import argparse,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parent
PIN="dd8fb6d9ea34decedc4e57d4c5deebc008b8adbd"
def git(repo,*args):
    return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def once(s,a,b):
    if s.count(a)!=1:raise ValueError("Unexpected source anchor: "+a[:100])
    return s.replace(a,b,1)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--checkout",type=pathlib.Path,required=True)
    repo=p.parse_args().checkout.resolve()
    if git(repo,"rev-parse","HEAD")!=PIN:raise SystemExit("Wrong upstream commit")
    src=repo/"src";engine=src/"GbaMonoGame"
    a=src/"GbaMonoGame.AnimEngine/AnimatedObject.cs";s=engine/"Gfx/Sprite.cs";m=engine/"AssetManager.cs"
    for path,sha in ((a,"241a2d399d1845910164b0b99bf098bfb2c580c1"),(s,"1808b0670e51f3cba6d929943b3c5833b5088fae")):
        if git(repo,"hash-object",str(path))!=sha:raise ValueError("Unexpected original blob: "+str(path))
    edits={}
    t=a.read_text(encoding="utf-8-sig")
    t=once(t,"                    PaletteTexture? paletteTexture;", """                    bool hdApplied = false;
                    if (Resource.Offset != null && Palettes.CachePointer != null && Engine.Assets.Remaster.Active)
                    {
                        var hdKey = new HdSpritePack.Key(Resource.Offset.FileOffset, Palettes.CachePointer.FileOffset,
                            CurrentAnimation, CurrentFrame, i, channel.TileIndex, channel.SpriteShape, channel.SpriteSize,
                            paletteIndex, Resource.Is8Bit);
                        bool hdEligible = texture is IndexedSpriteTexture2D &&
                            anim.Idx_PaletteCycleAnimation == 0 && RenderOptions.Shader == null && RenderOptions.WorldViewProj == null;
                        Texture2D hd = Engine.Assets.Remaster.Resolve(hdKey, shape.Width, shape.Height,
                            hdEligible, Resource.SpriteTable.Data, Palettes.Palettes);
                        if (hd != null) { texture = hd; hdApplied = true; }
                    }
                    PaletteTexture? paletteTexture;""")
    t=once(t,"                    sprite.Texture = texture;","                    sprite.Texture = texture;\n                    if (hdApplied) sprite.HdLogicalSize = new Microsoft.Xna.Framework.Point(shape.Width, shape.Height);")
    edits[a]=t
    t=s.read_text(encoding="utf-8-sig")
    t=once(t,"    public Texture2D Texture { get; set; }","    public Texture2D Texture { get; set; }\n    public Point? HdLogicalSize { get; set; }")
    t=once(t,"        Texture = null;","        Texture = null;\n        HdLogicalSize = null;")
    t=once(t,"        renderer.Draw(\n            texture: Texture,", """        if (HdLogicalSize is Point logical)
        {
            var x = HdGeometry.Axis(logical.X, textureRectangle.Width, Center, AffineMatrix?.Scale.X);
            var y = HdGeometry.Axis(logical.Y, textureRectangle.Height, Center, AffineMatrix?.Scale.Y);
            renderer.Draw(texture: Texture, position: Position + new Vector2(x.Offset,y.Offset),
                sourceRectangle: textureRectangle, rotation: rotation,
                origin: new Vector2(x.Origin,y.Origin), scale: new Vector2(x.Scale,y.Scale),
                effects: effects, color: color);
            return;
        }

        renderer.Draw(
            texture: Texture,""")
    edits[s]=t
    t=m.read_text(encoding="utf-8-sig")
    t=once(t,"        BinaryPaletteCache = new BinaryCache<Palette>();","        BinaryPaletteCache = new BinaryCache<Palette>();\n        Remaster = new HdSpritePack(GraphicsDevice);")
    t=once(t,"    public BinaryCache<Texture2D> BinaryTextureCache { get; }","    public HdSpritePack Remaster { get; }\n    public BinaryCache<Texture2D> BinaryTextureCache { get; }")
    t=once(t,"    public void UnloadFrameCache()\n    {","    public void UnloadFrameCache()\n    {\n        Remaster.ClearFrame();")
    t=once(t,"    public void UnloadAllCache()\n    {","    public void UnloadAllCache()\n    {\n        Remaster.ResetRom();")
    t=once(t,"        GraphicsDevice.Dispose();","        Remaster.Dispose();\n        GraphicsDevice.Dispose();")
    edits[m]=t
    for name in ("HdGeometry.cs","HdSpriteDecode.cs","HdSpritePack.cs"):
        target=engine/"Gfx"/name
        if target.exists():raise FileExistsError(target)
        edits[target]=(ROOT/name).read_text(encoding="utf-8")
    for path,content in edits.items():path.write_text(content,encoding="utf-8")
    print("Installed HD sprite renderer, source extraction and reviewed manifest hooks.")
if __name__=="__main__":main()
