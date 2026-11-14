#include "World/DustfallAtmosphereFX.h"
#include "World/DustfallAtmosphereTuning.h"
#include "World/DustfallAtmosphereMath.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "HAL/IConsoleManager.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Engine/World.h"
#if WITH_EDITOR
#include "ActorFolder.h"
#include "UObject/Package.h"
#endif
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Math/RotationMatrix.h"
#include "UObject/UnrealType.h"

namespace
{
    double ReadNumber(const UObject* Object, const FName Name)
    {
        if (!Object) return 0.;
        const FNumericProperty* Property = FindFProperty<FNumericProperty>(Object->GetClass(), Name);
        if (!Property) return 0.;
        const void* Value = Property->ContainerPtrToValuePtr<void>(Object);
        return Property->IsFloatingPoint() ? Property->GetFloatingPointPropertyValue(Value)
            : static_cast<double>(Property->GetSignedIntPropertyValue(Value));
    }
    template<typename T> T* ReadComponent(const UObject* Object, const FName Name)
    {
        const FObjectPropertyBase* Property = Object ? FindFProperty<FObjectPropertyBase>(Object->GetClass(), Name) : nullptr;
        return Property ? Cast<T>(Property->GetObjectPropertyValue_InContainer(Object)) : nullptr;
    }
    bool IsInside(const UObject* Object)
    {
        const FBoolProperty* Property = Object ? FindFProperty<FBoolProperty>(Object->GetClass(), TEXT("InHabitat")) : nullptr;
        return Property && Property->GetPropertyValue_InContainer(Object);
    }
}

ADustfallAtmosphereFX::ADustfallAtmosphereFX()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostUpdateWork;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    Moon = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Moon"));
    Moon->SetupAttachment(RootComponent);
    Moon->SetMobility(EComponentMobility::Movable);
    Moon->SetAtmosphereSunLight(true);
    Moon->SetAtmosphereSunLightIndex(1);
    Moon->SetIntensity(0.f);
    Moon->SetCastShadows(false);
    NightPostProcess = CreateDefaultSubobject<UPostProcessComponent>(TEXT("NightPostProcess"));
    NightPostProcess->SetupAttachment(RootComponent);
    NightPostProcess->bUnbound = true;
    NightPostProcess->BlendWeight = 0.f;
    Motes = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Motes"));
    Sheets = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Sheets"));
    GroundSheets = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("GroundSheets"));
    for (UInstancedStaticMeshComponent* Layer : {Motes.Get(), Sheets.Get(), GroundSheets.Get()})
    {
        Layer->SetupAttachment(RootComponent);
        Layer->SetMobility(EComponentMobility::Movable);
        Layer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Layer->SetGenerateOverlapEvents(false);
        Layer->SetCanEverAffectNavigation(false);
        Layer->SetCastShadow(false);
        Layer->SetNumCustomDataFloats(1);
    }
}

bool ADustfallAtmosphereFX::SetCaptureSaveSlot(AActor* Director, const FString& Slot)
{
#if WITH_EDITOR
    if (!IsValid(Director) || !Director->GetWorld() || Director->GetWorld()->WorldType != EWorldType::Editor
        || Director->GetClass()->GetFName() != FName(TEXT("BP_SurvivalDirector_C"))) return false;
    if (const FStrProperty* Property = FindFProperty<FStrProperty>(Director->GetClass(), TEXT("SaveSlotName")))
    {
        Property->SetPropertyValue_InContainer(Director, Slot);
        return true;
    }
#endif
    return false;
}

TArray<UPackage*> ADustfallAtmosphereFX::GetAuthoringPackages(bool bIncludeFolders) const
{
    TArray<UPackage*> Packages;
#if WITH_EDITOR
    Packages.AddUnique(GetPackage());
    TInlineComponentArray<UActorComponent*> Components;
    GetComponents(Components);
    for (const UActorComponent* Component : Components) Packages.AddUnique(Component->GetPackage());
    if (bIncludeFolders)
        for (FFolder Folder = GetFolder(); !Folder.IsNone(); Folder = Folder.GetParent())
            if (const UActorFolder* Object = Folder.GetActorFolder()) Packages.AddUnique(Object->GetPackage());
#endif
    return Packages;
}

