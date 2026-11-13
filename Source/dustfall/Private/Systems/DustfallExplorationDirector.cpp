#include "Systems/DustfallExplorationDirector.h"
#include "DustfallSurvivalBridge.h"
#include "DustfallTerrainHazardDirector.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInterface.h"
#include "Components/TextRenderComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Player/DustfallInputConfig.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "Engine/LocalPlayer.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"

using namespace DustfallSurvivalBridge;

namespace
{
void RebuildBeacons(ADustfallExplorationDirector* Director)
{
    TArray<AActor*> Old;
    for (TActorIterator<AActor> It(Director->GetWorld());It;++It)
        if (It->GetOwner()==Director && It->ActorHasTag(TEXT("DF_RuntimeNavigationBeacon"))) Old.Add(*It);
    for (AActor* Actor:Old) Actor->Destroy();
    for (const FVector& Position:Director->Beacons)
    {
        FActorSpawnParameters Params; Params.Owner=Director;
        AActor* Beacon=Director->GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),Position-FVector(0,0,30),FRotator::ZeroRotator,Params);
        if (!Beacon) continue;
        Beacon->Tags.Add(TEXT("DF_RuntimeNavigationBeacon"));
        auto* Post=NewObject<UStaticMeshComponent>(Beacon);
        Beacon->SetRootComponent(Post); Beacon->AddInstanceComponent(Post);
        Post->SetStaticMesh(Director->BeaconMesh); Post->SetMaterial(0,Director->BeaconMaterial);
        Post->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Post->SetWorldLocation(Position-FVector(0,0,30));Post->SetWorldScale3D(FVector(.12,.12,1.2));Post->RegisterComponent();
        auto* Lamp=NewObject<UStaticMeshComponent>(Beacon);Beacon->AddInstanceComponent(Lamp);
        Lamp->SetupAttachment(Post);Lamp->SetStaticMesh(Director->BeaconMesh);Lamp->SetMaterial(0,Director->BeaconMaterial);
        Lamp->SetCollisionEnabled(ECollisionEnabled::NoCollision);Lamp->RegisterComponent();
        Lamp->SetWorldLocation(Position+FVector(0,0,43));Lamp->SetWorldScale3D(FVector(.4,.4,.28));
        auto* Light=NewObject<UPointLightComponent>(Beacon);Beacon->AddInstanceComponent(Light);Light->SetupAttachment(Post);
        Light->SetLightColor(FLinearColor(1.f,.43f,.08f));Light->SetIntensity(220.f);Light->SetAttenuationRadius(650.f);
        Light->SetCastShadows(false);Light->RegisterComponent();Light->SetWorldLocation(Position+FVector(0,0,65));
        auto* Label=NewObject<UTextRenderComponent>(Beacon);Beacon->AddInstanceComponent(Label);Label->SetupAttachment(Post);
        Label->SetText(FText::FromString(TEXT("B / RECOVER BEACON")));Label->SetWorldSize(20);Label->SetTextRenderColor(FColor(255,180,70));Label->SetHorizontalAlignment(EHTA_Center);
        Label->RegisterComponent();Label->SetWorldLocation(Position+FVector(0,0,100));Label->SetWorldScale3D(FVector::OneVector);
    }
}
APawn* Player(const AActor* Context) { return UGameplayStatics::GetPlayerPawn(Context, 0); }

}

