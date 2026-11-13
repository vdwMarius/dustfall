#include "DustfallExploration.h"
#include "DustfallTerrainHazardDirector.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInterface.h"
#include "Components/TextRenderComponent.h"
#include "Engine/Canvas.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "UObject/UnrealType.h"

namespace
{
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
    return 0;
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
    if (FBoolProperty* Boolean = CastField<FBoolProperty>(Property)) Boolean->SetPropertyValue_InContainer(Object, Value != 0);
}
FVector VectorValue(const UObject* Object, FName Name)
{
    if (Object) if (const FStructProperty* P = FindFProperty<FStructProperty>(Object->GetClass(), Name))
        if (P->Struct == TBaseStructure<FVector>::Get()) return *P->ContainerPtrToValuePtr<FVector>(Object);
    return FVector::ZeroVector;
}
void SetVector(UObject* Object, FName Name, FVector Value)
{
    if (Object) if (FStructProperty* P = FindFProperty<FStructProperty>(Object->GetClass(), Name))
        if (P->Struct == TBaseStructure<FVector>::Get()) *P->ContainerPtrToValuePtr<FVector>(Object) = Value;
}
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
ADustfallExplorationDirector* FindDirector(UWorld* World)
{
    for (TActorIterator<ADustfallExplorationDirector> It(World); It; ++It) return *It;
    return nullptr;
}
}

