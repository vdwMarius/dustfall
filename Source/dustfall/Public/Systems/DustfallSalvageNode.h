#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DustfallSalvageNode.generated.h"

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
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    void SetClaimed(bool bValue);
private:
    friend class ADustfallExplorationDirector;
    TWeakObjectPtr<class ADustfallExplorationDirector> RegisteredDirector;
};

