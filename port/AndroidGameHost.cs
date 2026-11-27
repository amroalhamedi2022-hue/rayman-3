#if ANDROID
using System;
using System.IO;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using Android.App;
using Android.Content;
using Android.Content.PM;
using Android.OS;
using Android.Views;
using Android.Widget;
using Microsoft.Xna.Framework;
using GbaMonoGame;

namespace GbaMonoGame.Rayman3.AndroidHost;

// Compile candidate: no public APK until real content, native audio and device gates pass.
[Activity(Label="Rayman 3", MainLauncher=true, Exported=true,
    ScreenOrientation=ScreenOrientation.SensorLandscape,
    ConfigurationChanges=ConfigChanges.Orientation|ConfigChanges.ScreenSize|ConfigChanges.KeyboardHidden)]
public sealed class AndroidGameHost : AndroidGameActivity
{
    const int ImportRequest=701;
    const int RomSize=8*1024*1024;
    readonly CancellationTokenSource lifetime=new();
    Rayman3GbaGame game;
    Button choose,start;
    TextView status;
    bool busy;
    string UserData=>Path.Combine(FilesDir.AbsolutePath,"UserData");
    string RomFile=>Path.Combine(UserData,"Gba","rayman3.gba");

    protected override void OnCreate(Bundle state)
    {
        base.OnCreate(state);
        Directory.CreateDirectory(UserData);
        var layout=new LinearLayout(this){Orientation=Android.Widget.Orientation.Vertical};
        layout.SetPadding(32,24,32,24);
        status=new TextView(this){TextSize=18};
        choose=new Button(this){Text="Import your GBA ROM"};
        start=new Button(this){Text="Start original game"};
        choose.Click+=(_,_)=>PickRom();
        start.Click+=async (_,_)=>await LaunchAsync();
        layout.AddView(status);layout.AddView(choose);layout.AddView(start);
        SetContentView(layout);
        Refresh("Select your local Rayman 3 GBA ROM. No ROM is bundled.");
    }
    void Refresh(string message)
    {
        status.Text=message;
        choose.Enabled=!busy&&!File.Exists(RomFile);
        start.Enabled=!busy&&File.Exists(RomFile)&&game==null;
    }
    void PickRom()
    {
        var intent=new Intent(Intent.ActionOpenDocument);
        intent.AddCategory(Intent.CategoryOpenable);
        intent.SetType("*/*");
        intent.AddFlags(ActivityFlags.GrantReadUriPermission);
        StartActivityForResult(intent,ImportRequest);
    }
    protected override async void OnActivityResult(int requestCode,Result resultCode,Intent data)
    {
        base.OnActivityResult(requestCode,resultCode,data);
        if(requestCode!=ImportRequest||resultCode!=Result.Ok||data?.Data==null||busy)return;
        busy=true;Refresh("Validating selected ROM...");
        string stage=Path.Combine(CacheDir.AbsolutePath,"rom-"+Guid.NewGuid().ToString("N")+".gba");
        string message;
        try
        {
            // Snapshot once, bound size before writing, and validate via upstream ROM parser.
            await using(var source=ContentResolver.OpenInputStream(data.Data))
            await using(var dest=new FileStream(stage,FileMode.CreateNew,FileAccess.Write,FileShare.None))
            {
                if(source==null)throw new IOException("Selected document cannot be opened");
                byte[] buffer=new byte[65536];int total=0,n;
                while((n=await source.ReadAsync(buffer.AsMemory(),lifetime.Token))!=0)
                {
                    total+=n;if(total>RomSize)throw new InvalidDataException("Unexpected ROM size");
                    await dest.WriteAsync(buffer.AsMemory(0,n),lifetime.Token);
                }
                if(total!=RomSize)throw new InvalidDataException("Unexpected ROM size");
                await dest.FlushAsync(lifetime.Token);
            }
            if(!Rom.ValidateGbaRom(stage,BinarySerializer.Ubisoft.GbaEngine.Game.Rayman3))
                throw new InvalidDataException("Unsupported Rayman 3 ROM edition");
            await using var snapshot=File.OpenRead(stage);
            string digest=Convert.ToHexString(await SHA256.HashDataAsync(snapshot,lifetime.Token));
            snapshot.Position=0;
            // Private deployment may provide the known digest. Otherwise this validates
            // supported edition plus byte-for-byte import, not identity to a specific archival ROM.
            string expectedPath=Path.Combine(UserData,"expected-rom.sha256");
            string expected=File.Exists(expectedPath)?File.ReadAllText(expectedPath).Trim():digest;
            await PrivateRomStore.ImportAsync(snapshot,UserData,expected,lifetime.Token);
            message="ROM imported and validated. Source file was not modified.";
        }
        catch(System.OperationCanceledException){message="Import cancelled.";}
        catch(Exception ex){message="ROM import failed: "+ex.Message;}
        finally { if(File.Exists(stage))File.Delete(stage);busy=false; }
        if(!IsDestroyed)Refresh(message);
    }

