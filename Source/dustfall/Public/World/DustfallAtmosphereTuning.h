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
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector FogMaxOpacity = FVector(.82, .88, .92);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector FogStartDistance = FVector(100, 75, 50);
    // Volumetric fog has no max-opacity cap. Zero prevents it erasing the far silhouette floor.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Fog") FVector VolumetricExtinction = FVector(0, 0, 0);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float TwilightStart = -.2f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float TwilightEnd = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float NightSkyMinimum = .08f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") FLinearColor NightFogColor = FLinearColor(.018f, .020f, .024f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") FLinearColor NightSceneTint = FLinearColor(.85f, .9f, 1.f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float NightExposureBias = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float NightBlackLift = .004f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Night") float PostProcessPriority = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonLux = .08f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") FLinearColor MoonColor = FLinearColor(.65f, .75f, 1.f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonElevationScale = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonYawOffset = 180.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") float MoonDiscDegrees = 1.5f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") FLinearColor MoonDiscScale = FLinearColor(8.f, 8.f, 8.f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Moon") bool MoonShadows = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") TObjectPtr<UStaticMesh> DustPlane;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") TObjectPtr<UMaterialInterface> MoteMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") TObjectPtr<UMaterialInterface> SheetMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") int32 Seed = 2042;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust", meta=(ClampMin="0", ClampMax="256")) int32 MoteCount = 96;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustDensity = FVector(.25, .5, 1.);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustOpacity = FVector(.10, .16, .26);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector DustSpeed = FVector(90, 180, 480);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector WindDirection = FVector(1, .35, -.08);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector VolumeHalfExtent = FVector(1100, 1000, 650);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float VolumeForward = 1150.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector2D MoteSize = FVector2D(2, 18);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float MoteFraction = .35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float MoteDiameter = 3.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector SheetDistances = FVector(400, 850, 1400);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetSize = 1000.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetOpacityScale = .35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float SheetDriftFraction = .25f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float BoundsFadeFraction = .15f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float DensityFeather = .1f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float InteriorFadeSpeed = 4.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float NearFadeStart = 80.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float NearFadeEnd = 200.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") float DepthFadeDistance = 120.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FVector2D NoisePan = FVector2D(.06, .025);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FLinearColor DayDustColor = FLinearColor(.25f, .17f, .10f);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Dust") FLinearColor NightDustColor = FLinearColor(.018f, .020f, .024f);
};
