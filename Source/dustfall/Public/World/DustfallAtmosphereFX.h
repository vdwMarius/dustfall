#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DustfallAtmosphereFX.generated.h"

class UDustfallAtmosphereTuning;
class UDirectionalLightComponent;
class UInstancedStaticMeshComponent;
class UPostProcessComponent;
class UMaterialInstanceDynamic;

/** Presentation consumer only. Never changes the environment or survival state. */
UCLASS()
class DUSTFALL_API ADustfallAtmosphereFX : public AActor
{
    GENERATED_BODY()
public:
    ADustfallAtmosphereFX();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UDustfallAtmosphereTuning> Tuning;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UDirectionalLightComponent> Moon;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UInstancedStaticMeshComponent> Motes;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UInstancedStaticMeshComponent> Sheets;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UPostProcessComponent> NightPostProcess;
private:
    void FindDirectors();
    UPROPERTY(Transient) TObjectPtr<AActor> Environment;
    UPROPERTY(Transient) TObjectPtr<AActor> Survival;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MoteMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SheetMID;
    TArray<FVector> Positions;
    TArray<float> Variations;
    TArray<FVector2D> Sizes;
    FLinearColor DayDirectionalFogColor = FLinearColor::Black;
    float InteriorVisibility = 0.f;
    FVector SheetDrift = FVector::ZeroVector;
};
