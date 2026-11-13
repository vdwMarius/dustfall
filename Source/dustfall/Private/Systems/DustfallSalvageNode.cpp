#include "Systems/DustfallSalvageNode.h"
#include "Systems/DustfallExplorationDirector.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "UObject/ConstructorHelpers.h"
#include "EngineUtils.h"
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
    for (TActorIterator<ADustfallExplorationDirector> It(GetWorld()); It; ++It) { It->RegisterNode(this); break; }
}
void ADustfallSalvageNode::SetClaimed(bool bValue)
{
    bClaimed = bValue;
    SetActorHiddenInGame(bValue);
    SetActorEnableCollision(!bValue);
}
void ADustfallSalvageNode::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (RegisteredDirector.IsValid()) RegisteredDirector->UnregisterNode(this);
    Super::EndPlay(EndPlayReason);
}
