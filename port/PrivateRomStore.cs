// Platform-neutral import into Readvanced's existing private UserData/Gba/rayman3.gba path.
// The caller supplies Android FilesDir/UserData and a source stream opened via SAF.
// No ROM is distributed, no network, no modification of the source stream contents.
using System;
using System.IO;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;

namespace GbaMonoGame;
public static class PrivateRomStore
{
    public static async Task<string> ImportAsync(Stream source, string userDataPath,
        string expectedSha256, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(source);
        if (!Path.IsPathFullyQualified(userDataPath)) throw new ArgumentException("Absolute private path required");
        byte[] expected = Convert.FromHexString(expectedSha256);
        if (expected.Length != 32) throw new ArgumentException("Expected SHA-256 required");
        string dir = Path.Combine(userDataPath, "Gba");
        Directory.CreateDirectory(dir);
        string target = Path.Combine(dir, "rayman3.gba");
        string temp = Path.Combine(dir, $".import-{Guid.NewGuid():N}.tmp");
        try
        {
            const int expectedSize = 8 * 1024 * 1024; // current project ROM; do not generalize to unknown editions
            using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
            int total = 0;
            byte[] buffer = new byte[65536];
            await using (var output = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            {
                int n;
                while ((n = await source.ReadAsync(buffer.AsMemory(), cancellationToken)) != 0)
                {
                    total += n;
                    if (total > expectedSize) throw new InvalidDataException("Unexpected ROM size");
                    hash.AppendData(buffer, 0, n);
                    await output.WriteAsync(buffer.AsMemory(0, n), cancellationToken);
                }
                if (total != expectedSize || !CryptographicOperations.FixedTimeEquals(hash.GetHashAndReset(), expected))
                    throw new InvalidDataException("ROM does not match the selected verified source");
                await output.FlushAsync(cancellationToken);
                output.Flush(true);
            }
            cancellationToken.ThrowIfCancellationRequested();
            // Never replace an existing ROM automatically, even if hashes are identical.
            File.Move(temp, target, overwrite: false);
            return target;
        }
        finally { if (File.Exists(temp)) File.Delete(temp); }
    }
}
