#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DustfallSurvivalLibrary.generated.h"

/** Shared suit rules. Blueprint data assets supply rates and limits. */
UCLASS()
class DUSTFALL_API UDustfallSurvivalLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    /** Integrates elapsed seconds, clamps to capacity, rejects nonfinite input. */
    UFUNCTION(BlueprintPure, Category = "Dustfall|Survival")
    static double IntegrateResource(double Current, double RatePerSecond, double DeltaSeconds, double Maximum);

    /** Uses the same boundary rule for sanctuary refill and future consumers. */
    UFUNCTION(BlueprintPure, Category = "Dustfall|Habitat")
    static bool IsWithinHabitat(FVector Point, FVector Origin, FVector HalfExtent);

    /** A depletion tick stays exhausted while recovering toward the threshold. */
    UFUNCTION(BlueprintPure, Category = "Dustfall|Survival")
    static bool UpdateSprintExhaustion(double CurrentStamina, double StaminaBeforeTick,
        bool bWasExhausted, double RecoveryThreshold);
};
