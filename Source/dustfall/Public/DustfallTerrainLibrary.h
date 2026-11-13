#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "DustfallTerrainLibrary.generated.h"

/** Editor authoring utility. Packaged games use the saved Landscape, never this tool. */
UCLASS()
class DUSTFALL_API UDustfallTerrainLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Reads/writes an exact baseline heightfield before applying deterministic relief.
     * Protection discs store radius in Z. Route endpoints are consecutive pairs.
     * Returns measured extent/height information or an error; refuses PIE. */
    UFUNCTION(BlueprintCallable, Category="Dustfall|Editor")
    static FString AuthorHostileRelief(AActor* LandscapeActor, const FString& BaselineFile,
        const TArray<FVector>& ProtectionDiscs, const TArray<FVector>& RouteEndpoints);
};
