#include "DustfallSurvivalBridge.h"
#include "Systems/DustfallSurvivalDirector.h"
#include "UObject/UnrealType.h"
#include "EngineUtils.h"
namespace DustfallSurvivalBridge
{
static void Missing(const UObject* Object, FName Name)
{
    if (!Object) return;
    static TSet<FString> Warned;
    const FString Key = Object->GetClass()->GetPathName() + TEXT(":") + Name.ToString();
    if (!Warned.Contains(Key)) { Warned.Add(Key); UE_LOG(LogTemp, Warning, TEXT("Survival bridge missing or incompatible member %s"), *Key); }
}
double Number(const UObject* Object, FName Name)
{
    if (!Object) return 0;
    if (const auto* Director = Cast<ADustfallSurvivalDirector>(Object))
    {
        if (Name == TEXT("Oxygen")) return Director->Oxygen;
        if (Name == TEXT("Power")) return Director->Power;
        if (Name == TEXT("Integrity")) return Director->Integrity;
        if (Name == TEXT("Stamina")) return Director->Stamina;
        if (Name == TEXT("CloneGeneration")) return Director->CloneGeneration;
        if (Name == TEXT("CarriedScrap")) return Director->CarriedScrap;
        if (Name == TEXT("CrateScrap")) return Director->CrateScrap;
        if (Name == TEXT("CrateActive")) return Director->CrateActive;
        if (Name == TEXT("InHabitat")) return Director->InHabitat;
        if (Name == TEXT("DeathInProgress")) return Director->DeathInProgress;
        if (Name == TEXT("SprintExhausted")) return Director->SprintExhausted;
        if (Name == TEXT("SprintRequested")) return Director->SprintRequested;
        if (Name == TEXT("SaveElapsed")) return Director->SaveElapsed;
        if (Name == TEXT("LastSaveSucceeded")) return Director->LastSaveSucceeded;
        if (Name == TEXT("WarningElapsed")) return Director->WarningElapsed;
        if (Name == TEXT("OxygenWarningCount")) return Director->OxygenWarningCount;
        if (Name == TEXT("StaminaBeforeTick")) return Director->StaminaBeforeTick;
    }
    const FProperty* Property = Object->GetClass()->FindPropertyByName(Name);
    if (const FNumericProperty* Numeric = CastField<FNumericProperty>(Property))
    {
        const void* Address = Numeric->ContainerPtrToValuePtr<void>(Object);
        return Numeric->IsInteger() ? double(Numeric->GetSignedIntPropertyValue(Address)) : Numeric->GetFloatingPointPropertyValue(Address);
    }
    if (const FBoolProperty* Boolean = CastField<FBoolProperty>(Property)) return Boolean->GetPropertyValue_InContainer(Object) ? 1 : 0;
    Missing(Object,Name); return 0;
}
void SetNumber(UObject* Object, FName Name, double Value)
{
    if (!Object) return;
    if (auto* Director = Cast<ADustfallSurvivalDirector>(Object))
    {
        if (Name == TEXT("Oxygen")) { Director->Oxygen = Value; return; }
        if (Name == TEXT("Power")) { Director->Power = Value; return; }
        if (Name == TEXT("Integrity")) { Director->Integrity = Value; return; }
        if (Name == TEXT("Stamina")) { Director->Stamina = Value; return; }
        if (Name == TEXT("CloneGeneration")) { Director->CloneGeneration = int32(Value); return; }
        if (Name == TEXT("CarriedScrap")) { Director->CarriedScrap = int32(Value); return; }
        if (Name == TEXT("CrateScrap")) { Director->CrateScrap = int32(Value); return; }
        if (Name == TEXT("CrateActive")) { Director->CrateActive = Value != 0; return; }
        if (Name == TEXT("InHabitat")) { Director->InHabitat = Value != 0; return; }
        if (Name == TEXT("DeathInProgress")) { Director->DeathInProgress = Value != 0; return; }
        if (Name == TEXT("SprintExhausted")) { Director->SprintExhausted = Value != 0; return; }
        if (Name == TEXT("SprintRequested")) { Director->SprintRequested = Value != 0; return; }
        if (Name == TEXT("SaveElapsed")) { Director->SaveElapsed = Value; return; }
        if (Name == TEXT("LastSaveSucceeded")) { Director->LastSaveSucceeded = Value != 0; return; }
        if (Name == TEXT("WarningElapsed")) { Director->WarningElapsed = Value; return; }
        if (Name == TEXT("OxygenWarningCount")) { Director->OxygenWarningCount = int32(Value); return; }
        if (Name == TEXT("StaminaBeforeTick")) { Director->StaminaBeforeTick = Value; return; }
    }
    FProperty* Property = Object->GetClass()->FindPropertyByName(Name);
    if (FNumericProperty* Numeric = CastField<FNumericProperty>(Property))
    {
        void* Address = Numeric->ContainerPtrToValuePtr<void>(Object);
        if (Numeric->IsInteger()) Numeric->SetIntPropertyValue(Address, int64(Value));
        else Numeric->SetFloatingPointPropertyValue(Address, Value);
    }
    if (FBoolProperty* Boolean = CastField<FBoolProperty>(Property)) { Boolean->SetPropertyValue_InContainer(Object, Value != 0); return; }
    if (!CastField<FNumericProperty>(Property)) Missing(Object,Name);
}
FVector VectorValue(const UObject* Object, FName Name)
{
    if (const auto* Director = Cast<ADustfallSurvivalDirector>(Object))
    {
        if (Name == TEXT("CrateLocation")) return Director->CrateLocation;
        if (Name == TEXT("SavedLocation")) return Director->SavedLocation;
        if (Name == TEXT("HabitatCenter")) return Director->HabitatCenter;
        if (Name == TEXT("HabitatHalfExtent")) return Director->HabitatHalfExtent;
        if (Name == TEXT("CloneSpawn")) return Director->CloneSpawn;
    }
    if (Object) if (const FStructProperty* P = FindFProperty<FStructProperty>(Object->GetClass(), Name))
        if (P->Struct == TBaseStructure<FVector>::Get()) return *P->ContainerPtrToValuePtr<FVector>(Object);
    Missing(Object,Name); return FVector::ZeroVector;
}
void SetVector(UObject* Object, FName Name, FVector Value)
{
    if (auto* Director = Cast<ADustfallSurvivalDirector>(Object))
    {
        if (Name == TEXT("CrateLocation")) { Director->CrateLocation = Value; return; }
        if (Name == TEXT("SavedLocation")) { Director->SavedLocation = Value; return; }
        if (Name == TEXT("HabitatCenter")) { Director->HabitatCenter = Value; return; }
        if (Name == TEXT("HabitatHalfExtent")) { Director->HabitatHalfExtent = Value; return; }
        if (Name == TEXT("CloneSpawn")) { Director->CloneSpawn = Value; return; }
    }
    if (Object) if (FStructProperty* P = FindFProperty<FStructProperty>(Object->GetClass(), Name))
        if (P->Struct == TBaseStructure<FVector>::Get()) { *P->ContainerPtrToValuePtr<FVector>(Object) = Value; return; }
    Missing(Object,Name);
}

UObject* ObjectValue(const UObject* Object, FName Name)
{
    if (const auto* Director = Cast<ADustfallSurvivalDirector>(Object))
    {
        if (Name == TEXT("Tuning")) return Director->Tuning.Get();
        if (Name == TEXT("LegacyTuning")) return Director->LegacyTuning.Get();
        if (Name == TEXT("EnvironmentDirector")) return Director->EnvironmentDirector.Get();
        if (Name == TEXT("RecoveryActor")) return Director->RecoveryActor.Get();
    }
    if (Object) if (const auto* P=FindFProperty<FObjectPropertyBase>(Object->GetClass(),Name)) return P->GetObjectPropertyValue_InContainer(Object);
    Missing(Object,Name); return nullptr;
}
FString StringValue(const UObject* Object,FName Name,const FString& Fallback)
{
    if (const auto* Director = Cast<ADustfallSurvivalDirector>(Object))
    {
        if (Name == TEXT("SaveSlotName")) return Director->SaveSlotName;
    }
    if (Object) if (const auto* P=FindFProperty<FStrProperty>(Object->GetClass(),Name)) return P->GetPropertyValue_InContainer(Object);
    Missing(Object,Name); return Fallback;
}
void Call(UObject* Object,FName Name)
{
    if (auto* Director = Cast<ADustfallSurvivalDirector>(Object))
    {
        if (Name == TEXT("RefreshRecoveryCache")) { Director->RefreshRecoveryCache(); return; }
        if (Name == TEXT("SaveProgress")) { Director->SaveProgress(); return; }
        if (Name == TEXT("LoadProgress")) { Director->LoadProgress(); return; }
        if (Name == TEXT("RecoverCrate")) { Director->RecoverCrate(); return; }
        if (Name == TEXT("RespawnClone")) { Director->RespawnClone(); return; }
    }
    if (Object) if (UFunction* F=Object->FindFunction(Name)) { Object->ProcessEvent(F,nullptr); return; }
    Missing(Object,Name);
}
AActor* FindDirector(UWorld* World)
{
    if (!World) return nullptr;
    for (TActorIterator<ADustfallSurvivalDirector> It(World); It; ++It) return *It;
    for (TActorIterator<AActor> It(World); It; ++It)
        if (It->GetClass()->FindPropertyByName(TEXT("CloneGeneration")) && It->GetClass()->FindPropertyByName(TEXT("CrateScrap"))) return *It;
    return nullptr;
}
}
