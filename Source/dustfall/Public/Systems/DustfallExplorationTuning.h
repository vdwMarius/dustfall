#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "DustfallExplorationTuning.generated.h"

UENUM(BlueprintType)
enum class EDustfallSymptomKind : uint8 { HudText, ScannerEcho };

USTRUCT(BlueprintType)
struct DUSTFALL_API FDustfallSymptomDefinition
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) EDustfallSymptomKind Kind = EDustfallSymptomKind::HudText;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FString Text;
    // Zero inherits the tuning asset's default symptom duration.
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Duration = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float MinimumStrain = 18;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float Weight = 1;
};

/** Presentation only: the HUD receives no eligibility or internal Strain data. */
struct DUSTFALL_API FDustfallActiveSymptom
{
    EDustfallSymptomKind Kind = EDustfallSymptomKind::HudText;
    FString Text;
};

UCLASS(BlueprintType)
class DUSTFALL_API UDustfallExplorationTuning : public UDataAsset
{
    GENERATED_BODY()
public:
    UDustfallExplorationTuning();
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 InventoryCapacity = 80;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float InteractionRange = 275;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ScannerRange = 14000;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ScannerPowerCost = 2;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ScannerDuration = 7;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ScannerCooldown = 8;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float OutsideStrainPerSecond = .035f;
    // Deprecated additive rate retained for existing asset deserialization.
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float StormStrainPerSecond = .045f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float HomeStrainRecoveryPerSecond = .12f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float SymptomThreshold = 18;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float SymptomInterval = 75;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 MaximumBeacons = 6;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float LowOxygenStrainThreshold = 20;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float LowIntegrityStrainThreshold = 30;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float DeathStrainGain = 4;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float SymptomDuration = 3;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float BeaconRecoverRange = 300;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float CrateRecoverRange = 250;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float AutosaveInterval = 30;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="4.0")) float ManualSaveLoadMessageDuration = 4.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.0")) float AutosaveMessageDuration = 2.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float FirstLoadDelay = .35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float StormStrainMultiplier = .045f / .035f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float LowSuitStrainMultiplier = (.035f + .08f) / .035f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float HudLowOxygenThreshold = 20;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float HudCriticalIntegrityThreshold = 20;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float InteractionTraceHeight = 35;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 BeaconPowerCellCost = 1;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FVector ScannerEchoOffset = FVector(6500,1300,0);
    UPROPERTY(EditAnywhere, BlueprintReadOnly) int32 SymptomSeed = 2042;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) TArray<FDustfallSymptomDefinition> Symptoms;
};

