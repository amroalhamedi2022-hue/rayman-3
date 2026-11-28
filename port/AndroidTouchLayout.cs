// Deterministic normalized control layout. UI must draw exactly these same zones.
using System;
using BinarySerializer.Ubisoft.GbaEngine;

namespace GbaMonoGame;
public static class AndroidTouchLayout
{
    // Coordinates normalized to the actual safe control surface, not the GBA viewport.
    // Rectangular button zones are a prototype; not a final visual design.
    public static GbaInput Hit(float x, float y)
    {
        if (!float.IsFinite(x) || !float.IsFinite(y) || x < 0 || x > 1 || y < 0 || y > 1)
            return GbaInput.None;
        if (y < .16f && x < .22f) return GbaInput.L;
        if (y < .16f && x > .78f) return GbaInput.R;
        if (y > .88f && x >= .40f && x < .49f) return GbaInput.Select;
        if (y > .88f && x >= .51f && x <= .60f) return GbaInput.Start;
        if (x >= .68f && y >= .57f && y <= .90f)
            return x < .84f ? GbaInput.B : GbaInput.A;
        if (x <= .31f && y >= .50f && y <= .94f)
        {
            float dx = (x - .155f) / .155f, dy = (y - .72f) / .22f;
            GbaInput result = GbaInput.None;
            if (dx < -.28f) result |= GbaInput.Left;
            if (dx > .28f) result |= GbaInput.Right;
            if (dy < -.28f) result |= GbaInput.Up;
            if (dy > .28f) result |= GbaInput.Down;
            return result;
        }
        return GbaInput.None;
    }
}
