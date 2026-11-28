#if ANDROID
namespace GbaMonoGame;

// Values follow the pinned upstream GameOptions.cs ORIGINAL presets, not guesses.
// This is an initial Android fidelity baseline, not a claim of ROM parity.
internal static class FaithfulGbaProfile
{
    internal static void Apply(LocalGameSettings settings)
    {
        settings.Tweaks.InternalGameResolution = null; // Rom.Init selects actual original resolution.
        settings.Tweaks.KeepAllKnotsActive = null; // upstream provides no ORIGINAL preset assignment.
        // The 27 explicit boolean ORIGINAL preset selections:
        settings.Tweaks.UseExtendedBackgrounds = false;
        settings.Tweaks.FixTilingErrors = false;
        settings.Tweaks.UseGbaEffectsOnNGage = false;
        settings.Tweaks.UseModernMainMenu = false;
        settings.Tweaks.UseModernPauseDialog = false;
        settings.Tweaks.UseReadvancedLogo = false;
        settings.Tweaks.CanSkipTextBoxes = false;
        settings.Tweaks.FixBugs = false;
        settings.Tweaks.AddProjectilesWhenNeeded = false;
        settings.Tweaks.VisualImprovements = false;
        settings.Tweaks.ShowMode7Walls = false;
        settings.Tweaks.ShowCollectedLums = false;
        settings.Tweaks.AllowCheatMenu = false;
        settings.Tweaks.AllowPrototypeCheats = false;
        settings.Tweaks.PlayCheatTriggerSound = false;
        settings.Tweaks.VersatileWalljumps = false;
        settings.Tweaks.UseInputBuffering = false;
        settings.Tweaks.ShowAdditionalGameplayHints = false;
        settings.Tweaks.AllowRunOnWorldmap = false;
        settings.Tweaks.FixHelicoHitbox = false;
        settings.Tweaks.LowerInitialPlumSpeed = false;
        settings.Tweaks.PauseBlueLumTimerWhenStopped = false;
        settings.Difficulty.InfiniteLives = false;
        settings.Difficulty.NoInstaKills = false;
        settings.Difficulty.KeepLumsInRaces = false;
        settings.Difficulty.NoCheckpoints = false;
        settings.Difficulty.OneHitPoint = false;
        // Additional platform choices, separate from the original presets:
        settings.Tweaks.PauseOnDeactivation = true;
        settings.Controls.UseModernButtonMapping = false;
        settings.Controls.UseStandardKeyboardKeys = false;
        settings.Debug.DebugModeEnabled = false;
        settings.Debug.WriteSerializerLog = false;
        settings.Display.AltEnterToggle = null;
    }
}
#endif
