#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Systems/DustfallModifierStack.h"
#include "Systems/DustfallExplorationTuning.h"
#include "Systems/DustfallExplorationSave.h"
#include "Systems/DustfallSalvageNode.h"
#include "DustfallExplorationDirector.generated.h"

/** Exploration inventory owns typed payload; existing suit director owns survival. */
UCLASS()
class DUSTFALL_API ADustfallExplorationDirector : public AActor
{
    GENERATED_BODY()
public:
    ADustfallExplorationDirector();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<class UDustfallInputConfig> InputConfig;
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
    UPROPERTY(BlueprintReadOnly) FString ManualSaveLoadMessage;
    UPROPERTY(BlueprintReadOnly) FString AutosaveMessage;
    UPROPERTY(BlueprintReadOnly) FString ActiveLore;
    UPROPERTY(BlueprintReadOnly) float ScannerRemaining = 0;
    UFUNCTION(BlueprintCallable) void SetStrainModifier(FName Source, float Multiplier);
    UFUNCTION(BlueprintCallable) void ClearStrainModifier(FName Source);
    void RegisterNode(ADustfallSalvageNode* Node);
    void UnregisterNode(ADustfallSalvageNode* Node);
    const TArray<TWeakObjectPtr<ADustfallSalvageNode>>& GetNodes() const { return Nodes; }
    const FDustfallActiveSymptom* ActiveSymptom() const { return IsSymptomActive() ? &CurrentSymptom : nullptr; }
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
    void UpdateInputBindings();
    void RemoveInputBindings();
    TWeakObjectPtr<class UEnhancedInputComponent> BoundInputComponent;
    TWeakObjectPtr<class UEnhancedInputLocalPlayerSubsystem> BoundInputSubsystem;
    TWeakObjectPtr<class UInputMappingContext> BoundMappingContext;
    TWeakObjectPtr<class UDustfallInputConfig> BoundInputConfig;
    TWeakObjectPtr<class APawn> BoundInputPawn;
    TArray<uint32> InputBindingHandles;
    uint8 PendingInputActions = 0;
    bool bAddedInputContext = false;
    bool bLoggedInputPath = false;
    UPROPERTY(Transient) TObjectPtr<AActor> EnvironmentDirector;
    TArray<TWeakObjectPtr<ADustfallSalvageNode>> Nodes;
    TArray<FDustfallBeaconRecord> BeaconRecords;
    FDustfallModifierStack StrainModifiers;
    FRandomStream SymptomRandom;
    FDustfallActiveSymptom CurrentSymptom;
    void PickSymptom();
    float PrivateStrain = 0;
    float SymptomIntensity = 1;
    float SymptomRemaining = 0;
    float SymptomElapsed = 0;
    float ScannerCooldownRemaining = 0;
    float SaveElapsed = 0;
    float ManualMessageRemaining = 0;
    float AutosaveMessageRemaining = 0;
    FDateTime LastSavedAt;
    FDateTime LastLoadedAt;
    float Age = 0;
    bool bInitialized = false;
    bool bPreviousCrateActive = false;
    int32 LastClone = 1;
    void SynchronizeSurvival();
    void RefreshNodes();
    void CallSurvival(FName FunctionName);
};

