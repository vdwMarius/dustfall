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
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector FogMaxOpacity = FVector(.82, .86, .51);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector FogStartDistance = FVector(0, 0, 0);
    // Near volumetric transmission multiplies the analytic cap; see FX.cpp.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector VolumetricExtinction = FVector(.2, .3, .96);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector VolumetricFogDistance = FVector(6000, 4000, 1000);
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
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust", meta=(ClampMin="0", ClampMax="256")) int32 MoteCount = 200;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustDensity = FVector(.4, .65, 1.);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustOpacity = FVector(.5, .7, 1.);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustSpeed = FVector(100, 240, 900);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector WindDirection = FVector(1, .35, -.08);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector VolumeHalfExtent = FVector(500, 650, 400);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float VolumeForward = 700.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector2D MoteSize = FVector2D(4, 40);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float MoteFraction = .35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float MoteDiameter = 5.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector SheetDistances = FVector(400, 850, 1400);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetSize = 4200.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetOpacityScale = .22f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetDriftFraction = .25f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float BoundsFadeFraction = .15f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float DensityFeather = .1f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float InteriorFadeSpeed = 4.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float NearFadeStart = 80.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float NearFadeEnd = 200.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float DepthFadeDistance = 120.f;
    // UV wind speed multipliers; unity preserves the projected wind direction.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector2D NoisePan = FVector2D(1, 1);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FLinearColor DayDustColor = FLinearColor(.65f, .48f, .30f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FLinearColor NightDustColor = FLinearColor(.045f, .050f, .060f);
};
