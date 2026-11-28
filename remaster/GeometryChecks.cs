using System;
using GbaMonoGame;
int count=0;
void Check(bool result,string name){if(!result)throw new Exception(name);count++;Console.WriteLine("PASS: "+name);}
void Throws(Action action,string name){try{action();}catch(ArgumentException){Check(true,name);return;}throw new Exception(name);}
Check(HdGeometry.Valid(16,16,128,128),"8x canvas");
Check(HdGeometry.Valid(32,16,256,128),"non-square uniform canvas");
Check(!HdGeometry.Valid(16,16,128,144),"reject distortion");
Check(!HdGeometry.Valid(16,16,4096,4096),"reject oversized");
Check(!HdGeometry.Valid(16,16,16,16),"reject native resolution");
foreach(bool center in new[]{false,true})
foreach(float? affine in new float?[]{null,.75f,1.37f,2.1f})
{
    var hd=HdGeometry.Axis(16,128,center,affine);
    var original=HdGeometry.Axis(16,16,center,affine);
    Check(hd.Offset==original.Offset&&Math.Abs(hd.Origin*hd.Scale-original.Origin*original.Scale)<.0001f&&
        Math.Abs(128*hd.Scale-16*original.Scale)<.0001f,"logical position and extent "+center+"/"+affine);
}
byte[] pal=new byte[64];pal[4]=10;pal[7]=255;pal[8]=20;pal[11]=255;
byte[] tiles=new byte[96];tiles[32]=0x21;tiles[64]=0x12;
var r=HdSpriteDecode.Decode(tiles,1,16,8,false,pal);
Check(r[0]==10&&r[4]==20&&r[11]==0&&r[8*4]==20&&r[9*4]==10,"4bpp nibble order and second tile");
Check(r[16*4+3]==0,"transparent color");
byte[] p8=new byte[1024];p8[200*4]=55;p8[200*4+3]=255;
byte[] t8=new byte[96];t8[32]=200;
var r8=HdSpriteDecode.Decode(t8,1,8,8,true,p8);
Check(r8[0]==55&&r8[3]==255&&r8[7]==0,"8bpp tile address uses 32-byte units");
Throws(()=>HdSpriteDecode.Decode(new byte[31],0,8,8,false,pal),"truncated source rejected");
Throws(()=>HdSpriteDecode.Decode(tiles,0,8,8,false,new byte[63]),"palette mismatch rejected");
Console.WriteLine("PASS: "+count+" geometry and decoder checks.");
