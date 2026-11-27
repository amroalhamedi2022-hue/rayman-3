// Android input adapter. Original game logic remains in SimpleJoyPad/BufferedJoyPad.
using System;
using System.Collections.Generic;
using BinarySerializer.Ubisoft.GbaEngine;

namespace GbaMonoGame;

public static class TouchInputBridge
{
    private static readonly object Gate = new();
    private static readonly Dictionary<int, GbaInput> Contacts = new();
    private const GbaInput Buttons = GbaInput.A | GbaInput.B | GbaInput.Select |
        GbaInput.Start | GbaInput.Right | GbaInput.Left | GbaInput.Up | GbaInput.Down |
        GbaInput.R | GbaInput.L;

    // One pointer can hold a diagonal or a combination. Distinct pointers are independent.
    // Android UI calls this on pointer down/move, Remove on pointer up, Clear on cancel/pause.
    public static void Set(int pointerId, GbaInput buttons)
    {
        if (pointerId < 0) throw new ArgumentOutOfRangeException(nameof(pointerId));
        if ((buttons & ~Buttons) != 0) throw new ArgumentException("Unsupported input bits", nameof(buttons));
        lock (Gate)
        {
            if (buttons == GbaInput.None) Contacts.Remove(pointerId);
            else Contacts[pointerId] = buttons;
        }
    }
    public static void Remove(int pointerId) { lock (Gate) Contacts.Remove(pointerId); }
    public static void Clear() { lock (Gate) Contacts.Clear(); }
    public static GbaInput Snapshot()
    {
        lock (Gate)
        {
            GbaInput pressed = GbaInput.None;
            foreach (var value in Contacts.Values) pressed |= value;
            return pressed;
        }
    }
}
