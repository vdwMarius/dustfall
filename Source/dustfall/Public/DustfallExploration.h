#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "GameFramework/HUD.h"
#include "GameFramework/SaveGame.h"
#include "DustfallExploration.generated.h"

UCLASS(BlueprintType)
class DUSTFALL_API UDustfallExplorationTuning : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 InventoryCapacity = 80;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float InteractionRange = 275;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ScannerRange = 14000;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ScannerPowerCost = 2;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ScannerDuration = 7;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float ScannerCooldown = 8;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float OutsideStrainPerSecond = .035f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float StormStrainPerSecond = .045f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float HomeStrainRecoveryPerSecond = .12f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float SymptomThreshold = 18;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float SymptomInterval = 75;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 MaximumBeacons = 6;
};

/** Stable identity is authored, never derived from runtime actor names. */
UCLASS()
class DUSTFALL_API ADustfallSalvageNode : public AActor
{
    GENERATED_BODY()
public:
    ADustfallSalvageNode();
    virtual void BeginPlay() override;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UStaticMeshComponent> Mesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<class UTextRenderComponent> Label;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName StableId;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName ItemId = "Scrap";
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Quantity = 3;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString DisplayName = "SEALED SALVAGE";
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(MultiLine=true)) FString LoreText;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float LoreStrain = 0;
    UPROPERTY(BlueprintReadOnly) bool bClaimed = false;
    void SetClaimed(bool bValue);
};

UCLASS()
class DUSTFALL_API UDustfallExplorationSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY(SaveGame) int32 Version = 2;
    UPROPERTY(SaveGame) TMap<FName, int32> Inventory;
    UPROPERTY(SaveGame) TMap<FName, int32> RecoveryInventory;
    UPROPERTY(SaveGame) TSet<FName> ClaimedNodes;
    UPROPERTY(SaveGame) TMap<FName, FString> Journal;
    UPROPERTY(SaveGame) TArray<FVector> Beacons;
    UPROPERTY(SaveGame) float PrivateStrain = 0;
    UPROPERTY(SaveGame) float SymptomIntensity = 1;
    UPROPERTY(SaveGame) FVector PlayerLocation = FVector::ZeroVector;
    UPROPERTY(SaveGame) FVector CrateLocation = FVector::ZeroVector;
    UPROPERTY(SaveGame) bool bCrateActive = false;
    UPROPERTY(SaveGame) int32 CloneGeneration = 1;
    UPROPERTY(SaveGame) double Oxygen = 100;
    UPROPERTY(SaveGame) double Power = 100;
    UPROPERTY(SaveGame) double Integrity = 100;
    UPROPERTY(SaveGame) double Stamina = 100;
};

/** Exploration inventory owns typed payload; existing suit director owns survival. */
UCLASS()
class DUSTFALL_API ADustfallExplorationDirector : public AActor
{
    GENERATED_BODY()
public:
    ADustfallExplorationDirector();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(VisibleDefaultsOnly) TObjectPtr<class UStaticMesh> BeaconMesh;
    UPROPERTY(VisibleDefaultsOnly) TObjectPtr<class UMaterialInterface> BeaconMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<UDustfallExplorationTuning> Tuning;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TObjectPtr<AActor> SurvivalDirector;
    UPROPERTY(BlueprintReadOnly) TMap<FName, int32> Inventory;
    UPROPERTY(BlueprintReadOnly) TMap<FName, int32> RecoveryInventory;
    UPROPERTY(BlueprintReadOnly) TSet<FName> ClaimedNodes;
    UPROPERTY(BlueprintReadOnly) TMap<FName, FString> Journal;
    UPROPERTY(BlueprintReadOnly) TArray<FVector> Beacons;
    UPROPERTY(BlueprintReadOnly) bool bInventoryOpen = false;
    UPROPERTY(BlueprintReadOnly) bool bJournalOpen = false;
    UPROPERTY(BlueprintReadOnly) bool bLastSaveSucceeded = false;
    UPROPERTY(BlueprintReadOnly) FString StatusMessage;
    UPROPERTY(BlueprintReadOnly) FString ActiveLore;
    UPROPERTY(BlueprintReadOnly) float ScannerRemaining = 0;
    UFUNCTION(BlueprintCallable) bool AddItem(FName ItemId, int32 Quantity);
    UFUNCTION(BlueprintCallable) bool Interact();
    UFUNCTION(BlueprintCallable) bool PulseScanner();
    UFUNCTION(BlueprintCallable) bool PlaceBeacon();
    UFUNCTION(BlueprintCallable) bool RecoverInventory();
    UFUNCTION(BlueprintCallable) bool SaveExploration();
    UFUNCTION(BlueprintCallable) bool LoadExploration();
    UFUNCTION(BlueprintCallable) void SetSymptomIntensity(float Value);
    UFUNCTION(BlueprintPure) int32 InventoryCount() const;
    UFUNCTION(BlueprintPure) FString SaveSlot() const;
    UFUNCTION(BlueprintPure) float GetSymptomIntensity() const { return SymptomIntensity; }
    UFUNCTION(BlueprintPure) bool IsSymptomActive() const { return SymptomRemaining > 0; }
    UFUNCTION(BlueprintPure) double SuitValue(FName Name) const;
    UFUNCTION(BlueprintPure) FVector HomeLocation() const;
    ADustfallSalvageNode* NearestNode() const;
    bool HasRecoveredPayload() const { return RecoveryInventory.Num() > 0; }
    static void MergePayload(TMap<FName, int32>& Target, const TMap<FName, int32>& Source);
private:
    UPROPERTY(Transient) TObjectPtr<AActor> EnvironmentDirector;
    float PrivateStrain = 0;
    float SymptomIntensity = 1;
    float SymptomRemaining = 0;
    float SymptomElapsed = 0;
    float ScannerCooldownRemaining = 0;
    float SaveElapsed = 0;
    float Age = 0;
    bool bInitialized = false;
    bool bPreviousCrateActive = false;
    int32 LastClone = 1;
    void SynchronizeSurvival();
    void RefreshNodes();
    void CallSurvival(FName FunctionName);
};

UCLASS()
class DUSTFALL_API ADustfallExplorationHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};