void ADustfallAtmosphereFX::FindDirectors()
{
    UClass* EnvironmentClass = LoadClass<AActor>(nullptr,
        TEXT("/Game/World/Blueprints/BP_DustfallEnvironmentDirector.BP_DustfallEnvironmentDirector_C"));
    UClass* SurvivalClass = LoadClass<AActor>(nullptr, TEXT("/Game/Systems/BP_SurvivalDirector.BP_SurvivalDirector_C"));
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        if (EnvironmentClass && It->IsA(EnvironmentClass)) Environment = *It;
        if (SurvivalClass && It->IsA(SurvivalClass)) Survival = *It;
    }
    if (Environment) AddTickPrerequisiteActor(Environment);
    if (Survival) AddTickPrerequisiteActor(Survival);
}

void ADustfallAtmosphereFX::BeginPlay()
{
    Super::BeginPlay();
    if (!Tuning) { SetActorTickEnabled(false); return; }
    FindDirectors();
    LandscapeClass = LoadClass<AActor>(nullptr, TEXT("/Script/Landscape.LandscapeProxy"));
    const auto& T = *Tuning;
    Moon->SetLightColor(T.MoonColor);
    Moon->SetLightSourceAngle(T.MoonDiscDegrees);
    Moon->SetAtmosphereSunDiskColorScale(T.MoonDiscScale);
    Moon->SetCastShadows(T.MoonShadows);
    NightPostProcess->Priority = T.PostProcessPriority;
    auto& Post = NightPostProcess->Settings;
    // The authored exposure volume locks min/max EV100 to 0. Bias is additive at
    // runtime; do not mutate that volume or its saved settings. Tint neutralizes
    // its daylight orange cast at night so cool moonlight remains readable.
    Post.bOverride_AutoExposureBias = true;
    Post.AutoExposureBias = T.NightExposureBias;
    Post.bOverride_SceneColorTint = true;
    // SceneView.cpp LERP_PP(SceneColorTint): high-priority full-night override
    // replaces Phase3's (1,.65,.35), rather than multiplying an inverse tint.
    Post.SceneColorTint = T.NightSceneTint;
    Post.bOverride_ColorSaturation = true;
    Post.ColorSaturation = FVector4(1, 1, 1, T.NightSaturation);
    Post.bOverride_ColorOffset = true;
    Post.ColorOffset = FVector4(0, 0, 0, T.NightBlackLift);
    if (T.HorizonMaterial)
    {
        HorizonMID = UMaterialInstanceDynamic::Create(T.HorizonMaterial, this);
        NightPostProcess->AddOrUpdateBlendable(HorizonMID.Get());
        HorizonMID->SetVectorParameterValue(TEXT("HorizonColor"), T.NightHorizonColor);
        HorizonMID->SetVectorParameterValue(TEXT("HaloColor"), T.MoonHaloColor);
        HorizonMID->SetScalarParameterValue(TEXT("HorizonWidth"), T.HorizonWidth);
        HorizonMID->SetScalarParameterValue(TEXT("HaloRadians"), FMath::DegreesToRadians(T.MoonHaloDegrees));
    }
    FRandomStream Random(T.Seed);
    const int32 Count = FMath::Clamp(T.MoteCount, 0, 512);
    for (UInstancedStaticMeshComponent* Layer : {Motes.Get(), Sheets.Get(), GroundSheets.Get()}) Layer->SetStaticMesh(T.DustPlane);
    if (T.MoteMaterial) MoteMID = Motes->CreateDynamicMaterialInstance(0, T.MoteMaterial);
    if (T.SheetMaterial)
    {
        SheetMID = Sheets->CreateDynamicMaterialInstance(0, T.SheetMaterial);
        GroundMID = GroundSheets->CreateDynamicMaterialInstance(0, T.SheetMaterial);
    }
    for (UMaterialInstanceDynamic* MID : {MoteMID.Get(), SheetMID.Get(), GroundMID.Get()})
    {
        if (!MID) continue;
        MID->SetScalarParameterValue(TEXT("NearStart"), T.NearFadeStart);
        MID->SetScalarParameterValue(TEXT("NearEnd"), T.NearFadeEnd);
        MID->SetScalarParameterValue(TEXT("DepthFade"), T.DepthFadeDistance);
        MID->SetVectorParameterValue(TEXT("Pan"), FLinearColor(static_cast<float>(T.NoisePan.X), static_cast<float>(T.NoisePan.Y), 0, 0));
    }
    for (int32 Index = 0; Index < Count; ++Index)
    {
        Positions.Add(FVector(Random.FRandRange(-static_cast<float>(T.VolumeHalfExtent.X), static_cast<float>(T.VolumeHalfExtent.X)),
            Random.FRandRange(-static_cast<float>(T.VolumeHalfExtent.Y), static_cast<float>(T.VolumeHalfExtent.Y)),
            Random.FRandRange(-static_cast<float>(T.VolumeHalfExtent.Z), static_cast<float>(T.VolumeHalfExtent.Z))));
        Variations.Add(Random.FRand());
        const bool bSpeck = Random.FRand() < T.MoteFraction;
        const float SizeVariation = Random.FRandRange(static_cast<float>(T.ParticleSizeVariation.X), static_cast<float>(T.ParticleSizeVariation.Y));
        Sizes.Add((bSpeck ? FVector2D(T.MoteDiameter, T.MoteDiameter) : T.MoteSize) * SizeVariation);
        Specks.Add(bSpeck);
        Motes->AddInstance(FTransform::Identity);
        Motes->SetCustomDataValue(Index, 0, static_cast<float>(Random.FRandRange(.5f, 1.f)));
    }
    for (int32 Index = 0; Index < 3; ++Index)
    {
        GroundSheets->AddInstance(FTransform::Identity);
        Sheets->AddInstance(FTransform::Identity);
        Sheets->SetCustomDataValue(Index, 0, static_cast<float>(Random.FRandRange(.5f, 1.f)));
    }
}

