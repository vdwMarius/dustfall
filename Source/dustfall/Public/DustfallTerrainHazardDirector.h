#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DustfallTerrainHazardDirector.generated.h"

/** Collision-driven falling damage; saves a recoverable cache on the last safe rim. */
UCLASS()
class DUSTFALL_API ADustfallTerrainHazardDirector : public AActor
{
    GENERATED_BODY()
public:
    ADustfallTerrainHazardDirector();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<AActor> SurvivalDirector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float SafeImpactSpeed = 1050;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float DamagePerExcessSpeed = .065f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float KillHeight = -20000;
    UPROPERTY(BlueprintReadOnly) FVector LastSafeLocation;
    UPROPERTY(BlueprintReadOnly) float LastImpactDamage = 0;
private:
    float MaximumFallSpeed = 0;
    bool bWasFalling = false;
    bool bRelocateCache = false;
    int32 LastClone = 1;
};
