using UnrealBuildTool;

public class dustfallEditorTarget : TargetRules
{
    public dustfallEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.Latest;
        IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
        ExtraModuleNames.Add("dustfall");
    }
}
