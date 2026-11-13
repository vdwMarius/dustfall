#include "DustfallTerrainHazardDirector.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Systems/DustfallSurvivalBridge.h"

using namespace DustfallSurvivalBridge;
ADustfallTerrainHazardDirector::ADustfallTerrainHazardDirector()
{
    PrimaryActorTick.bCanEverTick=true; PrimaryActorTick.TickGroup=TG_PostPhysics;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
}
void ADustfallTerrainHazardDirector::BeginPlay()
{
    Super::BeginPlay();
    if(!SurvivalDirector)SurvivalDirector=FindDirector(GetWorld());
    if(SurvivalDirector)AddTickPrerequisiteActor(SurvivalDirector);
    LastClone=int32(Number(SurvivalDirector,TEXT("CloneGeneration")));
    if(auto* C=UGameplayStatics::GetPlayerCharacter(this,0)) LastSafeLocation=C->GetActorLocation();
}
void ADustfallTerrainHazardDirector::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    auto* C=UGameplayStatics::GetPlayerCharacter(this,0);if(!C||!SurvivalDirector)return;
    auto RelocateCache=[&]()
    {
        SetVector(SurvivalDirector,TEXT("CrateLocation"),LastSafeLocation-FVector(0,0,65));
        Call(SurvivalDirector,TEXT("RefreshRecoveryCache"));
        Call(SurvivalDirector,TEXT("SaveProgress"));
    };
    auto* Movement=C->GetCharacterMovement();
    int32 Clone=int32(Number(SurvivalDirector,TEXT("CloneGeneration")));
    if(Clone!=LastClone)
    {
        if(bRelocateCache)
        {
            RelocateCache();
        }
        LastClone=Clone;bRelocateCache=false;MaximumFallSpeed=0;bWasFalling=false;
    }
    const bool bFalling=Movement->IsFalling();
    if(bFalling)
    {
        MaximumFallSpeed=FMath::Max(MaximumFallSpeed,float(-C->GetVelocity().Z));
        if(MaximumFallSpeed>SafeImpactSpeed)bRelocateCache=true;
        // World-boundary rescue: a missed collision cannot strand the player/cache.
        if(C->GetActorLocation().Z < KillHeight)
        {
            SetNumber(SurvivalDirector,TEXT("Integrity"),0);
            Call(SurvivalDirector,TEXT("RespawnClone"));
            RelocateCache();
            LastClone=int32(Number(SurvivalDirector,TEXT("CloneGeneration")));
            bRelocateCache=false;MaximumFallSpeed=0;bWasFalling=false;return;
        }
    }
    else if(bWasFalling)
    {
        LastImpactDamage=FMath::Max(0.f,MaximumFallSpeed-SafeImpactSpeed)*DamagePerExcessSpeed;
        if(LastImpactDamage>0)SetNumber(SurvivalDirector,TEXT("Integrity"),FMath::Max(0.,Number(SurvivalDirector,TEXT("Integrity"))-LastImpactDamage));
        MaximumFallSpeed=0;
        if(Number(SurvivalDirector,TEXT("Integrity"))>0)bRelocateCache=false;
    }
    else if(Movement->IsMovingOnGround() && !bRelocateCache)
    {
        // Keep rim position until the landing has been evaluated, never a point mid-fall.
        LastSafeLocation=C->GetActorLocation();
    }
    bWasFalling=bFalling;
}
