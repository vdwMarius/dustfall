#include "Systems/DustfallSurvivalDirector.h"
#include "DustfallSurvivalBridge.h"
#include "DustfallSurvivalLibrary.h"
#include "Components/InputComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SpotLightComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SaveGame.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "UObject/UnrealType.h"

namespace
{
bool IsResource(FName Name)
{
    return Name == TEXT("Oxygen") || Name == TEXT("Power") || Name == TEXT("Integrity") || Name == TEXT("Stamina");
}
bool IsRate(FName Name)
{
    return Name == TEXT("OxygenDrain") || Name == TEXT("OxygenRefill")
        || Name == TEXT("PowerDrain") || Name == TEXT("PowerRefill")
        || Name == TEXT("StaminaDrain") || Name == TEXT("StaminaRefill")
        || Name == TEXT("IntegrityDrain") || Name == TEXT("IntegrityRefill");
}

// Validate the entire legacy schema before copying any state into the live session.
bool HasSaveSchema(const UObject* Save)
{
    if (!Save) return false;
    for (const TCHAR* Name : {TEXT("Oxygen"), TEXT("Power"), TEXT("Integrity"), TEXT("Stamina")})
    {
        const auto* P = FindFProperty<FNumericProperty>(Save->GetClass(), Name);
        if (!P || !P->IsFloatingPoint()) return false;
        const double Value = P->GetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(Save));
        if (!FMath::IsFinite(Value) || Value < 0.0) return false;
    }
    for (const TCHAR* Name : {TEXT("CloneGeneration"), TEXT("CarriedScrap"), TEXT("CrateScrap"), TEXT("SaveVersion")})
    {
        const auto* P = FindFProperty<FIntProperty>(Save->GetClass(), Name);
        if (!P || P->GetPropertyValue_InContainer(Save) < 0) return false;
    }
    if (!FindFProperty<FBoolProperty>(Save->GetClass(), TEXT("CrateActive"))) return false;
    for (const TCHAR* Name : {TEXT("CrateLocation"), TEXT("SavedLocation")})
    {
        const auto* P = FindFProperty<FStructProperty>(Save->GetClass(), Name);
        if (!P || P->Struct != TBaseStructure<FVector>::Get()
            || P->ContainerPtrToValuePtr<FVector>(Save)->ContainsNaN()) return false;
    }
    return true;
}
}

ADustfallSurvivalDirector::ADustfallSurvivalDirector()
{
    PrimaryActorTick.bCanEverTick = true;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    OxygenWarningSound = TSoftObjectPtr<USoundBase>(FSoftObjectPath(TEXT("/Game/Audio/Suit/S_OxygenWarning_Phase3.S_OxygenWarning_Phase3")));
    LegacySaveClass = TSoftClassPtr<USaveGame>(FSoftObjectPath(TEXT("/Game/Systems/BP_DustfallSaveGame.BP_DustfallSaveGame_C")));
    // Register every supported rate, including the zero-base integrity refill reserved for upgrades.
    for (const TCHAR* Name : {TEXT("OxygenDrain"), TEXT("OxygenRefill"), TEXT("PowerDrain"), TEXT("PowerRefill"),
        TEXT("StaminaDrain"), TEXT("StaminaRefill"), TEXT("IntegrityDrain"), TEXT("IntegrityRefill")})
        RateModifiers.Add(FName(Name));
}

void ADustfallSurvivalDirector::BeginPlay()
{
    Super::BeginPlay();
    if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
    {
        EnableInput(PC);
        if (InputComponent)
        {
            InputComponent->BindKey(EKeys::E, IE_Pressed, this, &ADustfallSurvivalDirector::RecoverCrate).bConsumeInput = false;
            InputComponent->BindKey(EKeys::F5, IE_Pressed, this, &ADustfallSurvivalDirector::SaveProgress).bConsumeInput = false;
            InputComponent->BindKey(EKeys::F9, IE_Pressed, this, &ADustfallSurvivalDirector::LoadProgress).bConsumeInput = false;
        }
    }
    LoadProgress();
    RefreshRecoveryCache();
}