ADustfallExplorationDirector::ADustfallExplorationDirector()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickGroup = TG_PostUpdateWork;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Post(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Amber(TEXT("/Game/Systems/M_RecoveryCache.M_RecoveryCache"));
    BeaconMesh=Post.Object;BeaconMaterial=Amber.Object;
}
void ADustfallExplorationDirector::BeginPlay()
{
    Super::BeginPlay();
    if (!Tuning) Tuning = NewObject<UDustfallExplorationTuning>(this);
    SymptomRandom.Initialize(Tuning->SymptomSeed);
    if (!SurvivalDirector) SurvivalDirector = DustfallSurvivalBridge::FindDirector(GetWorld());
    if (SurvivalDirector)
    {
        AddTickPrerequisiteActor(SurvivalDirector);
        EnvironmentDirector=Cast<AActor>(ObjectValue(SurvivalDirector,TEXT("EnvironmentDirector")));
    }
    for (TActorIterator<ADustfallSalvageNode> It(GetWorld()); It; ++It) RegisterNode(*It);
    for (TActorIterator<ADustfallTerrainHazardDirector> It(GetWorld()); It; ++It) AddTickPrerequisiteActor(*It);
    StatusMessage = TEXT("Q scanner  |  E salvage / recover  |  Tab inventory  |  J journal  |  B beacon");
    UpdateInputBindings();
}
void ADustfallExplorationDirector::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    RemoveInputBindings();
    Super::EndPlay(EndPlayReason);
}
void ADustfallExplorationDirector::RemoveInputBindings()
{
    if (UEnhancedInputComponent* Component = BoundInputComponent.Get())
        for (uint32 Handle : InputBindingHandles) Component->RemoveBindingByHandle(Handle);
    if (bAddedInputContext && BoundInputSubsystem.IsValid() && BoundMappingContext.IsValid())
        BoundInputSubsystem->RemoveMappingContext(BoundMappingContext.Get());
    InputBindingHandles.Reset();
    BoundInputComponent.Reset();
    BoundInputSubsystem.Reset();
    BoundMappingContext.Reset();
    BoundInputConfig.Reset();
    BoundInputPawn.Reset();
    PendingInputActions = 0;
    bAddedInputContext = false;
}
void ADustfallExplorationDirector::UpdateInputBindings()
{
    APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
    ULocalPlayer* LocalPlayer = PC && PC->IsLocalController() ? PC->GetLocalPlayer() : nullptr;
    UEnhancedInputLocalPlayerSubsystem* Subsystem = LocalPlayer ? LocalPlayer->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>() : nullptr;
    UEnhancedInputComponent* Component = PC ? Cast<UEnhancedInputComponent>(PC->InputComponent) : nullptr;
    APawn* Pawn = PC ? PC->GetPawn() : nullptr;
    if (!InputConfig || !InputConfig->MappingContext || !Subsystem || !Component || !Pawn)
    {
        RemoveInputBindings();
        if (!InputConfig && !bLoggedInputPath)
        {
            UE_LOG(LogTemp, Log, TEXT("DUSTFALL exploration input: raw-key fallback (InputConfig is null)."));
            bLoggedInputPath = true;
        }
        return; // Retry on Tick: possession/controller input setup can happen after BeginPlay.
    }
    if (BoundInputComponent.Get() == Component && BoundInputSubsystem.Get() == Subsystem &&
        BoundInputConfig.Get() == InputConfig && BoundInputPawn.Get() == Pawn &&
        BoundMappingContext.Get() == InputConfig->MappingContext.Get()) return;
    RemoveInputBindings();
    BoundInputComponent = Component;
    BoundInputSubsystem = Subsystem;
    BoundMappingContext = InputConfig->MappingContext;
    BoundInputConfig = InputConfig;
    BoundInputPawn = Pawn;
    // Do not remove a context installed by another owner during our teardown.
    bAddedInputContext = !Subsystem->HasMappingContext(InputConfig->MappingContext);
    if (bAddedInputContext) Subsystem->AddMappingContext(InputConfig->MappingContext, InputConfig->MappingPriority);
    const UInputAction* Actions[] = { InputConfig->Inventory, InputConfig->Journal, InputConfig->Scanner,
        InputConfig->Beacon, InputConfig->Interact, InputConfig->QuickSave, InputConfig->QuickLoad, InputConfig->ToggleSymptoms };
    for (uint8 Index = 0; Index < UE_ARRAY_COUNT(Actions); ++Index)
    {
        if (!Actions[Index]) continue;
        const uint8 Mask = uint8(1u << Index);
        InputBindingHandles.Add(Component->BindActionValueLambda(Actions[Index], ETriggerEvent::Started,
            [this, Mask](const FInputActionValue&)
            {
                // Drain in the original Tick input block, after survival synchronization.
                if (bInitialized) PendingInputActions |= Mask;
            }).GetHandle());
    }
    if (!bLoggedInputPath)
    {
        UE_LOG(LogTemp, Log, TEXT("DUSTFALL exploration input: Enhanced Input (Started)."));
        bLoggedInputPath = true;
    }
}
int32 ADustfallExplorationDirector::InventoryCount() const
{
    int64 Total = 0; for (const auto& Item : Inventory) Total += FMath::Max(0, Item.Value); return int32(FMath::Min<int64>(Total,MAX_int32));
}
void ADustfallExplorationDirector::MergePayload(TMap<FName,int32>& Target, const TMap<FName,int32>& Source)
{
    for (const auto& Item : Source) if (!Item.Key.IsNone() && Item.Value > 0)
        Target.FindOrAdd(Item.Key) = int32(FMath::Min<int64>(int64(Target.FindRef(Item.Key)) + Item.Value, MAX_int32));
}
bool ADustfallExplorationDirector::AddItem(FName ItemId, int32 Quantity)
{
    if (ItemId.IsNone() || Quantity <= 0 || !Tuning || int64(InventoryCount()) + Quantity > Tuning->InventoryCapacity) return false;
    Inventory.FindOrAdd(ItemId) += Quantity;
    return true;
}
double ADustfallExplorationDirector::SuitValue(FName Name) const { return Number(SurvivalDirector,Name); }
FVector ADustfallExplorationDirector::HomeLocation() const { return VectorValue(SurvivalDirector,TEXT("CloneSpawn")); }
FString ADustfallExplorationDirector::SaveSlot() const
{
    return StringValue(SurvivalDirector,TEXT("SaveSlotName"),TEXT("Dustfall_Phase4")) + TEXT("_Exploration");
}
void ADustfallExplorationDirector::CallSurvival(FName FunctionName)
{
    Call(SurvivalDirector,FunctionName);
}
void ADustfallExplorationDirector::RegisterNode(ADustfallSalvageNode* Node)
{
    if (!IsValid(Node)) return;
    Nodes.AddUnique(Node); Node->RegisteredDirector=this;
    Node->SetClaimed(ClaimedNodes.Contains(Node->StableId));
}
void ADustfallExplorationDirector::UnregisterNode(ADustfallSalvageNode* Node)
{
    Nodes.RemoveAll([Node](const TWeakObjectPtr<ADustfallSalvageNode>& Entry) { return !Entry.IsValid() || Entry.Get()==Node; });
}

