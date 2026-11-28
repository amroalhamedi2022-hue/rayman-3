#if ANDROID
using System;
using System.IO;
using System.Text.Json;

namespace GbaMonoGame.Rayman3;

// Explicit opt-in, no network and no gameplay writes.
// FrameManager invokes this after Frame.Step and before GameTime.Update.
internal sealed class FaithfulTraceRecorder : IDisposable
{
    private const int Limit = 3600;
    private StreamWriter writer;
    private int tick;
    private bool disposed;
    private FaithfulTraceRecorder(StreamWriter output)
    {
        writer = output;
        Engine.FrameMngr.AddStepAction(Capture);
    }
    internal static FaithfulTraceRecorder TryStart()
    {
        if (!File.Exists(Engine.UserData.GetFile("faithful-trace.enabled"))) return null;
        try
        {
            string dir = Engine.UserData.GetDirectory("Trace");
            Directory.CreateDirectory(dir);
            string path = Path.Combine(dir, "trace-" + Guid.NewGuid().ToString("N") + ".jsonl");
            return new FaithfulTraceRecorder(new StreamWriter(
                new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.Read)));
        }
        catch (Exception ex)
        {
            Android.Util.Log.Warn("RaymanTrace", ex.Message);
            return null;
        }
    }
    private void Capture()
    {
        if (writer == null) return;
        try
        {
            if (Frame.Current is not FrameSideScroller frame || frame.Scene == null ||
                frame.Scene.MainActor is not Rayman player) return;
            var a = player.AnimatedObject;
            var pos = player.Position;
            var speed = player.Speed;
            var camera = frame.Scene.Playfield.Camera.Position;
            writer.WriteLine(JsonSerializer.Serialize(new
            {
                schema = 1, tick, game_frame = GameTime.ElapsedFrames,
                map_id = (int)Rayman3.GameInfo.MapId,
                input_mask = (ushort)Engine.JoyPad.Current.KeyStatus,
                action_id = (int)player.ActionId, animation_id = a.CurrentAnimation,
                animation_frame = a.CurrentFrame, animation_timer = a.Timer,
                x = pos.X, y = pos.Y, vx = speed.X, vy = speed.Y,
                camera_x = camera.X, camera_y = camera.Y,
                hit_points = player.HitPoints, flip_x = a.FlipX, flip_y = a.FlipY,
                paused = GameTime.IsPaused
            }));
            tick++;
            if (tick % 120 == 0) writer.Flush();
            if (tick >= Limit) { writer.Dispose(); writer = null; }
        }
        catch (Exception ex)
        {
            Android.Util.Log.Warn("RaymanTrace", ex.Message);
            writer?.Dispose();
            writer = null;
        }
    }
    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        Engine.FrameMngr?.RemoveStepAction(Capture);
        writer?.Dispose();
        writer = null;
    }
}
#endif