    async Task LaunchAsync()
    {
        if(busy||game!=null)return;
        busy=true;Refresh("Checking game content...");
        try
        {
            if(!Rom.ValidateGbaRom(RomFile,BinarySerializer.Ubisoft.GbaEngine.Game.Rayman3))
                throw new InvalidDataException("Installed ROM edition is not supported");
            string expected=Path.Combine(UserData,"expected-rom.sha256");
            if(File.Exists(expected))
            {
                await using var s=File.OpenRead(RomFile);
                string actual=Convert.ToHexString(await SHA256.HashDataAsync(s,lifetime.Token));
                if(!string.Equals(actual,File.ReadAllText(expected).Trim(),StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("Installed ROM differs from the private source digest");
            }
            // MonoGame Android TitleContainer reads packaged assets, while upstream sound/config
            // paths are real filesystem paths. Materialize only hash-listed raw assets.
            await PrepareRawAssetsAsync(lifetime.Token);
            foreach(string shader in new[]{"DefaultShader","PaletteShader","PaletteVertexShader","VertexShader"})
                using(Assets.Open("Assets/GbaMonoGame/Gfx/"+shader+".xnb")){}
            if(IsDestroyed||lifetime.IsCancellationRequested)return;
            Directory.SetCurrentDirectory(FilesDir.AbsolutePath);
            game=new Rayman3GbaGame();
            var view=(View)game.Services.GetService(typeof(View));
            SetContentView(view);
            game.Run();
        }
        catch(Exception ex)
        {
            // Do not mask a failed native/graphics initialization with a fake game.
            if(!IsDestroyed)
            {
                if(game==null)Refresh("Cannot start: "+ex.Message);
                else new AlertDialog.Builder(this).SetTitle("Cannot start").SetMessage(ex.Message)
                    .SetPositiveButton("Close",(_,_)=>Finish()).Show();
            }
        }
        finally{busy=false;if(!IsDestroyed&&game==null){choose.Enabled=!File.Exists(RomFile);start.Enabled=File.Exists(RomFile);}}
    }
    async Task PrepareRawAssetsAsync(CancellationToken token)
    {
        using var manifest=new StreamReader(Assets.Open("Assets/raw-assets.manifest"));
        string root=Path.GetFullPath(FilesDir.AbsolutePath)+Path.DirectorySeparatorChar;
        string line;int count=0;
        while((line=await manifest.ReadLineAsync(token))!=null)
        {
            if(line.Length<67||line.Substring(64,2)!="  ")throw new InvalidDataException("Invalid raw content manifest");
            byte[] expected=Convert.FromHexString(line.Substring(0,64));
            string relative=line.Substring(66);
            if(!relative.StartsWith("Assets/",StringComparison.Ordinal)||relative.Contains('\\'))
                throw new InvalidDataException("Unsafe asset path");
            string ext=Path.GetExtension(relative).ToLowerInvariant();
            if(ext!=".wav"&&ext!=".sf2"&&ext!=".jsonc"&&ext!=".json")
                throw new InvalidDataException("Unexpected raw content type");
            string target=Path.GetFullPath(Path.Combine(root,relative));
            if(!target.StartsWith(root+"Assets"+Path.DirectorySeparatorChar,StringComparison.Ordinal))
                throw new InvalidDataException("Unsafe asset destination");
            if(File.Exists(target))
            {
                await using var existing=File.OpenRead(target);
                if(CryptographicOperations.FixedTimeEquals(await SHA256.HashDataAsync(existing,token),expected)){count++;continue;}
            }
            Directory.CreateDirectory(Path.GetDirectoryName(target));
            string tmp=target+"."+Guid.NewGuid().ToString("N")+".tmp";
            try
            {
                using var input=Assets.Open(relative);
                await using(var output=new FileStream(tmp,FileMode.CreateNew,FileAccess.Write,FileShare.None))
                {await input.CopyToAsync(output,token);await output.FlushAsync(token);}
                await using(var verify=File.OpenRead(tmp))
                    if(!CryptographicOperations.FixedTimeEquals(await SHA256.HashDataAsync(verify,token),expected))
                        throw new InvalidDataException("Raw content digest mismatch");
                File.Move(tmp,target,true);count++;
            }
            finally{if(File.Exists(tmp))File.Delete(tmp);}
        }
        if(count==0)throw new InvalidDataException("Raw content is missing");
    }
    protected override void OnPause(){TouchInputBridge.Clear();base.OnPause();}
    protected override void OnDestroy(){lifetime.Cancel();TouchInputBridge.Clear();base.OnDestroy();}
}
#endif
