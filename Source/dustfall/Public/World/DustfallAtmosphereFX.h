#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DustfallAtmosphereFX.generated.h"

class UDustfallAtmosphereTuning;
class UDirectionalLightComponent;
class UInstancedStaticMeshComponent;
class UPostProcessComponent;
class UMaterialInstanceDynamic;
class UPackage;

/** Runtime presentation consumer only. Never changes survival state. */
UCLASS()
class DUSTFALL_API ADustfallAtmosphereFX : public AActor
{
    GENERATED_BODY()
public:
    ADustfallAtmosphereFX();
    /** Editor capture only: temporary string assignment without Modify/PostEditChange,
     * so the authored survival package retains its dirty state. Caller MUST restore. */
    UFUNCTION(BlueprintCallable, Category="Atmosphere|Editor", meta=(DevelopmentOnly))
    static bool SetCaptureSaveSlot(AActor* Director, const FString& Slot);

    /** Exact actor/component (and optionally folder) packages for scoped editor saving. */
    UFUNCTION(BlueprintCallable, Category="Atmosphere|Editor", meta=(DevelopmentOnly))
    TArray<UPackage*> GetAuthoringPackages(bool bIncludeFolders = false) const;

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UDustfallAtmosphereTuning> Tuning;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UDirectionalLightComponent> Moon;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UInstancedStaticMeshComponent> Motes;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UInstancedStaticMeshComponent> Sheets;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UInstancedStaticMeshComponent> GroundSheets;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Atmosphere") TObjectPtr<UPostProcessComponent> NightPostProcess;
private:
    void FindDirectors();
    UPROPERTY(Transient) TObjectPtr<AActor> Environment;
    UPROPERTY(Transient) TObjectPtr<AActor> Survival;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> HorizonMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MoteMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SheetMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> GroundMID;
    UPROPERTY(Transient) TObjectPtr<UClass> LandscapeClass;
    TArray<FVector> Positions;
    TArray<float> Variations;
    TArray<FVector2D> Sizes;
    TArray<bool> Specks;
    float InteriorVisibility = 0.f;
    FVector SheetDrift = FVector::ZeroVector;
};
