#pragma once
#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "DustfallExplorationSave.generated.h"

USTRUCT(BlueprintType)
struct DUSTFALL_API FDustfallBeaconRecord
{
    GENERATED_BODY()
    UPROPERTY(SaveGame, BlueprintReadOnly) FGuid Id;
    UPROPERTY(SaveGame, BlueprintReadOnly) FVector Location = FVector::ZeroVector;
};

UCLASS()
class DUSTFALL_API UDustfallExplorationSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) int32 Version = 3;
    UPROPERTY(SaveGame) FDateTime SavedAt;
    UPROPERTY(SaveGame) TMap<FName, int32> Inventory;
    UPROPERTY(SaveGame) TMap<FName, int32> RecoveryInventory;
    UPROPERTY(SaveGame) TSet<FName> ClaimedNodes;
    UPROPERTY(SaveGame) TMap<FName, FString> Journal;
    // Legacy schema 2 positions must remain readable.
    UPROPERTY(SaveGame) TArray<FVector> Beacons;
    UPROPERTY(SaveGame) TArray<FDustfallBeaconRecord> BeaconRecords;

    UPROPERTY(SaveGame) float SymptomIntensity = 1;
    UPROPERTY(SaveGame) FVector PlayerLocation = FVector::ZeroVector;
    UPROPERTY(SaveGame) FVector CrateLocation = FVector::ZeroVector;
    UPROPERTY(SaveGame) bool bCrateActive = false;
    UPROPERTY(SaveGame) int32 CloneGeneration = 1;
    UPROPERTY(SaveGame) double Oxygen = 100;
    UPROPERTY(SaveGame) double Power = 100;
    UPROPERTY(SaveGame) double Integrity = 100;
    UPROPERTY(SaveGame) double Stamina = 100;
    /** Validates first; on failure neither input nor output changes. No file/session access. */
    static bool ValidateAndMigrate(const UDustfallExplorationSave& Input, UDustfallExplorationSave& Output);
private:
    friend class ADustfallExplorationDirector;
    UPROPERTY(SaveGame) float PrivateStrain = 0;
};