void ADustfallAtmosphereFX::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!Tuning || !IsValid(Environment)) return;
    const auto& T = *Tuning;
    using Math = FDustfallAtmosphereMath;
    const float Night = Math::Night(static_cast<float>(ReadNumber(Environment, TEXT("TimeOfDay"))), T.TwilightStart, T.TwilightEnd);
    const int32 Weather = static_cast<int32>(ReadNumber(Environment, TEXT("Weather")));
    const float Storm = static_cast<float>(ReadNumber(Environment, TEXT("StormIntensity")));
    if (auto* Fog = ReadComponent<UExponentialHeightFogComponent>(Environment, TEXT("FogComponent")))
    {
        // UE5.8 HeightFogCommon.ush: CalculateHeightFog excludes V/cos(view angle);
        // StartDistance=max(exclusion, start), NOT a far crossfade. CombineVolumetricFog
        // returns Cv + Tv*Ca, Tv*Ta. NearFadeInDistance fades the CAMERA-side start only.
        // VolumetricFog.usf MaterialSetup: sigma=.5*rho/1000*ext; Integration:
        // Cv=(j/sigma)*(1-Tv). Choose j=C*sigma and zero albedo so BOTH source
        // radiances equal C: Cv+Tv*Ca=C*(1-Tv*Ta). No radiance boundary in day/night.
        // Homogeneous height/second layer is essential: legacy emissive is a constant
        // density, not height-modulated. PROJECT_EXPFOG_MATCHES_VFOG instead multiplies
        // j by .5*rho/1000 and uses Emissive as analytic C (requires ext=1).
        // SceneCore.cpp scales legacy emissive settings by 1/10000, so author
        // 10000*C*sigma. Do not confuse the component setting with shader j.
        // No engine/config change. Physical local-light scattering is replaced by a
        // cheap spotlight cone evaluated on the six dust sheets and tiny particles.
        // Horizontal predictions at 5/10/15/25/150m (transmission, NOT pixel contrast):
        // calm rho=.3 V=60m ext=.2 cap=.82: .985/.970/.956/.928/.228
        // haze rho=.6 V=40m ext=.3 cap=.86: .956/.914/.874/.799/.098
        // storm rho=3.3 V=10m ext=.5 cap=.40: .662/.438/.263/.263/.263
        // Round 4 LIVE isolation: original storm horizon contrast ~0; dust off
        // ~0; extinction off .010 (and a seam); extinction=0/cap=.01 gives .648.
        // Haze source x.2 gives .076 horizon contrast (forward view -.117).
        // Storm source x.075/dust x.1 gives .084 but turns daytime storms near black:
        // REJECTED. Lead fix: keep the source, raise StormLightMultiplier .52 -> 2.0 so
        // the lit scene is no longer far dimmer than the fog (captures: figures clear
        // at 5/10 m, faint at 15-25 m, ridges and the 150 m box as faint silhouettes).
        Fog->SetFogMaxOpacity(FMath::Clamp(Math::Weather(T.FogMaxOpacity, Weather, Storm), 0.f, 1.f));
        Fog->SetStartDistance(Math::Weather(T.FogStartDistance, Weather, Storm));
        Fog->SetVolumetricFogDistance(Math::Weather(T.VolumetricFogDistance, Weather, Storm));
        Fog->SetVolumetricFog(true);
        Fog->SetVolumetricFogStartDistance(0.f);
        Fog->SetVolumetricFogNearFadeInDistance(0.f);
        float Extinction = Math::Weather(T.VolumetricExtinction, Weather, Storm);
        const FLinearColor DayColor = FMath::Lerp(Weather == 0 ? T.CalmFogColor : T.HazeFogColor, T.StormFogColor, FMath::Clamp(Storm, 0.f, 1.f));
        const FLinearColor Source = FMath::Lerp(DayColor, T.NightFogColor, Night);
        const IConsoleVariable* Match = IConsoleManager::Get().FindConsoleVariable(TEXT("r.SupportExpFogMatchesVolumetricFog"));
        const bool bMatches = Match && Match->GetInt() != 0;
        // The optional engine matching permutation binds analytic C to Emissive,
        // so equality then requires extinction=1. Current project uses default 0.
        if (bMatches) Extinction = 1.f;
        Fog->SetFogHeightFalloff(0.f);
        Fog->SetSecondFogDensity(0.f);
        Fog->SetVolumetricFogExtinctionScale(Extinction);
        Fog->SetVolumetricFogAlbedo(FColor::Black);
        Fog->SetVolumetricFogEmissive(bMatches ? Source : Source * Math::EmissiveSetting(Fog->FogDensity, Extinction));
        Fog->SetFogInscatteringColor(Source);
        Fog->SetInscatteringColorCubemap(nullptr);
        Fog->SetSkyAtmosphereAmbientContributionColorScale(FLinearColor::Black);
        Fog->SetDirectionalInscatteringColor(FLinearColor::Black);
        if (Fog->SkyLightCaptureAffectsHeightFogStrength != 0.f)
        {
            Fog->SkyLightCaptureAffectsHeightFogStrength = 0.f;
            Fog->MarkRenderStateDirty();
        }
    }
    if (auto* Sky = ReadComponent<USkyLightComponent>(Environment, TEXT("SkyComponent")))
        Sky->SetIntensity(FMath::Max(Sky->Intensity, T.NightSkyMinimum * Night));
    if (auto* Sun = ReadComponent<UDirectionalLightComponent>(Environment, TEXT("SunComponent")))
    {
        const FRotator SunRotation = Sun->GetComponentRotation();
        Moon->SetWorldRotation(FRotator(-SunRotation.Pitch * T.MoonElevationScale, SunRotation.Yaw + T.MoonYawOffset, 0));
    }
    Moon->SetIntensity(T.MoonLux * Night);
    NightPostProcess->BlendWeight = Night;
    if (HorizonMID)
    {
        const FVector Direction = -Moon->GetForwardVector();
        HorizonMID->SetVectorParameterValue(TEXT("MoonDirection"), FLinearColor(static_cast<float>(Direction.X), static_cast<float>(Direction.Y), static_cast<float>(Direction.Z)));
    }
    InteriorVisibility = Math::Approach(InteriorVisibility, IsValid(Survival) && !IsInside(Survival) ? 1.f : 0.f, T.InteriorFadeSpeed, DeltaSeconds);
    const float Opacity = Math::Weather(T.DustOpacity, Weather, Storm) * InteriorVisibility;
    for (UMaterialInstanceDynamic* MID : {MoteMID.Get(), SheetMID.Get(), GroundMID.Get()})
    {
        if (!MID) continue;
        const float LayerOpacity = MID == GroundMID.Get() ? Math::Weather(T.GroundDustOpacity, Weather, Storm)
            : MID == SheetMID.Get() ? T.SheetOpacityScale : T.StreakOpacityScale;
        MID->SetScalarParameterValue(TEXT("Opacity"), Opacity * LayerOpacity);
        MID->SetVectorParameterValue(TEXT("DustColor"), FMath::Lerp(T.DayDustColor, T.NightDustColor, Night));
    }
    APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0);
    if (!Camera) return;
    // Runtime presentation only: read the existing flashlight, never change it.
    USpotLightComponent* Flashlight = nullptr;
    if (AActor* Pawn = UGameplayStatics::GetPlayerPawn(this, 0))
    {
        TInlineComponentArray<USpotLightComponent*> Lights;
        Pawn->GetComponents(Lights);
        for (USpotLightComponent* Light : Lights)
            if (Light->GetName().Contains(TEXT("Flashlight"))) { Flashlight = Light; break; }
    }
    for (UMaterialInstanceDynamic* MID : {MoteMID.Get(), SheetMID.Get(), GroundMID.Get()})
    {
        if (!MID) continue;
        const bool bLit = Flashlight && Flashlight->IsVisible() && Flashlight->Intensity > 0.f;
        MID->SetScalarParameterValue(TEXT("FlashlightGain"), bLit ? T.FlashlightDustGain : 0.f);
        if (!bLit) continue;
        const FVector Position = Flashlight->GetComponentLocation(), Direction = Flashlight->GetForwardVector();
        MID->SetVectorParameterValue(TEXT("FlashlightPosition"), FLinearColor(static_cast<float>(Position.X), static_cast<float>(Position.Y), static_cast<float>(Position.Z)));
        MID->SetVectorParameterValue(TEXT("FlashlightDirection"), FLinearColor(static_cast<float>(Direction.X), static_cast<float>(Direction.Y), static_cast<float>(Direction.Z)));
        MID->SetScalarParameterValue(TEXT("FlashlightRange"), Flashlight->AttenuationRadius);
        MID->SetScalarParameterValue(TEXT("FlashlightCosOuter"), FMath::Cos(FMath::DegreesToRadians(Flashlight->OuterConeAngle)));
        MID->SetScalarParameterValue(TEXT("FlashlightCosInner"), FMath::Cos(FMath::DegreesToRadians(Flashlight->InnerConeAngle)));
        MID->SetVectorParameterValue(TEXT("FlashlightColor"), Flashlight->GetLightColor());
    }
    const FQuat View = Camera->GetCameraRotation().Quaternion();
    // Plane mesh is 100cm square in XY, normal +Z; rotate it to face the camera.
    const FQuat Facing = FRotationMatrix::MakeFromZY(-View.GetForwardVector(), T.WindDirection.GetSafeNormal()).ToQuat();
    const FVector LocalWind = Facing.UnrotateVector(T.WindDirection.GetSafeNormal());
    const float Speed = Math::Weather(T.DustSpeed, Weather, Storm);
    const FVector Wind = View.UnrotateVector(T.WindDirection.GetSafeNormal()) * Speed;
    // Plane local Y is projected wind; both material octaves use this direction/speed.
    for (UMaterialInstanceDynamic* MID : {MoteMID.Get(), SheetMID.Get(), GroundMID.Get()})
        if (MID) MID->SetVectorParameterValue(TEXT("Pan"), FLinearColor(
            -static_cast<float>(LocalWind.X * T.NoisePan.X) * Speed / FMath::Max(T.SheetSize, 1.f),
            -static_cast<float>(LocalWind.Y * T.NoisePan.Y) * Speed / FMath::Max(T.SheetSize, 1.f), 0, 0));
    const float Density = FMath::Clamp(Math::Weather(T.DustDensity, Weather, Storm), 0.f, 1.f);
    SheetDrift += Wind * DeltaSeconds;
    for (int32 Index = 0; Index < Positions.Num(); ++Index)
    {
        FVector& Position = Positions[Index];
        Position += Wind * DeltaSeconds;
        Position.X = Math::Wrap(static_cast<float>(Position.X), static_cast<float>(T.VolumeHalfExtent.X));
        Position.Y = Math::Wrap(static_cast<float>(Position.Y), static_cast<float>(T.VolumeHalfExtent.Y));
        Position.Z = Math::Wrap(static_cast<float>(Position.Z), static_cast<float>(T.VolumeHalfExtent.Z));
        const FVector Location = Camera->GetCameraLocation() + View.RotateVector(Position + FVector(T.VolumeForward, 0, 0));
        // Fade at the volume boundaries before wrapping, and introduce density
        // continuously rather than popping whole instances during weather blends.
        const float Margin = static_cast<float>(FMath::Min3(1.f - FMath::Abs(Position.X) / FMath::Max(T.VolumeHalfExtent.X, 1.),
            1.f - FMath::Abs(Position.Y) / FMath::Max(T.VolumeHalfExtent.Y, 1.),
            1.f - FMath::Abs(Position.Z) / FMath::Max(T.VolumeHalfExtent.Z, 1.)));
        const float Active = Math::Smooth(0, T.DensityFeather, Density - Variations[Index])
            * Math::Smooth(0, T.BoundsFadeFraction, Margin);
        Motes->SetCustomDataValue(Index, 0, Active * FMath::Lerp(.5f, 1.f, Variations[Index]) * (Specks[Index] ? T.SpeckOpacityScale : 1.f));
        const float LengthScale = Specks[Index] ? 1.f : Math::StreakLength(Speed, T.StreakReferenceSpeed, T.StreakMinimumLengthScale);
        const FVector Scale(Sizes[Index].X * (Specks[Index] ? 1.f : T.StreakWidthScale) / 100.f, Sizes[Index].Y * LengthScale / 100.f, 1);
        Motes->UpdateInstanceTransform(Index, FTransform(Facing, Location, Scale), true, false, true);
    }
    for (int32 Index = 0; Index < 3; ++Index)
    {
        const float Distance = static_cast<float>(T.SheetDistances[Index]);
        const FVector Offset(Distance, FMath::Sin(SheetDrift.Y / FMath::Max(T.SheetSize, 1.f)) * T.SheetSize * T.SheetDriftFraction,
            FMath::Sin(SheetDrift.Z / FMath::Max(T.SheetSize, 1.f)) * T.SheetSize * T.SheetDriftFraction);
        Sheets->UpdateInstanceTransform(Index, FTransform(Facing, Camera->GetCameraLocation() + View.RotateVector(Offset),
            FVector(T.SheetSize / 100.f, T.SheetSize / 100.f, 1)), true, false, true);
    }
    // Object multi-trace returns all matching static objects; select landscape
    // hits below without a world-size actor ignore list. Tangent planes
    // within 1.5m of the terrain under the camera. No saved world modifications.
    FHitResult Ground;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(AtmosphereGround), false, this);
    Query.AddIgnoredActor(UGameplayStatics::GetPlayerPawn(this, 0));
    const FVector CameraLocation = Camera->GetCameraLocation();
    TArray<FHitResult> Hits;
    GetWorld()->LineTraceMultiByObjectType(Hits, CameraLocation,
        CameraLocation - FVector(0, 0, T.GroundTraceDistance), FCollisionObjectQueryParams(ECC_WorldStatic), Query);
    bool bGround = false;
    for (const FHitResult& Hit : Hits)
    {
        if (LandscapeClass && Hit.GetActor() && Hit.GetActor()->IsA(LandscapeClass))
        {
            Ground = Hit;
            bGround = true;
            break;
        }
    }
    if (bGround)
    {
        const FVector Normal = Ground.ImpactNormal.GetSafeNormal();
        const FQuat GroundFacing = FRotationMatrix::MakeFromZY(Normal, T.WindDirection).ToQuat();
        const FVector GroundWind = GroundFacing.UnrotateVector(T.WindDirection.GetSafeNormal());
        if (GroundMID) GroundMID->SetVectorParameterValue(TEXT("Pan"), FLinearColor(
            -static_cast<float>(GroundWind.X * T.NoisePan.X) * Speed / FMath::Max(T.GroundSheetSize, 1.f),
            -static_cast<float>(GroundWind.Y * T.NoisePan.Y) * Speed / FMath::Max(T.GroundSheetSize, 1.f), 0, 0));
        for (int32 Index = 0; Index < 3; ++Index)
        {
            const float Height = static_cast<float>(T.GroundSheetHeights[Index]);
            GroundSheets->SetCustomDataValue(Index, 0, Math::GroundHeightFade(Height, T.GroundDustHeight));
            GroundSheets->UpdateInstanceTransform(Index, FTransform(GroundFacing, Ground.ImpactPoint + Normal * Height,
                FVector(T.GroundSheetSize / 100.f, T.GroundSheetSize / 100.f, 1)), true, false, true);
        }
    }
    GroundSheets->SetVisibility(bGround && Opacity > KINDA_SMALL_NUMBER);
    GroundSheets->MarkRenderStateDirty();
    Motes->SetVisibility(Opacity > KINDA_SMALL_NUMBER);
    Sheets->SetVisibility(Opacity > KINDA_SMALL_NUMBER);
    Motes->MarkRenderStateDirty();
    Sheets->MarkRenderStateDirty();
}
