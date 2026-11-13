#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "DustfallInputConfig.generated.h"

class UInputAction;
class UInputMappingContext;

/** Content-owned exploration bindings; template movement and airlock input remain independent. */
UCLASS(BlueprintType)
class DUSTFALL_API UDustfallInputConfig : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputMappingContext> MappingContext;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") int32 MappingPriority = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputAction> Interact;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputAction> Scanner;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputAction> Inventory;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputAction> Journal;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputAction> Beacon;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputAction> QuickSave;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputAction> QuickLoad;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Input") TObjectPtr<UInputAction> ToggleSymptoms;
};
