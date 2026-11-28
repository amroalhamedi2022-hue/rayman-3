# Runs on disposable Windows CI; never publishes an APK or game content.
$ErrorActionPreference = 'Stop'
function CheckExit([string] $Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed: exit $LASTEXITCODE" }
}
$repo = Join-Path $env:RUNNER_TEMP "readvanced"
$assets = Join-Path $env:RUNNER_TEMP "staged-android-assets"
$audio = Join-Path $env:RUNNER_TEMP "native-candidate"
$inventory = Join-Path $env:RUNNER_TEMP "package-inventory.json"
git clone --no-checkout https://github.com/RayCarrot/Rayman3Readvanced.git $repo
CheckExit "Checkout"
git -C $repo checkout --detach dd8fb6d9ea34decedc4e57d4c5deebc008b8adbd
CheckExit "Pin"
git -C $repo submodule update --init --recursive
CheckExit "Submodules"
dotnet tool install dotnet-mgcb --version 3.8.4.1 --tool-path "$env:RUNNER_TEMP/mgcb"
CheckExit "MGCB installation"
foreach ($project in @('GbaMonoGame','GbaMonoGame.TgxEngine','GbaMonoGame.Rayman3')) {
    $dir = Join-Path "$repo/src" "$project/Assets"
    $out = Join-Path $env:RUNNER_TEMP "content-$project"
    $obj = Join-Path $env:RUNNER_TEMP "content-obj-$project"
    Push-Location $dir
    try {
        & "$env:RUNNER_TEMP/mgcb/mgcb.exe" "/@:$dir/Assets.mgcb" "/platform:Android" "/outputDir:$out" "/intermediateDir:$obj" "/workingDir:$dir" 2>&1 | Tee-Object -FilePath "$env:RUNNER_TEMP/package-content-$project.log"
        CheckExit "Android content $project"
    } finally { Pop-Location }
}
python port/stage_android_content.py --checkout $repo --content-root $env:RUNNER_TEMP --output $assets
CheckExit "Staging"
python port/prepare_android_compile_probe.py --checkout $repo
CheckExit "Managed source adaptation"
python port/prepare_android_package.py --checkout $repo --assets $assets --native-library "$audio/libsoloud.so" --abi-report "$audio/soloud-abi.json" --inventory $inventory
CheckExit "Package source preparation"
Push-Location "$repo/src"
try {
    New-Item -ItemType Directory -Force -Path "nuget-artifacts" | Out-Null
    dotnet pack GbaMonoGame.Native/GbaMonoGame.Native.csproj -c Release -p:GeneratePackageOnBuild=false -o "$PWD/nuget-artifacts"
    CheckExit "Local interop NuGet package"
    if (!(Test-Path "nuget-artifacts/GbaMonoGame.Native.1.0.0.nupkg")) { throw "Native managed package missing" }
    $app = "GbaMonoGame.Rayman3.Android/GbaMonoGame.Rayman3.Android.csproj"
    $sdk = $env:ANDROID_HOME
    if (!$sdk) { $sdk = $env:ANDROID_SDK_ROOT }
    if (!$sdk) { $sdk = Join-Path $env:RUNNER_TEMP "android-sdk" }
    dotnet build $app -t:InstallAndroidDependencies -f net10.0-android "-p:AndroidSdkDirectory=$sdk" "-p:JavaSdkDirectory=$env:JAVA_HOME" -p:AcceptAndroidSDKLicenses=true
    CheckExit "Android SDK dependencies"
    dotnet build $app -f net10.0-android -c Release "-p:AndroidSdkDirectory=$sdk" "-p:JavaSdkDirectory=$env:JAVA_HOME" -p:RuntimeIdentifier=android-arm64 --verbosity minimal 2>&1 | Tee-Object -FilePath "$env:RUNNER_TEMP/package-build.log"
    CheckExit "APK package build"
    $apks = @(Get-ChildItem "GbaMonoGame.Rayman3.Android/bin/Release" -Recurse -Filter "*-Signed.apk" -File)
    if ($apks.Count -eq 0) { $apks = @(Get-ChildItem "GbaMonoGame.Rayman3.Android/bin/Release" -Recurse -Filter "*.apk" -File) }
    if ($apks.Count -ne 1) { throw "Expected exactly one package candidate; found $($apks.Count)" }
    $apk = $apks[0].FullName
    python "$env:GITHUB_WORKSPACE/port/verify_android_package.py" --apk $apk --inventory $inventory | Tee-Object -FilePath "$env:RUNNER_TEMP/package-verification.log"
    CheckExit "APK content verification"
    $tools = Get-ChildItem "$sdk/build-tools" -Directory | Sort-Object Name -Descending | Where-Object { Test-Path "$($_.FullName)/aapt2.exe" } | Select-Object -First 1
    if (!$tools) { throw "aapt2 not found" }
    $badging = & "$($tools.FullName)/aapt2.exe" dump badging $apk
    CheckExit "Manifest inspection"
    $badging | Out-File "$env:RUNNER_TEMP/package-manifest.log" -Encoding utf8
    $text = $badging -join "`n"
    if ($text -notmatch "package: name='org.readvanced.rayman3.androidtest'") { throw "Incorrect app ID" }
    if ($text -notmatch "launchable-activity:") { throw "Missing launchable Activity" }
    if ($text -match "android.permission.(INTERNET|READ_EXTERNAL_STORAGE|WRITE_EXTERNAL_STORAGE|MANAGE_EXTERNAL_STORAGE)") { throw "Offline/private-storage permission gate failed" }
    if ($text -notmatch "native-code:.*arm64-v8a") { throw "Missing ARM64 in package metadata" }
    Write-Host "Private APK packaging and manifest probe passed. No APK uploaded, device test pending."
} finally { Pop-Location }
