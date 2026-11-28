using System;
namespace GbaMonoGame;
// Unflipped, full-canvas GBA 1D tile order. No resampling. Index zero is transparent.
public static class HdSpriteDecode
{
    public static byte[] Decode(byte[] tiles,int tileIndex,int width,int height,bool eightBit,byte[] palette)
    {
        if(width<8||height<8||width>64||height>64||width%8!=0||height%8!=0||tileIndex<0)
            throw new ArgumentException("Invalid sprite geometry");
        if(palette.Length!=(eightBit?256:16)*4)throw new ArgumentException("Invalid palette");
        int size=eightBit?64:32;
        long begin=(long)tileIndex*32,count=(long)(width/8)*(height/8)*size;
        if(begin+count>tiles.Length)throw new ArgumentException("Truncated source tiles");
        byte[] rgba=new byte[width*height*4];
        int cursor=(int)begin;
        for(int ty=0;ty<height;ty+=8)for(int tx=0;tx<width;tx+=8)
        {
            for(int y=0;y<8;y++)for(int x=0;x<8;x++)
            {
                int offset=y*8+x;
                int value=eightBit?tiles[cursor+offset]:(tiles[cursor+offset/2]>>((offset&1)*4))&15;
                if(value!=0)Buffer.BlockCopy(palette,value*4,rgba,((ty+y)*width+tx+x)*4,4);
            }
            cursor+=size;
        }
        return rgba;
    }
}
