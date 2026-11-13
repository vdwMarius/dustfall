using UnrealBuildTool;

public class dustfallTarget : TargetRules
{
    public dustfallTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("dustfall");
    }
}
