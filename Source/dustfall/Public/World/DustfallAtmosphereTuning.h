#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "DustfallAtmosphereTuning.generated.h"

class UMaterialInterface;
class UStaticMesh;

/** Units: cm, seconds, directional-light lux. Vector weather values = calm/haze/storm. */
UCLASS(BlueprintType)
class DUSTFALL_API UDustfallAtmosphereTuning : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector FogMaxOpacity = FVector(.82, .86, .40);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector FogStartDistance = FVector(0, 0, 0);
    // Near volumetric transmission multiplies the analytic cap; see FX.cpp.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector VolumetricExtinction = FVector(.2, .3, .5);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector VolumetricFogDistance = FVector(6000, 4000, 1000);
    // Shared source radiance. Homogeneous fog makes emissive/extinction constant
    // on every ray; height-dependent dust comes from the terrain-following sheets.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FLinearColor CalmFogColor = FLinearColor(.26f, .18f, .11f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FLinearColor HazeFogColor = FLinearColor(.30f, .21f, .13f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FLinearColor StormFogColor = FLinearColor(.34f, .24f, .15f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float FlashlightDustGain = .12f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float TwilightStart = -.2f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float TwilightEnd = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float NightSkyMinimum = .6f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") FLinearColor NightFogColor = FLinearColor(.018f, .020f, .024f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") FLinearColor NightSceneTint = FLinearColor(.92f, .97f, 1.f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float NightSaturation = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float NightExposureBias = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float NightBlackLift = .012f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float PostProcessPriority = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonLux = 1.5f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") FLinearColor MoonColor = FLinearColor(.65f, .75f, 1.f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonElevationScale = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonYawOffset = 180.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonDiscDegrees = 1.1f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") FLinearColor MoonDiscScale = FLinearColor(.08f, .08f, .08f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") bool MoonShadows = false;
    // Sky-only horizon/halo; does not brighten the ground or undo fog silhouettes.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") TObjectPtr<UMaterialInterface> HorizonMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") FLinearColor NightHorizonColor = FLinearColor(.025f, .030f, .040f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float HorizonWidth = .12f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonHaloDegrees = 2.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") FLinearColor MoonHaloColor = FLinearColor(.025f, .03f, .04f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") TObjectPtr<UStaticMesh> DustPlane;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") TObjectPtr<UMaterialInterface> MoteMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") TObjectPtr<UMaterialInterface> SheetMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") int32 Seed = 2042;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust", meta=(ClampMin="0", ClampMax="512")) int32 MoteCount = 360;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustDensity = FVector(.6, .8, 1.);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustOpacity = FVector(.8, .9, 1.);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustSpeed = FVector(100, 240, 900);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector WindDirection = FVector(1, .35, -.08);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector VolumeHalfExtent = FVector(500, 650, 400);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float VolumeForward = 700.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector2D MoteSize = FVector2D(3, 26);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float MoteFraction = .04f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float MoteDiameter = .8f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float StreakWidthScale = .28f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float StreakOpacityScale = .18f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SpeckOpacityScale = .12f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector2D ParticleSizeVariation = FVector2D(.75, 1.2);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float StreakReferenceSpeed = 900.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float StreakMinimumLengthScale = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector GroundDustOpacity = FVector(.24, .34, .48);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector GroundSheetHeights = FVector(25, 65, 115);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float GroundDustHeight = 150.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float GroundSheetSize = 2400.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float GroundTraceDistance = 10000.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector SheetDistances = FVector(400, 850, 1400);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetSize = 4200.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetOpacityScale = .14f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetDriftFraction = .25f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float BoundsFadeFraction = .15f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float DensityFeather = .1f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float InteriorFadeSpeed = 4.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float NearFadeStart = 80.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float NearFadeEnd = 200.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float DepthFadeDistance = 120.f;
    // UV wind speed multipliers; unity preserves the projected wind direction.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector2D NoisePan = FVector2D(1, 1);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FLinearColor DayDustColor = FLinearColor(.42f, .31f, .19f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FLinearColor NightDustColor = FLinearColor(.045f, .050f, .060f);
};