ADustfallSalvageNode::ADustfallSalvageNode()
{
    Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SalvageMesh"));
    SetRootComponent(Mesh);
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Shape(TEXT("/Engine/BasicShapes/Cube.Cube"));
    Mesh->SetStaticMesh(Shape.Object);
    Mesh->SetRelativeScale3D(FVector(.65, .45, .35));
    Mesh->SetCollisionProfileName(TEXT("BlockAll"));
    Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("InteractionLabel"));
    Label->SetupAttachment(Mesh);
    Label->SetRelativeLocation(FVector(0,0,110));
    Label->SetWorldSize(25);
    Label->SetTextRenderColor(FColor(240,177,85));
    Label->SetHorizontalAlignment(EHTA_Center);
}
void ADustfallSalvageNode::BeginPlay()
{
    Super::BeginPlay();
    Label->SetText(FText::FromString(DisplayName));
    if (auto* D = FindDirector(GetWorld())) SetClaimed(D->ClaimedNodes.Contains(StableId));
}
void ADustfallSalvageNode::SetClaimed(bool bValue)
{
    bClaimed = bValue;
    SetActorHiddenInGame(bValue);
    SetActorEnableCollision(!bValue);
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
    if (!SurvivalDirector)
        for (TActorIterator<AActor> It(GetWorld()); It; ++It)
            if (It->GetClass()->FindPropertyByName(TEXT("CloneGeneration")) && It->GetClass()->FindPropertyByName(TEXT("CrateScrap"))) { SurvivalDirector = *It; break; }
    if (SurvivalDirector)
    {
        AddTickPrerequisiteActor(SurvivalDirector);
        if (const FObjectProperty* P=FindFProperty<FObjectProperty>(SurvivalDirector->GetClass(),TEXT("EnvironmentDirector")))
            EnvironmentDirector=Cast<AActor>(P->GetObjectPropertyValue_InContainer(SurvivalDirector));
    }
    for (TActorIterator<ADustfallTerrainHazardDirector> It(GetWorld()); It; ++It) AddTickPrerequisiteActor(*It);
    StatusMessage = TEXT("Q scanner  |  E salvage / recover  |  Tab inventory  |  J journal  |  B beacon");
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
    if (SurvivalDirector) if (const FStrProperty* P = FindFProperty<FStrProperty>(SurvivalDirector->GetClass(), TEXT("SaveSlotName")))
        return P->GetPropertyValue_InContainer(SurvivalDirector) + TEXT("_Exploration");
    return TEXT("Dustfall_Phase4_Exploration");
}
void ADustfallExplorationDirector::CallSurvival(FName FunctionName)
{
    if (SurvivalDirector) if (UFunction* F = SurvivalDirector->FindFunction(FunctionName)) SurvivalDirector->ProcessEvent(F,nullptr);
}
void ADustfallExplorationDirector::RefreshNodes()
{
    for (TActorIterator<ADustfallSalvageNode> It(GetWorld()); It; ++It) It->SetClaimed(ClaimedNodes.Contains(It->StableId));
}
ADustfallSalvageNode* ADustfallExplorationDirector::NearestNode() const
{
    APawn* Pawn = Player(this); if (!Pawn || !Tuning) return nullptr;
    ADustfallSalvageNode* Best = nullptr;
    double Range = Tuning->InteractionRange;
    for (TActorIterator<ADustfallSalvageNode> It(GetWorld()); It; ++It)
    {
        if (It->bClaimed) continue;
        double Distance = FVector::Dist(Pawn->GetActorLocation(), It->GetActorLocation());
        if (Distance < Range)
        {
            FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(DustfallInteraction), false, Pawn);
            bool bBlocked = GetWorld()->LineTraceSingleByChannel(Hit, Pawn->GetActorLocation()+FVector(0,0,35), It->GetActorLocation(), ECC_Visibility, Query);
            if (!bBlocked || Hit.GetActor() == *It) { Best = *It; Range = Distance; }
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
    Node->SetClaimed(true); SaveExploration(); return true;
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
        if (FVector::Dist(Pawn->GetActorLocation(),Beacons[I]) < 300) { Beacons.RemoveAt(I); Inventory.FindOrAdd(TEXT("PowerCell")) += 1; StatusMessage=TEXT("Beacon recovered; PowerCell returned."); RebuildBeacons(this); SaveExploration(); return true; }
    if (Beacons.Num() >= Tuning->MaximumBeacons) { StatusMessage=TEXT("Beacon limit reached. B near a beacon recovers it."); return false; }
    int32* Cells = Inventory.Find(TEXT("PowerCell"));
    if (!Cells || *Cells < 1) { StatusMessage=TEXT("Beacon requires one salvaged PowerCell."); return false; }
    if (--*Cells == 0) Inventory.Remove(TEXT("PowerCell"));
    Beacons.Add(Pawn->GetActorLocation()); StatusMessage=TEXT("Beacon placed. B nearby recovers the marker."); RebuildBeacons(this); SaveExploration(); return true;
}
bool ADustfallExplorationDirector::RecoverInventory()
{
    APawn* Pawn = Player(this);
    if (!Pawn || RecoveryInventory.IsEmpty() || !SuitValue(TEXT("CrateActive")) || FVector::Dist(Pawn->GetActorLocation(), VectorValue(SurvivalDirector,TEXT("CrateLocation"))) > 250) return false;
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
        PrivateStrain=FMath::Min(100.f,PrivateStrain+4.f);
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
    Save->Inventory=Inventory; Save->RecoveryInventory=RecoveryInventory; Save->ClaimedNodes=ClaimedNodes; Save->Journal=Journal; Save->Beacons=Beacons;
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
        if (Save->Version != 2) { StatusMessage=TEXT("Unsupported exploration save version; current session retained."); return false; }
        for (const auto& Item : Save->Inventory) if (Item.Key.IsNone() || Item.Value<=0) { StatusMessage=TEXT("Invalid inventory save; session retained."); return false; }
        for (const auto& Item : Save->RecoveryInventory) if (Item.Key.IsNone() || Item.Value<=0) { StatusMessage=TEXT("Invalid recovery save; session retained."); return false; }
        if (!FMath::IsFinite(Save->PrivateStrain) || Save->PlayerLocation.ContainsNaN() || Save->CrateLocation.ContainsNaN() || !FMath::IsFinite(Save->Oxygen) || !FMath::IsFinite(Save->Power) || !FMath::IsFinite(Save->Integrity) || !FMath::IsFinite(Save->Stamina)) return false;
        Inventory=Save->Inventory; RecoveryInventory=Save->RecoveryInventory; ClaimedNodes=Save->ClaimedNodes; Journal=Save->Journal; Beacons=Save->Beacons;
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
        if (Age>.35f && SurvivalDirector && Player(this)) { LoadExploration(); bInitialized=true; }
        return;
    }
    SynchronizeSurvival(); RefreshNodes();
    ScannerRemaining=FMath::Max(0.f,ScannerRemaining-DeltaSeconds); ScannerCooldownRemaining=FMath::Max(0.f,ScannerCooldownRemaining-DeltaSeconds);
    const bool bHome=SuitValue(TEXT("InHabitat")) != 0;
    const float Danger=(SuitValue(TEXT("Oxygen"))<20 || SuitValue(TEXT("Integrity"))<30) ? .08f : 0;
    PrivateStrain=FMath::Clamp(PrivateStrain+DeltaSeconds*(bHome ? -Tuning->HomeStrainRecoveryPerSecond : Tuning->OutsideStrainPerSecond+Danger+Tuning->StormStrainPerSecond*FMath::Clamp(float(Number(EnvironmentDirector,TEXT("StormIntensity"))),0.f,1.f)),0.f,100.f);
    SymptomRemaining=FMath::Max(0.f,SymptomRemaining-DeltaSeconds); SymptomElapsed+=DeltaSeconds;
    if (bHome) SymptomRemaining=0;
    else if (SymptomIntensity>0 && PrivateStrain>=Tuning->SymptomThreshold && SymptomElapsed>Tuning->SymptomInterval)
    { SymptomRemaining=3*SymptomIntensity; SymptomElapsed=0; }
    if (APlayerController* PC=UGameplayStatics::GetPlayerController(this,0))
    {
        if (PC->WasInputKeyJustPressed(EKeys::Tab)) bInventoryOpen=!bInventoryOpen;
        if (PC->WasInputKeyJustPressed(EKeys::J)) bJournalOpen=!bJournalOpen;
        if (PC->WasInputKeyJustPressed(EKeys::Q)) PulseScanner();
        if (PC->WasInputKeyJustPressed(EKeys::B)) PlaceBeacon();
        if (PC->WasInputKeyJustPressed(EKeys::E)) Interact();
        if (PC->WasInputKeyJustPressed(EKeys::F5)) { SaveExploration(); StatusMessage=bLastSaveSucceeded ? TEXT("Progress saved.") : TEXT("Save failed."); }
        if (PC->WasInputKeyJustPressed(EKeys::F9)) { const bool bLoaded=LoadExploration(); StatusMessage=bLoaded ? TEXT("Progress loaded.") : TEXT("Load failed; current exploration session retained."); }
        if (PC->WasInputKeyJustPressed(EKeys::F8)) { SetSymptomIntensity(SymptomIntensity>0 ? 0 : 1); SaveExploration(); StatusMessage=SymptomIntensity>0 ? TEXT("Subtle symptoms enabled.") : TEXT("Symptoms disabled."); }
    }
    SaveElapsed+=DeltaSeconds;
    if (SaveElapsed>=30) { SaveExploration(); SaveElapsed=0; }
}