double ADustfallSurvivalDirector::TuningValue(FName Name) const
{
    const UObject* Data = Tuning ? static_cast<const UObject*>(Tuning.Get()) : LegacyTuning.Get();
    if (Data)
    {
        if (const auto* P = FindFProperty<FNumericProperty>(Data->GetClass(), Name))
            if (P->IsFloatingPoint()) return P->GetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(Data));
    }
    // Also covers fields newly exposed on the native asset but absent from legacy tuning.
    return DustfallSurvivalBridge::Number(GetDefault<UDustfallSurvivalTuning>(), Name);
}

double ADustfallSurvivalDirector::Maximum(FName Resource) const
{
    const double Base = TuningValue(FName(*(TEXT("Max") + Resource.ToString())));
    if (const auto* Bonuses = CapacityBonuses.Find(Resource)) return FDustfallSurvivalRules::Capacity(Base, *Bonuses);
    return FDustfallSurvivalRules::Capacity(Base, TMap<FName, double>());
}

double ADustfallSurvivalDirector::Rate(FName Name, double Base) const
{
    const auto* Stack = RateModifiers.Find(Name);
    return Stack ? FDustfallSurvivalRules::EffectiveRate(Base, *Stack) : Base;
}

void ADustfallSurvivalDirector::SetSuitModifier(FName RateName, FName Source, float Multiplier)
{
    if (IsRate(RateName)) RateModifiers.FindOrAdd(RateName).Set(Source, Multiplier);
}
void ADustfallSurvivalDirector::ClearSuitModifier(FName RateName, FName Source)
{
    if (auto* Stack = RateModifiers.Find(RateName)) Stack->Clear(Source);
}
void ADustfallSurvivalDirector::SetCapacityBonus(FName Resource, FName Source, double Bonus)
{
    if (IsResource(Resource)) FDustfallSurvivalRules::SetCapacityBonus(CapacityBonuses.FindOrAdd(Resource), Source, Bonus);
}

