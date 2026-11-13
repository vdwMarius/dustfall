#pragma once
#include "CoreMinimal.h"
namespace DustfallSurvivalBridge
{
    double Number(const UObject* Object, FName Name);
    void SetNumber(UObject* Object, FName Name, double Value);
    FVector VectorValue(const UObject* Object, FName Name);
    void SetVector(UObject* Object, FName Name, FVector Value);
    UObject* ObjectValue(const UObject* Object, FName Name);
    FString StringValue(const UObject* Object, FName Name, const FString& Fallback);
    void Call(UObject* Object, FName Name);
    AActor* FindDirector(UWorld* World);
}
