#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Systems/DustfallSurvivalTuning.h"
#include "Systems/DustfallSurvivalRules.h"
#include "DustfallSurvivalDirector.generated.h"

class USoundBase;
class USaveGame;
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FDustfallCloneRespawned);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDustfallSuitWarning, FName, Kind);

/** Native suit authority. Reparent BP_SurvivalDirector only in a dedicated editor task. */
UCLASS(Blueprintable)
class DUSTFALL_API ADustfallSurvivalDirector : public AActor
{
    GENERATED_BODY()
public:
    ADustfallSurvivalDirector();
    virtual void Tick(float DeltaSeconds) override;

    // Declare before the matching properties: UHT permits the legacy output names
    // in this order. The definition uses Out* names to avoid C++ member shadowing.
    UFUNCTION(BlueprintCallable, BlueprintPure = false, Category = "Dustfall|Survival")
    void GetSuitState(double& Oxygen, double& Power, double& Integrity, double& Stamina, int32& CloneGeneration) const;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    double Oxygen = 100.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    double Power = 100.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    double Integrity = 100.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    double Stamina = 100.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    int32 CloneGeneration = 1;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    int32 CarriedScrap = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    int32 CrateScrap = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    bool CrateActive = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    bool InHabitat = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    bool DeathInProgress = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    bool SprintExhausted = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    bool SprintRequested = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    bool LastSaveSucceeded = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    FVector CrateLocation = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    FVector SavedLocation = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    FVector HabitatCenter = FVector(0, 0, 285);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    FVector HabitatHalfExtent = FVector(475, 325, 185);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    FVector CloneSpawn = FVector(-120, 0, 198);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    double SaveElapsed = 0.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    double WarningElapsed = 8.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    int32 OxygenWarningCount = 0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    double StaminaBeforeTick = 0.0;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    FString SaveSlotName = TEXT("Dustfall_Phase3");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    TObjectPtr<UDustfallSurvivalTuning> Tuning = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    TObjectPtr<UObject> LegacyTuning = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    TObjectPtr<AActor> EnvironmentDirector = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Survival")
    TObjectPtr<AActor> RecoveryActor = nullptr;

    UPROPERTY(BlueprintAssignable, Category = "Dustfall|Survival")
    FDustfallCloneRespawned OnCloneRespawned;

    UPROPERTY(BlueprintAssignable, Category = "Dustfall|Survival")
    FDustfallSuitWarning OnSuitWarning;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Dustfall|Presentation")
    TSoftObjectPtr<USoundBase> OxygenWarningSound;

    UFUNCTION(BlueprintCallable, Category = "Dustfall|Survival")
    void RefreshRecoveryCache();
    UFUNCTION(BlueprintCallable, Category = "Dustfall|Survival")
    void SaveProgress();
    UFUNCTION(BlueprintCallable, Category = "Dustfall|Survival")
    void LoadProgress();
    UFUNCTION(BlueprintCallable, Category = "Dustfall|Survival")
    void RecoverCrate();
    UFUNCTION(BlueprintCallable, Category = "Dustfall|Survival")
    void RespawnClone();

    /** Rate names: OxygenDrain/Refill, PowerDrain/Refill, StaminaDrain/Refill, IntegrityDrain/Refill. */
    UFUNCTION(BlueprintCallable, Category = "Dustfall|Survival")
    void SetSuitModifier(FName Rate, FName Source, float Multiplier);
    UFUNCTION(BlueprintCallable, Category = "Dustfall|Survival")
    void ClearSuitModifier(FName Rate, FName Source);
    /** Resource names: Oxygen, Power, Integrity, Stamina. Set a source to zero to clear its bonus. */
    UFUNCTION(BlueprintCallable, Category = "Dustfall|Survival")
    void SetCapacityBonus(FName Resource, FName Source, double Bonus);

protected:
    virtual void BeginPlay() override;

private:
    // A reflected soft reference also keeps the legacy save class discoverable by the cooker.
    UPROPERTY()
    TSoftClassPtr<USaveGame> LegacySaveClass;

    double TuningValue(FName Name) const;
    double Maximum(FName Resource) const;
    double Rate(FName Name, double Base) const;
    TMap<FName, FDustfallModifierStack> RateModifiers;
    TMap<FName, TMap<FName, double>> CapacityBonuses;
};