void ADustfallSurvivalDirector::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    ACharacter* Character = UGameplayStatics::GetPlayerCharacter(this, 0);
    if (!Character) return;
    using Core = UDustfallSurvivalLibrary;
    InHabitat = Core::IsWithinHabitat(Character->GetActorLocation(), HabitatCenter, HabitatHalfExtent);
    Oxygen = Core::IntegrateResource(Oxygen, InHabitat
        ? Rate(TEXT("OxygenRefill"), TuningValue(TEXT("OxygenRefillPerSecond")))
        : -Rate(TEXT("OxygenDrain"), TuningValue(TEXT("OxygenDrainPerSecond"))), DeltaSeconds, Maximum(TEXT("Oxygen")));
    Power = Core::IntegrateResource(Power, InHabitat
        ? Rate(TEXT("PowerRefill"), TuningValue(TEXT("PowerRefillPerSecond")))
        : -Rate(TEXT("PowerDrain"), TuningValue(TEXT("PowerDrainPerSecond"))), DeltaSeconds, Maximum(TEXT("Power")));
    const double Storm = DustfallSurvivalBridge::Number(EnvironmentDirector, TEXT("StormIntensity"));
    Integrity = Core::IntegrateResource(Integrity, InHabitat ? Rate(TEXT("IntegrityRefill"), 0.0)
        : -Rate(TEXT("IntegrityDrain"), TuningValue(TEXT("StormIntegrityDrainPerSecond")) * Storm), DeltaSeconds, Maximum(TEXT("Integrity")));
    const bool Sprinting = Character->GetVelocity().Size2D() > TuningValue(TEXT("SprintVelocityThreshold"));
    StaminaBeforeTick = Stamina;
    Stamina = Core::IntegrateResource(Stamina, Sprinting
        ? -Rate(TEXT("StaminaDrain"), TuningValue(TEXT("StaminaDrainPerSecond")))
        : Rate(TEXT("StaminaRefill"), TuningValue(TEXT("StaminaRefillPerSecond"))), DeltaSeconds, Maximum(TEXT("Stamina")));
    SprintExhausted = Core::UpdateSprintExhaustion(Stamina, StaminaBeforeTick, SprintExhausted, TuningValue(TEXT("StaminaRecoveryThreshold")));
    const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
    const bool WantsSprint = SprintRequested || (PC && PC->IsInputKeyDown(EKeys::LeftShift));
    Character->GetCharacterMovement()->MaxWalkSpeed = float(TuningValue(SprintExhausted
        ? TEXT("ExhaustedSpeed") : WantsSprint ? TEXT("SprintSpeed") : TEXT("WalkSpeed")));
    if (Power <= 0.0)
        if (auto* Light = Character->FindComponentByClass<USpotLightComponent>()) Light->SetVisibility(false);
    if (Oxygen <= 0.0 || Integrity <= 0.0)
    {
        RespawnClone();
        return; // Blueprint death branch does not advance save/warning clocks.
    }
    SaveElapsed += DeltaSeconds;
    // The generated graph re-evaluates its pure Add(Get SaveElapsed, DeltaSeconds)
    // at the branch, after the setter. Preserve that one-frame-early due check.
    if (SaveElapsed + DeltaSeconds >= TuningValue(TEXT("SaveIntervalSeconds")))
    {
        SaveElapsed = 0.0;
        SaveProgress();
    }
    WarningElapsed += DeltaSeconds;
    // WarningElapsed uses the same setter-then-pure-Add pattern in the legacy graph.
    if (Oxygen <= TuningValue(TEXT("OxygenWarningThreshold")) && WarningElapsed + DeltaSeconds >= TuningValue(TEXT("OxygenWarningCooldown")))
    {
        if (USoundBase* Sound = OxygenWarningSound.LoadSynchronous())
            UGameplayStatics::PlaySound2D(this, Sound, float(TuningValue(TEXT("OxygenWarningVolume"))));
        WarningElapsed = 0.0;
        ++OxygenWarningCount;
        OnSuitWarning.Broadcast(TEXT("Oxygen"));
    }
}

void ADustfallSurvivalDirector::RefreshRecoveryCache()
{
    if (!IsValid(RecoveryActor)) return;
    RecoveryActor->SetActorHiddenInGame(!CrateActive);
    RecoveryActor->SetActorLocation(CrateLocation, false, nullptr, ETeleportType::TeleportPhysics);
}

void ADustfallSurvivalDirector::SaveProgress()
{
    if (const ACharacter* Character = UGameplayStatics::GetPlayerCharacter(this, 0)) SavedLocation = Character->GetActorLocation();
    LastSaveSucceeded = false;
    UClass* SaveClass = LegacySaveClass.LoadSynchronous();
    if (!SaveClass) return;
    USaveGame* Save = UGameplayStatics::CreateSaveGameObject(SaveClass);
    if (!HasSaveSchema(Save)) return;
    using namespace DustfallSurvivalBridge;
    SetNumber(Save, TEXT("Oxygen"), Oxygen);
    SetNumber(Save, TEXT("Power"), Power);
    SetNumber(Save, TEXT("Integrity"), Integrity);
    SetNumber(Save, TEXT("Stamina"), Stamina);
    SetNumber(Save, TEXT("CloneGeneration"), CloneGeneration);
    SetNumber(Save, TEXT("CarriedScrap"), CarriedScrap);
    SetNumber(Save, TEXT("CrateScrap"), CrateScrap);
    SetNumber(Save, TEXT("CrateActive"), CrateActive);
    SetVector(Save, TEXT("CrateLocation"), CrateLocation);
    SetVector(Save, TEXT("SavedLocation"), SavedLocation);
    SetNumber(Save, TEXT("SaveVersion"), 1);
    LastSaveSucceeded = UGameplayStatics::SaveGameToSlot(Save, SaveSlotName, 0);
}

