#include "DustfallSurvivalBridge.h"
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
    if (Object) if (const FStructProperty* P = FindFProperty<FStructProperty>(Object->GetClass(), Name))
        if (P->Struct == TBaseStructure<FVector>::Get()) return *P->ContainerPtrToValuePtr<FVector>(Object);
    Missing(Object,Name); return FVector::ZeroVector;
}
void SetVector(UObject* Object, FName Name, FVector Value)
{
    if (Object) if (FStructProperty* P = FindFProperty<FStructProperty>(Object->GetClass(), Name))
        if (P->Struct == TBaseStructure<FVector>::Get()) { *P->ContainerPtrToValuePtr<FVector>(Object) = Value; return; }
    Missing(Object,Name);
}

UObject* ObjectValue(const UObject* Object, FName Name)
{
    if (Object) if (const auto* P=FindFProperty<FObjectPropertyBase>(Object->GetClass(),Name)) return P->GetObjectPropertyValue_InContainer(Object);
    Missing(Object,Name); return nullptr;
}
FString StringValue(const UObject* Object,FName Name,const FString& Fallback)
{
    if (Object) if (const auto* P=FindFProperty<FStrProperty>(Object->GetClass(),Name)) return P->GetPropertyValue_InContainer(Object);
    Missing(Object,Name); return Fallback;
}
void Call(UObject* Object,FName Name)
{
    if (Object) if (UFunction* F=Object->FindFunction(Name)) { Object->ProcessEvent(F,nullptr); return; }
    Missing(Object,Name);
}
AActor* FindDirector(UWorld* World)
{
    for (TActorIterator<AActor> It(World); It; ++It)
        if (It->GetClass()->FindPropertyByName(TEXT("CloneGeneration")) && It->GetClass()->FindPropertyByName(TEXT("CrateScrap"))) return *It;
    return nullptr;
}
}
