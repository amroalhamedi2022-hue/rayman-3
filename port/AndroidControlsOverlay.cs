#if ANDROID
using System;
using Microsoft.Xna.Framework.Graphics;
using BinarySerializer.Ubisoft.GbaEngine;
using XColor = Microsoft.Xna.Framework.Color;
using XRect = Microsoft.Xna.Framework.Rectangle;
using XViewport = Microsoft.Xna.Framework.Graphics.Viewport;

namespace GbaMonoGame;

// Prototype overlay; geometry matches AndroidTouchLayout.Hit. No physics/render-scale changes.
internal sealed class AndroidControlsOverlay : IDisposable
{
    readonly GraphicsDevice device;
    readonly SpriteBatch batch;
    readonly Texture2D pixel;
    readonly (GbaInput Key, float X1,float Y1,float X2,float Y2,string Label)[] zones =
    {
        (GbaInput.L,0,0,.22f,.16f,"L"),
        (GbaInput.R,.78f,0,1,.16f,"R"),
        (GbaInput.Select,.40f,.88f,.49f,1,"SEL"),
        (GbaInput.Start,.51f,.88f,.60f,1,"START"),
        (GbaInput.B,.68f,.57f,.84f,.90f,"B"),
        (GbaInput.A,.84f,.57f,1,.90f,"A"),
        (GbaInput.Up,.1116f,.50f,.1984f,.6584f,""),
        (GbaInput.Down,.1116f,.7816f,.1984f,.94f,""),
        (GbaInput.Left,0,.6584f,.1116f,.7816f,""),
        (GbaInput.Right,.1984f,.6584f,.31f,.7816f,""),
        (GbaInput.Left|GbaInput.Up,0,.50f,.1116f,.6584f,""),
        (GbaInput.Right|GbaInput.Up,.1984f,.50f,.31f,.6584f,""),
        (GbaInput.Left|GbaInput.Down,0,.7816f,.1116f,.94f,""),
        (GbaInput.Right|GbaInput.Down,.1984f,.7816f,.31f,.94f,"")
    };
    // A minimal original glyph set so no font or external artwork is required.
    static readonly System.Collections.Generic.Dictionary<char,string[]> Glyphs=new()
    {
        ['A']=new[]{"01110","10001","11111","10001","10001"},
        ['B']=new[]{"11110","10001","11110","10001","11110"},
        ['L']=new[]{"10000","10000","10000","10000","11111"},
        ['R']=new[]{"11110","10001","11110","10100","10010"},
        ['S']=new[]{"01111","10000","01110","00001","11110"},
        ['E']=new[]{"11111","10000","11110","10000","11111"},
        ['T']=new[]{"11111","00100","00100","00100","00100"}
    };
    internal AndroidControlsOverlay(GraphicsDevice graphics)
    {
        device=graphics;
        batch=new SpriteBatch(graphics);
        pixel=new Texture2D(graphics,1,1);
        pixel.SetData(new[]{XColor.White});
    }
    internal void Draw()
    {
        var pp=device.PresentationParameters;
        int w=pp.BackBufferWidth,h=pp.BackBufferHeight;
        if(w<=0||h<=0)return;
        var viewport=device.Viewport;
        var scissor=device.ScissorRectangle;
        try
        {
            device.Viewport=new XViewport(0,0,w,h);
            device.ScissorRectangle=new XRect(0,0,w,h);
            batch.Begin(SpriteSortMode.Deferred,BlendState.AlphaBlend,SamplerState.PointClamp,DepthStencilState.None,RasterizerState.CullNone);
            var held=TouchInputBridge.Snapshot();
            foreach(var z in zones)
            {
                int x=(int)(z.X1*w),y=(int)(z.Y1*h);
                int x2=(int)(z.X2*w),y2=(int)(z.Y2*h);
                var r=new XRect(x+2,y+2,Math.Max(1,x2-x-4),Math.Max(1,y2-y-4));
                bool pressed=(held&z.Key)==z.Key;
                batch.Draw(pixel,r,pressed ? new XColor(231,184,71)*.60f : XColor.Black*.25f);
                batch.Draw(pixel,new XRect(r.X,r.Y,r.Width,2),XColor.White*.32f);
                batch.Draw(pixel,new XRect(r.X,r.Bottom-2,r.Width,2),XColor.White*.32f);
                batch.Draw(pixel,new XRect(r.X,r.Y,2,r.Height),XColor.White*.32f);
                batch.Draw(pixel,new XRect(r.Right-2,r.Y,2,r.Height),XColor.White*.32f);
                DrawLabel(z.Label,r);
            }
            batch.End();
        }
        finally
        {
            device.Viewport=viewport;
            device.ScissorRectangle=scissor;
        }
    }
    void DrawLabel(string label,XRect rect)
    {
        if(label.Length==0)return;
        int unit=Math.Max(1,Math.Min(rect.Width/(label.Length*6+2),rect.Height/8));
        int left=rect.Center.X-(label.Length*6-1)*unit/2,top=rect.Center.Y-5*unit/2;
        for(int i=0;i<label.Length;i++)
        {
            if(!Glyphs.TryGetValue(label[i],out var glyph))continue;
            for(int y=0;y<5;y++)for(int x=0;x<5;x++)
                if(glyph[y][x]=='1')batch.Draw(pixel,new XRect(left+(i*6+x)*unit,top+y*unit,unit,unit),XColor.White*.85f);
        }
    }
    public void Dispose(){pixel.Dispose();batch.Dispose();}
}
#endif