void ADustfallExplorationDirector::RefreshNodes()
{
    for (const auto& Entry : Nodes) if (auto* Node=Entry.Get()) Node->SetClaimed(ClaimedNodes.Contains(Node->StableId));
}
ADustfallSalvageNode* ADustfallExplorationDirector::NearestNode() const
{
    APawn* Pawn = Player(this); if (!Pawn || !Tuning) return nullptr;
    ADustfallSalvageNode* Best = nullptr;
    double Range = Tuning->InteractionRange;
    for (const auto& Entry : Nodes)
    {
        auto* It=Entry.Get(); if (!It) continue;
        if (It->bClaimed) continue;
        double Distance = FVector::Dist(Pawn->GetActorLocation(), It->GetActorLocation());
        if (Distance < Range)
        {
            FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(DustfallInteraction), false, Pawn);
            bool bBlocked = GetWorld()->LineTraceSingleByChannel(Hit, Pawn->GetActorLocation()+FVector(0,0,Tuning->InteractionTraceHeight), It->GetActorLocation(), ECC_Visibility, Query);
            if (!bBlocked || Hit.GetActor() == It) { Best = It; Range = Distance; }
        }
    }
    return Best;
}
bool ADustfallExplorationDirector::Interact()
{
    if (RecoverInventory()) return true;
    auto* Node = NearestNode(); if (!Node || Node->StableId.IsNone()) return false;
    if (Node->LoreText.IsEmpty() && !AddItem(Node->ItemId, Node->Quantity)) { StatusMessage = TEXT("Inventory full. Recover space before salvaging."); return false; }
    ClaimedNodes.Add(Node->StableId);
    if (!Node->LoreText.IsEmpty())
    {
        Journal.Add(Node->StableId, Node->DisplayName + TEXT("\n") + Node->LoreText);
        ActiveLore = Node->LoreText; bJournalOpen = true;
        PrivateStrain = FMath::Clamp(PrivateStrain + Node->LoreStrain,0.f,100.f);
        StatusMessage = TEXT("Record archived. J closes journal.");
    }
    else StatusMessage = FString::Printf(TEXT("Recovered %d %s"),Node->Quantity,*Node->ItemId.ToString());
    RefreshNodes(); SaveExploration(); return true;
}
bool ADustfallExplorationDirector::PulseScanner()
{
    if (!Tuning || ScannerCooldownRemaining > 0 || SuitValue(TEXT("Power")) < Tuning->ScannerPowerCost) return false;
    SetNumber(SurvivalDirector,TEXT("Power"),SuitValue(TEXT("Power"))-Tuning->ScannerPowerCost);
    ScannerRemaining = Tuning->ScannerDuration; ScannerCooldownRemaining = Tuning->ScannerCooldown;
    StatusMessage = TEXT("Scanner pulse: amber salvage / cyan records. Critical suit telemetry remains live."); return true;
}
bool ADustfallExplorationDirector::PlaceBeacon()
{
    APawn* Pawn = Player(this); if (!Pawn || !Tuning) return false;
    for (int32 I = Beacons.Num()-1; I >= 0; --I)
        if (FVector::Dist(Pawn->GetActorLocation(),Beacons[I]) < Tuning->BeaconRecoverRange) { Beacons.RemoveAt(I); BeaconRecords.RemoveAt(I); MergePayload(Inventory, {{TEXT("PowerCell"),Tuning->BeaconPowerCellCost}}); StatusMessage=Tuning->BeaconPowerCellCost==1 ? TEXT("Beacon recovered; PowerCell returned.") : FString::Printf(TEXT("Beacon recovered; %d PowerCell returned."),Tuning->BeaconPowerCellCost); RebuildBeacons(this); SaveExploration(); return true; }
    if (Beacons.Num() >= Tuning->MaximumBeacons) { StatusMessage=TEXT("Beacon limit reached. B near a beacon recovers it."); return false; }
    int32* Cells = Inventory.Find(TEXT("PowerCell"));
    if (!Cells || Tuning->BeaconPowerCellCost<=0 || *Cells < Tuning->BeaconPowerCellCost) { StatusMessage=Tuning->BeaconPowerCellCost==1 ? TEXT("Beacon requires one salvaged PowerCell.") : FString::Printf(TEXT("Beacon requires %d salvaged PowerCell."),Tuning->BeaconPowerCellCost); return false; }
    if ((*Cells -= Tuning->BeaconPowerCellCost) == 0) Inventory.Remove(TEXT("PowerCell"));
    FDustfallBeaconRecord Record; Record.Id=FGuid::NewGuid(); Record.Location=Pawn->GetActorLocation(); BeaconRecords.Add(Record); Beacons.Add(Record.Location); StatusMessage=TEXT("Beacon placed. B nearby recovers the marker."); RebuildBeacons(this); SaveExploration(); return true;
}
bool ADustfallExplorationDirector::RecoverInventory()
{
    APawn* Pawn = Player(this);
    if (!Pawn || !Tuning || RecoveryInventory.IsEmpty() || !SuitValue(TEXT("CrateActive")) || FVector::Dist(Pawn->GetActorLocation(), VectorValue(SurvivalDirector,TEXT("CrateLocation"))) > Tuning->CrateRecoverRange) return false;
    // Recovery may exceed carrying capacity: existing player property is never discarded.
    MergePayload(Inventory,RecoveryInventory); RecoveryInventory.Empty();
    CallSurvival(TEXT("RecoverCrate")); bPreviousCrateActive = false;
    StatusMessage=TEXT("Recovery crate transferred to inventory."); SaveExploration(); return true;
}
void ADustfallExplorationDirector::SynchronizeSurvival()
{
    const int32 Clone = int32(SuitValue(TEXT("CloneGeneration")));
    const bool bCrate = SuitValue(TEXT("CrateActive")) != 0;
    if (Clone > LastClone)
    {
        MergePayload(RecoveryInventory, Inventory); Inventory.Empty();
        PrivateStrain=FMath::Min(100.f,PrivateStrain+Tuning->DeathStrainGain);
        LastClone=Clone; bPreviousCrateActive=bCrate;
        SetNumber(SurvivalDirector,TEXT("CarriedScrap"),0); SetNumber(SurvivalDirector,TEXT("CrateScrap"),0);
        StatusMessage=TEXT("New clone online. Carried items remain in your recovery crate."); SaveExploration();
    }
    // Blueprint E may recover first in the same frame. Transfer typed payload exactly once.
    else if (bPreviousCrateActive && !bCrate && !RecoveryInventory.IsEmpty())
    {
        MergePayload(Inventory,RecoveryInventory); RecoveryInventory.Empty(); SaveExploration();
    }
    bPreviousCrateActive=bCrate;
    SetNumber(SurvivalDirector,TEXT("CarriedScrap"),0); SetNumber(SurvivalDirector,TEXT("CrateScrap"),0);
}
void ADustfallExplorationDirector::SetSymptomIntensity(float Value)
{
    SymptomIntensity = FMath::IsFinite(Value) ? FMath::Clamp(Value,0.f,1.f) : 0;
    if (SymptomIntensity == 0) SymptomRemaining=0;
}
bool ADustfallExplorationDirector::SaveExploration()
{
    if (!SurvivalDirector || !Player(this)) return false;
    auto* Save = Cast<UDustfallExplorationSave>(UGameplayStatics::CreateSaveGameObject(UDustfallExplorationSave::StaticClass()));
    Save->Inventory=Inventory; Save->RecoveryInventory=RecoveryInventory; Save->ClaimedNodes=ClaimedNodes; Save->Journal=Journal; Save->Beacons=Beacons; Save->BeaconRecords=BeaconRecords;
    Save->PrivateStrain=PrivateStrain; Save->SymptomIntensity=SymptomIntensity;
    Save->PlayerLocation=Player(this)->GetActorLocation(); Save->CrateLocation=VectorValue(SurvivalDirector,TEXT("CrateLocation"));
    Save->bCrateActive=SuitValue(TEXT("CrateActive")) != 0; Save->CloneGeneration=int32(SuitValue(TEXT("CloneGeneration")));
    Save->Oxygen=SuitValue(TEXT("Oxygen")); Save->Power=SuitValue(TEXT("Power")); Save->Integrity=SuitValue(TEXT("Integrity")); Save->Stamina=SuitValue(TEXT("Stamina"));
    bLastSaveSucceeded=UGameplayStatics::SaveGameToSlot(Save,SaveSlot(),0);
    if (bLastSaveSucceeded) CallSurvival(TEXT("SaveProgress"));
    return bLastSaveSucceeded;
}
bool ADustfallExplorationDirector::LoadExploration()
{
    if (!SurvivalDirector || !Player(this)) return false;
    const bool bExists=UGameplayStatics::DoesSaveGameExist(SaveSlot(),0);
    auto* Save=Cast<UDustfallExplorationSave>(bExists ? UGameplayStatics::LoadGameFromSlot(SaveSlot(),0) : nullptr);
    if (!Save)
    {
        // One-time migration preserves schema-1 scalar payloads and the user's Phase3 save.
        if (bExists) { StatusMessage=TEXT("Exploration save unreadable; current session retained."); return false; }
        Inventory.Empty(); RecoveryInventory.Empty();
        int32 Carried=int32(SuitValue(TEXT("CarriedScrap"))), Cached=int32(SuitValue(TEXT("CrateScrap")));
        if (Carried>0) Inventory.Add(TEXT("Scrap"),Carried);
        if (Cached>0) RecoveryInventory.Add(TEXT("Scrap"),Cached);
    }
    else
    {
        auto* Validated=NewObject<UDustfallExplorationSave>();
        if (!UDustfallExplorationSave::ValidateAndMigrate(*Save,*Validated)) { StatusMessage=TEXT("Invalid exploration save; session retained."); return false; }
        Save=Validated;
        Inventory=Save->Inventory; RecoveryInventory=Save->RecoveryInventory; ClaimedNodes=Save->ClaimedNodes; Journal=Save->Journal; BeaconRecords=Save->BeaconRecords; Beacons.Empty();
        for (const auto& Record : BeaconRecords) Beacons.Add(Record.Location);
        PrivateStrain=FMath::Clamp(Save->PrivateStrain,0.f,100.f); SetSymptomIntensity(Save->SymptomIntensity);
        SetNumber(SurvivalDirector,TEXT("Oxygen"),Save->Oxygen); SetNumber(SurvivalDirector,TEXT("Power"),Save->Power);
        SetNumber(SurvivalDirector,TEXT("Integrity"),Save->Integrity); SetNumber(SurvivalDirector,TEXT("Stamina"),Save->Stamina);
        SetNumber(SurvivalDirector,TEXT("CloneGeneration"),Save->CloneGeneration); SetNumber(SurvivalDirector,TEXT("CrateActive"),Save->bCrateActive);
        SetVector(SurvivalDirector,TEXT("CrateLocation"),Save->CrateLocation);
        Player(this)->SetActorLocation(Save->PlayerLocation,false,nullptr,ETeleportType::TeleportPhysics);
        CallSurvival(TEXT("RefreshRecoveryCache"));
    }
    LastClone=int32(SuitValue(TEXT("CloneGeneration"))); bPreviousCrateActive=SuitValue(TEXT("CrateActive")) != 0;
    SetNumber(SurvivalDirector,TEXT("CarriedScrap"),0); SetNumber(SurvivalDirector,TEXT("CrateScrap"),0);
    SymptomRemaining=0; ScannerRemaining=0; RefreshNodes(); RebuildBeacons(this); bInitialized=true; return true;
}
void ADustfallExplorationDirector::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds); Age+=DeltaSeconds;
    if (!bInitialized)
    {
        if (Age>Tuning->FirstLoadDelay && SurvivalDirector && Player(this)) { LoadExploration(); bInitialized=true; }
        return;
    }
    SynchronizeSurvival();
    ScannerRemaining=FMath::Max(0.f,ScannerRemaining-DeltaSeconds); ScannerCooldownRemaining=FMath::Max(0.f,ScannerCooldownRemaining-DeltaSeconds);
    const bool bHome=SuitValue(TEXT("InHabitat")) != 0;
    FDustfallModifierStack FrameModifiers;
    FrameModifiers.Set(TEXT("Weather"),1.f+Tuning->StormStrainMultiplier*FMath::Clamp(float(Number(EnvironmentDirector,TEXT("StormIntensity"))),0.f,1.f));
    const bool bLowSuit=SuitValue(TEXT("Oxygen"))<Tuning->LowOxygenStrainThreshold || SuitValue(TEXT("Integrity"))<Tuning->LowIntegrityStrainThreshold;
    FrameModifiers.Set(TEXT("LowSuit"), bLowSuit ? Tuning->LowSuitStrainMultiplier : 1.f);
    const float OutsideRate=StrainModifiers.Evaluate(FrameModifiers.Evaluate(Tuning->OutsideStrainPerSecond));
    PrivateStrain=FMath::Clamp(PrivateStrain+DeltaSeconds*(bHome ? -Tuning->HomeStrainRecoveryPerSecond : OutsideRate),0.f,100.f);
    SymptomRemaining=FMath::Max(0.f,SymptomRemaining-DeltaSeconds); SymptomElapsed+=DeltaSeconds;
    if (bHome) SymptomRemaining=0;
    else if (SymptomIntensity>0 && PrivateStrain>=Tuning->SymptomThreshold && SymptomElapsed>Tuning->SymptomInterval)
    { PickSymptom(); SymptomElapsed=0; }
    UpdateInputBindings();
    if (APlayerController* PC=UGameplayStatics::GetPlayerController(this,0))
    {
        const auto Pressed = [this, PC](uint8 Index, const FKey& Key)
        {
            return InputConfig ? (PendingInputActions & (1u << Index)) != 0 : PC->WasInputKeyJustPressed(Key);
        };
        if (Pressed(0, EKeys::Tab)) bInventoryOpen=!bInventoryOpen;
        if (Pressed(1, EKeys::J)) bJournalOpen=!bJournalOpen;
        if (Pressed(2, EKeys::Q)) PulseScanner();
        if (Pressed(3, EKeys::B)) PlaceBeacon();
        if (Pressed(4, EKeys::E)) Interact();
        if (Pressed(5, EKeys::F5)) { SaveExploration(); StatusMessage=bLastSaveSucceeded ? TEXT("Progress saved.") : TEXT("Save failed."); }
        if (Pressed(6, EKeys::F9)) { const bool bLoaded=LoadExploration(); StatusMessage=bLoaded ? TEXT("Progress loaded.") : TEXT("Load failed; current exploration session retained."); }
        if (Pressed(7, EKeys::F8)) { SetSymptomIntensity(SymptomIntensity>0 ? 0 : 1); SaveExploration(); StatusMessage=SymptomIntensity>0 ? TEXT("Subtle symptoms enabled.") : TEXT("Symptoms disabled."); }
    }
    PendingInputActions = 0;
    SaveElapsed+=DeltaSeconds;
    if (SaveElapsed>=Tuning->AutosaveInterval) { SaveExploration(); SaveElapsed=0; }
}

void ADustfallExplorationDirector::SetStrainModifier(FName Source,float Multiplier) { StrainModifiers.Set(Source,Multiplier); }
void ADustfallExplorationDirector::ClearStrainModifier(FName Source) { StrainModifiers.Clear(Source); }
void ADustfallExplorationDirector::PickSymptom()
{
    double Total=0;
    auto Eligible=[this](const FDustfallSymptomDefinition& S) { return !S.Id.IsNone() && FMath::IsFinite(S.Weight) && S.Weight>0 && FMath::IsFinite(S.MinimumStrain) && PrivateStrain>=S.MinimumStrain && FMath::IsFinite(S.Duration) && S.Duration>=0; };
    for (const auto& S : Tuning->Symptoms) if (Eligible(S)) Total+=S.Weight;
    if (Total<=0) return;
    double Pick=SymptomRandom.FRand()*Total;
    for (const auto& S : Tuning->Symptoms) if (Eligible(S))
    {
        Pick-=S.Weight;
        if (Pick<=0) { CurrentSymptom.Kind=S.Kind; CurrentSymptom.Text=S.Text; SymptomRemaining=(S.Duration>0 ? S.Duration : Tuning->SymptomDuration)*SymptomIntensity; return; }
    }
}
