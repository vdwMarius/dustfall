#include "DustfallTerrainHazardDirector.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/UnrealType.h"

namespace
{
double Read(UObject* O,FName N)
{
    if(!O) return 0;
    if(auto* P=FindFProperty<FNumericProperty>(O->GetClass(),N))
    {void* V=P->ContainerPtrToValuePtr<void>(O);return P->IsInteger()?double(P->GetSignedIntPropertyValue(V)):P->GetFloatingPointPropertyValue(V);}
    return 0;
}
void Write(UObject* O,FName N,double V)
{
    if(!O)return;
    if(auto* P=FindFProperty<FNumericProperty>(O->GetClass(),N))
    {void* A=P->ContainerPtrToValuePtr<void>(O);if(P->IsInteger())P->SetIntPropertyValue(A,int64(V));else P->SetFloatingPointPropertyValue(A,V);}
}
}
ADustfallTerrainHazardDirector::ADustfallTerrainHazardDirector()
{
    PrimaryActorTick.bCanEverTick=true; PrimaryActorTick.TickGroup=TG_PostPhysics;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Root")));
}
void ADustfallTerrainHazardDirector::BeginPlay()
{
    Super::BeginPlay();
    if(!SurvivalDirector)for(TActorIterator<AActor> It(GetWorld());It;++It)
        if(It->GetClass()->FindPropertyByName(TEXT("CloneGeneration"))&&It->GetClass()->FindPropertyByName(TEXT("CrateScrap"))){SurvivalDirector=*It;break;}
    if(SurvivalDirector)AddTickPrerequisiteActor(SurvivalDirector);
    LastClone=int32(Read(SurvivalDirector,TEXT("CloneGeneration")));
    if(auto* C=UGameplayStatics::GetPlayerCharacter(this,0)) LastSafeLocation=C->GetActorLocation();
}
void ADustfallTerrainHazardDirector::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    auto* C=UGameplayStatics::GetPlayerCharacter(this,0);if(!C||!SurvivalDirector)return;
    auto RelocateCache=[&]()
    {
        if(auto* P=FindFProperty<FStructProperty>(SurvivalDirector->GetClass(),TEXT("CrateLocation")))
            if(P->Struct==TBaseStructure<FVector>::Get())*P->ContainerPtrToValuePtr<FVector>(SurvivalDirector)=LastSafeLocation-FVector(0,0,65);
        if(auto* F=SurvivalDirector->FindFunction(TEXT("RefreshRecoveryCache")))SurvivalDirector->ProcessEvent(F,nullptr);
        if(auto* F=SurvivalDirector->FindFunction(TEXT("SaveProgress")))SurvivalDirector->ProcessEvent(F,nullptr);
    };
    auto* Movement=C->GetCharacterMovement();
    int32 Clone=int32(Read(SurvivalDirector,TEXT("CloneGeneration")));
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
        if(C->GetActorLocation().Z < -20000)
        {
            Write(SurvivalDirector,TEXT("Integrity"),0);
            if(auto* F=SurvivalDirector->FindFunction(TEXT("RespawnClone")))SurvivalDirector->ProcessEvent(F,nullptr);
            RelocateCache();
            LastClone=int32(Read(SurvivalDirector,TEXT("CloneGeneration")));
            bRelocateCache=false;MaximumFallSpeed=0;bWasFalling=false;return;
        }
    }
    else if(bWasFalling)
    {
        LastImpactDamage=FMath::Max(0.f,MaximumFallSpeed-SafeImpactSpeed)*DamagePerExcessSpeed;
        if(LastImpactDamage>0)Write(SurvivalDirector,TEXT("Integrity"),FMath::Max(0.,Read(SurvivalDirector,TEXT("Integrity"))-LastImpactDamage));
        MaximumFallSpeed=0;
        if(Read(SurvivalDirector,TEXT("Integrity"))>0)bRelocateCache=false;
    }
    else if(Movement->IsMovingOnGround() && !bRelocateCache)
    {
        // Keep rim position until the landing has been evaluated, never a point mid-fall.
        LastSafeLocation=C->GetActorLocation();
    }
    bWasFalling=bFalling;
}