void ADustfallSurvivalDirector::LoadProgress()
{
    if (!UGameplayStatics::DoesSaveGameExist(SaveSlotName, 0)) return;
    USaveGame* Save = UGameplayStatics::LoadGameFromSlot(SaveSlotName, 0);
    UClass* SaveClass = LegacySaveClass.LoadSynchronous();
    if (!SaveClass || !Save || !Save->IsA(SaveClass) || !HasSaveSchema(Save)) return;
    using namespace DustfallSurvivalBridge;
    if (Number(Save, TEXT("SaveVersion")) != 1) return;
    Oxygen = Number(Save, TEXT("Oxygen"));
    Power = Number(Save, TEXT("Power"));
    Integrity = Number(Save, TEXT("Integrity"));
    Stamina = Number(Save, TEXT("Stamina"));
    CloneGeneration = int32(Number(Save, TEXT("CloneGeneration")));
    CarriedScrap = int32(Number(Save, TEXT("CarriedScrap")));
    CrateScrap = int32(Number(Save, TEXT("CrateScrap")));
    CrateActive = Number(Save, TEXT("CrateActive")) != 0;
    CrateLocation = VectorValue(Save, TEXT("CrateLocation"));
    SavedLocation = VectorValue(Save, TEXT("SavedLocation"));
    if (ACharacter* Character = UGameplayStatics::GetPlayerCharacter(this, 0))
        Character->SetActorLocation(SavedLocation, false, nullptr, ETeleportType::TeleportPhysics);
    RefreshRecoveryCache();
}

void ADustfallSurvivalDirector::RecoverCrate()
{
    const ACharacter* Character = UGameplayStatics::GetPlayerCharacter(this, 0);
    if (!CrateActive || !Character || FVector::Distance(Character->GetActorLocation(), CrateLocation) > TuningValue(TEXT("RecoveryDistance"))) return;
    CarriedScrap += CrateScrap;
    CrateScrap = 0;
    CrateActive = false;
    RefreshRecoveryCache();
    SaveProgress();
}

void ADustfallSurvivalDirector::RespawnClone()
{
    ACharacter* Character = UGameplayStatics::GetPlayerCharacter(this, 0);
    if (DeathInProgress || !Character) return;
    DeathInProgress = true;
    const UDustfallSurvivalTuning* Defaults = GetDefault<UDustfallSurvivalTuning>();
    FVector Offset = Tuning ? Tuning->RecoveryOffset : Defaults->RecoveryOffset;
    if (!Tuning && LegacyTuning)
    {
        const auto* P = FindFProperty<FStructProperty>(LegacyTuning->GetClass(), TEXT("RecoveryOffset"));
        if (P && P->Struct == TBaseStructure<FVector>::Get()) Offset = *P->ContainerPtrToValuePtr<FVector>(LegacyTuning);
    }
    CrateLocation = Character->GetActorLocation() + Offset;
    CrateScrap += CarriedScrap;
    CarriedScrap = 0;
    CrateActive = true;
    ++CloneGeneration;
    Oxygen = Maximum(TEXT("Oxygen"));
    Power = Maximum(TEXT("Power"));
    Integrity = Maximum(TEXT("Integrity"));
    Stamina = Maximum(TEXT("Stamina"));
    SprintExhausted = false;
    Character->SetActorLocation(CloneSpawn, false, nullptr, ETeleportType::TeleportPhysics);
    DeathInProgress = false;
    RefreshRecoveryCache();
    SaveProgress();
    OnCloneRespawned.Broadcast();
}

void ADustfallSurvivalDirector::GetSuitState(double& OutOxygen, double& OutPower, double& OutIntegrity, double& OutStamina, int32& OutCloneGeneration) const
{
    OutOxygen = Oxygen;
    OutPower = Power;
    OutIntegrity = Integrity;
    OutStamina = Stamina;
    OutCloneGeneration = CloneGeneration;
}
