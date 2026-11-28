using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Xna.Framework.Graphics;
using BinarySerializer.Ubisoft.GbaEngine;

namespace GbaMonoGame;
// Private rendering-only override; only exact, reviewed GBA sprite occurrences.
public sealed class HdSpritePack : IDisposable
{
    public readonly record struct Key(long Resource,long Palette,int Animation,int Frame,int Channel,
        int Tile,int Shape,int Size,int PaletteIndex,bool EightBit)
    {
        public string Id=>FormattableString.Invariant($"sprite:{Resource}:{Palette}:{Animation}:{Frame}:{Channel}:{Tile}:{Shape}:{Size}:{PaletteIndex}:{(EightBit?8:4)}");
        public string SourceId=>FormattableString.Invariant($"sprite:{Resource}:{Palette}:{Tile}:{Shape}:{Size}:{PaletteIndex}:{(EightBit?8:4)}");
    }
    private sealed record Entry(int W,int H,int TW,int TH,string Png,string Source);
    private sealed record Source(string File,string Sha);
    private readonly GraphicsDevice device;
    private readonly Dictionary<string,Entry> entries=new(StringComparer.Ordinal);
    private readonly Dictionary<string,Texture2D> loaded=new(StringComparer.Ordinal);
    private readonly HashSet<string> rejected=new(StringComparer.Ordinal);
    private readonly HashSet<string> seen=new(StringComparer.Ordinal);
    private readonly Dictionary<string,Source> sources=new(StringComparer.Ordinal);
    private bool initialized;
    private string root,romSha,auditRoot;
    private StreamWriter audit;
    private long resident,exported;
    private const long ResidentLimit=96L*1024*1024,ExportLimit=128L*1024*1024;
    private const int RecordLimit=100000;
    public HdSpritePack(GraphicsDevice graphics){device=graphics;}
    private static string Sha(byte[] data)=>Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
    private static string Digest(string path){using var f=File.OpenRead(path);return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();}
    private static bool Hex(string v)
    {
        if(v==null||v.Length!=64)return false;
        foreach(char c in v)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;
        return true;
    }
    private void Initialize()
    {
        if(initialized||!Rom.IsLoaded||Rom.Platform!=Platform.GBA)return;
        initialized=true;
        try
        {
            root=Engine.UserData.GetDirectory("Remaster");
            string manifest=Path.Combine(root,"manifest.json");
            bool capture=File.Exists(Path.Combine(root,"capture.enabled"));
            if(!capture&&!File.Exists(manifest))return;
            if(Rom.GameFileNames.Length!=1)throw new InvalidDataException("Expected one GBA source");
            romSha=Digest(Path.Combine(Rom.GameDirectory,Rom.GameFileNames[0]));
            if(capture)
            {
                auditRoot=Path.Combine(root,"capture-"+Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(Path.Combine(auditRoot,"sources"));
                audit=new StreamWriter(new FileStream(Path.Combine(auditRoot,"observed.jsonl"),FileMode.CreateNew)){AutoFlush=true};
            }
            if(!File.Exists(manifest))return;
            if(new FileInfo(manifest).Length>32*1024*1024)throw new InvalidDataException("Manifest exceeds limit");
            using var doc=JsonDocument.Parse(File.ReadAllBytes(manifest));
            var m=doc.RootElement;
            if(m.GetProperty("schema").GetInt32()!=1||m.GetProperty("rom_sha256").GetString()!=romSha)
                throw new InvalidDataException("Wrong ROM identity");
            foreach(var e in m.GetProperty("entries").EnumerateArray())
            {
                string id=e.GetProperty("key").GetString();
                int w=e.GetProperty("logical_width").GetInt32(),h=e.GetProperty("logical_height").GetInt32();
                int tw=e.GetProperty("texture_width").GetInt32(),th=e.GetProperty("texture_height").GetInt32();
                string png=e.GetProperty("png_sha256").GetString(),source=e.GetProperty("source_sha256").GetString(),review=e.GetProperty("review_sha256").GetString();
                if(id==null||!id.StartsWith("sprite:",StringComparison.Ordinal)||id.Length>180||
                   !HdGeometry.Valid(w,h,tw,th)||!Hex(png)||!Hex(source)||!Hex(review)||
                   !e.GetProperty("approved").GetBoolean()||entries.Count>=RecordLimit||
                   !entries.TryAdd(id,new Entry(w,h,tw,th,png,source)))
                    throw new InvalidDataException("Invalid or duplicate reviewed entry");
            }
        }
        catch(Exception ex){entries.Clear();System.Diagnostics.Debug.WriteLine("HD manifest rejected: "+ex.Message);}
    }
    public bool Active { get {Initialize();return audit!=null||entries.Count!=0;} }
    private static byte[] Decode(Key key,int w,int h,byte[] tiles,Palette[] palettes)
    {
        var colors=palettes[key.PaletteIndex].Colors;
        int expected=key.EightBit?256:16;
        if(colors.Length!=expected)throw new InvalidDataException("Unresolved palette layout");
        byte[] rgba=new byte[expected*4];
        for(int i=0;i<colors.Length;i++)
        {
            rgba[i*4]=colors[i].R;rgba[i*4+1]=colors[i].G;rgba[i*4+2]=colors[i].B;rgba[i*4+3]=colors[i].A;
        }
        return HdSpriteDecode.Decode(tiles,key.Tile,w,h,key.EightBit,rgba);
    }
    private void Observe(Key key,string id,int w,int h,bool eligible,byte[] tiles,Palette[] palettes)
    {
        if(audit==null||seen.Count>=RecordLimit||!seen.Add(id))return;
        Source source=null;
        string reason=eligible?"eligible":"unsupported_palette_cycle_custom_or_3d";
        if(eligible)
        {
            try
            {
                if(!sources.TryGetValue(key.SourceId,out source))
                {
                    byte[] rgba=Decode(key,w,h,tiles,palettes);
                    if(exported+rgba.Length>ExportLimit)throw new IOException("Source capture quota");
                    string name="sources/"+Sha(Encoding.UTF8.GetBytes(key.SourceId))+".rgba";
                    using(var f=new FileStream(Path.Combine(auditRoot,name),FileMode.CreateNew))f.Write(rgba);
                    source=new Source(name,Sha(rgba));sources.Add(key.SourceId,source);exported+=rgba.Length;
                }
            }
            catch(Exception ex){reason="unresolved_source: "+ex.GetType().Name;}
        }
        try
        {
            audit.WriteLine(JsonSerializer.Serialize(new {schema=1,rom_sha256=romSha,key=id,source_key=key.SourceId,
                logical_width=w,logical_height=h,eligible=eligible&&source!=null,reason,source_file=source?.File,source_sha256=source?.Sha}));
        }
        catch(Exception ex){System.Diagnostics.Debug.WriteLine(ex.Message);audit.Dispose();audit=null;}
    }
    public Texture2D Resolve(Key key,int w,int h,bool eligible,byte[] tiles,Palette[] palettes)
    {
        if(!Active)return null;
        string id=key.Id;
        Observe(key,id,w,h,eligible,tiles,palettes);
        if(!eligible||!entries.TryGetValue(id,out Entry e)||e.W!=w||e.H!=h||rejected.Contains(id))return null;
        if(loaded.TryGetValue(id,out Texture2D previous))return previous;
        Texture2D texture=null;
        try
        {
            if(Sha(Decode(key,w,h,tiles,palettes))!=e.Source)throw new InvalidDataException("Source pixels differ from reviewed binding");
            long bytes=4L*e.TW*e.TH;
            if(resident+bytes>ResidentLimit)throw new InvalidDataException("HD texture budget exceeded");
            string path=Path.Combine(root,"textures",e.Png+".png");
            var info=new FileInfo(path);
            if(!info.Exists||info.Length<33||info.Length>16*1024*1024)throw new InvalidDataException("Invalid PNG size");
            byte[] data=File.ReadAllBytes(path);
            if(Sha(data)!=e.Png||!data.AsSpan(0,8).SequenceEqual(new byte[]{137,80,78,71,13,10,26,10})||
               BinaryPrimitives.ReadUInt32BigEndian(data.AsSpan(8,4))!=13||
               !data.AsSpan(12,4).SequenceEqual("IHDR"u8)||
               BinaryPrimitives.ReadInt32BigEndian(data.AsSpan(16,4))!=e.TW||
               BinaryPrimitives.ReadInt32BigEndian(data.AsSpan(20,4))!=e.TH||data[24]!=8||data[25]!=6)
                throw new InvalidDataException("Invalid reviewed RGBA PNG");
            using var stream=new MemoryStream(data,false);
            texture=Texture2D.FromStream(device,stream);
            if(texture.Width!=e.TW||texture.Height!=e.TH)throw new InvalidDataException("Decoded dimensions differ");
            loaded.Add(id,texture);resident+=bytes;return texture;
        }
        catch(Exception ex){texture?.Dispose();rejected.Add(id);System.Diagnostics.Debug.WriteLine("HD fallback: "+ex.Message);return null;}
    }
    public void ClearFrame()
    {
        foreach(var t in loaded.Values)t.Dispose();
        loaded.Clear();rejected.Clear();resident=0;
    }
    public void ResetRom()
    {
        ClearFrame();entries.Clear();seen.Clear();sources.Clear();audit?.Dispose();audit=null;
        initialized=false;root=null;romSha=null;auditRoot=null;exported=0;
    }
    public void Dispose()=>ResetRom();
}
