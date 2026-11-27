using System;
using System.IO;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using BinarySerializer.Ubisoft.GbaEngine;
using GbaMonoGame;

static void Require(bool ok, string name) { if (!ok) throw new Exception("FAIL: " + name); Console.WriteLine("PASS: " + name); }
static async Task Throws<T>(Func<Task> action) where T : Exception
{
    try { await action(); } catch (T) { Console.WriteLine("PASS: expected " + typeof(T).Name); return; }
    throw new Exception("Expected " + typeof(T).Name);
}
TouchInputBridge.Clear();
Require(TouchInputBridge.Snapshot() == GbaInput.None, "initial neutral");
TouchInputBridge.Set(1, GbaInput.Right | GbaInput.Up);
TouchInputBridge.Set(2, GbaInput.A);
Require(TouchInputBridge.Snapshot() == (GbaInput.Right | GbaInput.Up | GbaInput.A), "diagonal + action");
TouchInputBridge.Set(3, GbaInput.A);
TouchInputBridge.Remove(2);
Require((TouchInputBridge.Snapshot() & GbaInput.A) != 0, "two contacts same button");
TouchInputBridge.Set(1, GbaInput.Left);
Require(TouchInputBridge.Snapshot() == (GbaInput.Left | GbaInput.A), "move updates contact");
TouchInputBridge.Clear();
Require(TouchInputBridge.Snapshot() == GbaInput.None, "pause/cancel clears");
Require(AndroidTouchLayout.Hit(.05f,.58f) == (GbaInput.Left | GbaInput.Up), "diagonal hit area");
Require(AndroidTouchLayout.Hit(.155f,.72f) == GbaInput.None, "D-pad dead zone");
Require(AndroidTouchLayout.Hit(.92f,.7f) == GbaInput.A && AndroidTouchLayout.Hit(.75f,.7f) == GbaInput.B, "action zones");
Require(AndroidTouchLayout.Hit(float.NaN,.7f) == GbaInput.None, "invalid coordinate");
string root = Path.Combine(Path.GetTempPath(), "rayman-stage02-" + Guid.NewGuid().ToString("N"));
try
{
    byte[] data = new byte[8*1024*1024]; // Synthetic fixture, not a ROM.
    data[123] = 42;
    string hash = Convert.ToHexString(SHA256.HashData(data));
    await Throws<InvalidDataException>(async () => { await PrivateRomStore.ImportAsync(new MemoryStream(data), root, new string('0',64)); });
    Require(!File.Exists(Path.Combine(root,"Gba","rayman3.gba")), "bad digest does not promote");
    await Throws<InvalidDataException>(async () => { await PrivateRomStore.ImportAsync(new MemoryStream(new byte[4]), root, hash); });
    string path = await PrivateRomStore.ImportAsync(new MemoryStream(data), root, hash);
    Require(Convert.ToHexString(SHA256.HashData(await File.ReadAllBytesAsync(path))) == hash, "import bytes unchanged");
    await Throws<IOException>(async () => { await PrivateRomStore.ImportAsync(new MemoryStream(data), root, hash); });
    Require(Convert.ToHexString(SHA256.HashData(await File.ReadAllBytesAsync(path))) == hash, "existing original preserved");
    using var cts = new CancellationTokenSource(); cts.Cancel();
    await Throws<OperationCanceledException>(async () => { await PrivateRomStore.ImportAsync(new MemoryStream(data), root, hash, cts.Token); });
    Require(Directory.GetFiles(Path.GetDirectoryName(path)!,"*.tmp").Length == 0, "no temp leftovers");
}
finally { if (Directory.Exists(root)) Directory.Delete(root,true); }
