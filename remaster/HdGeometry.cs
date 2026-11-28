using System;
namespace GbaMonoGame;
public static class HdGeometry
{
    public static bool Valid(int w,int h,int tw,int th) =>
        w>0 && h>0 && tw>0 && th>0 && tw<=2048 && th<=2048 &&
        (long)tw*h==(long)th*w && (long)tw>=2L*w && (long)tw<=16L*w;
    public static (float Offset,float Origin,float Scale) Axis(float logical,float texture,bool center,float? affine)
    {
        if(logical<=0||texture<=0) throw new ArgumentOutOfRangeException();
        float span=center?logical/2f:logical;
        float factor=affine.HasValue?MathF.Round(span*affine.Value)/span:1f;
        return (center?logical/2f:0f,center?texture/2f:0f,factor*logical/texture);
    }
}
