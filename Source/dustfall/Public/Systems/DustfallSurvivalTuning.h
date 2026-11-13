#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "DustfallSurvivalTuning.generated.h"

/** Native BP_SurvivalData equivalent; defaults match build_phase3_survival.py. */
UCLASS(BlueprintType)
class DUSTFALL_API UDustfallSurvivalTuning : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double MaxOxygen = 100.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double MaxPower = 100.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double MaxIntegrity = 100.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double MaxStamina = 100.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double OxygenDrainPerSecond = 0.12;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double OxygenRefillPerSecond = 8.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double PowerDrainPerSecond = 0.04;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double PowerRefillPerSecond = 5.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double StaminaDrainPerSecond = 18.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double StaminaRefillPerSecond = 12.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double StormIntegrityDrainPerSecond = 0.015;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double WalkSpeed = 500.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double SprintSpeed = 750.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double ExhaustedSpeed = 300.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double SaveIntervalSeconds = 30.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double RecoveryDistance = 250.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double OxygenWarningThreshold = 20.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double OxygenWarningCooldown = 8.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double StaminaRecoveryThreshold = 25.0;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Survival")
    double SprintVelocityThreshold = 550.0;

    // Presentation values previously authored directly into the Blueprint graph.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Presentation")
    double OxygenWarningVolume = 0.65;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Dustfall|Recovery")
    FVector RecoveryOffset = FVector(0, 0, -65);
};
