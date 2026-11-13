using UnrealBuildTool;

public class dustfall : ModuleRules
{
    public dustfall(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput" });
        if (Target.bBuildEditor) PrivateDependencyModuleNames.AddRange(new[] { "Landscape", "Foliage", "RHI", "RenderCore" });
    }
}
