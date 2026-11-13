#if WITH_DEV_AUTOMATION_TESTS
#include "Systems/DustfallModifierStack.h"
#include "Systems/DustfallExplorationSave.h"
#include "Systems/DustfallExplorationDirector.h"
#include "Misc/AutomationTest.h"
#include "UObject/UnrealType.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallModifierTest, "Dustfall.Core.ModifierStack",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDustfallModifierTest::RunTest(const FString& Parameters)
{
    FDustfallModifierStack Stack;
    TestEqual(TEXT("Empty stack"),Stack.Evaluate(2),2.f);
    TestTrue(TEXT("Set weather"),Stack.Set(TEXT("Weather"),2));
    Stack.Set(TEXT("Suit"),3);
    TestEqual(TEXT("Multiplication"),Stack.Evaluate(2),12.f);
    Stack.Set(TEXT("Weather"),4);
    TestEqual(TEXT("Replace source"),Stack.Evaluate(2),24.f);
    TestFalse(TEXT("Reject negative"),Stack.Set(TEXT("Weather"),-1));
    TestFalse(TEXT("Reject NaN"),Stack.Set(TEXT("Weather"),std::numeric_limits<float>::quiet_NaN()));
    TestFalse(TEXT("Reject infinity"),Stack.Set(TEXT("Weather"),std::numeric_limits<float>::infinity()));
    TestFalse(TEXT("Reject unnamed"),Stack.Set(NAME_None,2));
    TestEqual(TEXT("Rejected updates retain previous multiplier"),Stack.Evaluate(2),24.f);
    Stack.Clear(TEXT("Weather"));
    TestEqual(TEXT("Clear source"),Stack.Evaluate(2),6.f);
    TestEqual(TEXT("Reject negative base"),Stack.Evaluate(-2),0.f);
    TestEqual(TEXT("Reject NaN base"),Stack.Evaluate(std::numeric_limits<float>::quiet_NaN()),0.f);
    Stack.Set(TEXT("OverflowA"),MAX_flt); Stack.Set(TEXT("OverflowB"),MAX_flt);
    TestEqual(TEXT("Overflow stays finite"),Stack.Evaluate(MAX_flt),MAX_flt);
    Stack.Set(TEXT("Suit"),0);
    TestEqual(TEXT("Zero modifier"),Stack.Evaluate(2),0.f);
    Stack.Clear(TEXT("OverflowA")); Stack.Clear(TEXT("OverflowB"));
    Stack.Set(TEXT("Suit"),(.035f+.08f)/.035f);
    TestTrue(TEXT("Low suit preserves old rate"),FMath::IsNearlyEqual(Stack.Evaluate(.035f),.115f));
    Stack.Clear(TEXT("Suit")); Stack.Set(TEXT("Weather"),1+.045f/.035f);
    TestTrue(TEXT("Storm preserves old rate"),FMath::IsNearlyEqual(Stack.Evaluate(.035f),.08f));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallSaveMigrationTest, "Dustfall.Core.ExplorationSaveMigration",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDustfallSaveMigrationTest::RunTest(const FString& Parameters)
{
    auto* Input=NewObject<UDustfallExplorationSave>();
    auto* Output=NewObject<UDustfallExplorationSave>();
    Input->Version=2; Input->Beacons={FVector(1,2,3),FVector(4,5,6)};
    Input->Inventory.Add(TEXT("Scrap"),7); Input->RecoveryInventory.Add(TEXT("Wiring"),3);
    TestTrue(TEXT("v2 migration accepted"),UDustfallExplorationSave::ValidateAndMigrate(*Input,*Output));
    TestEqual(TEXT("Emits schema 3"),Output->Version,3);
    TestEqual(TEXT("Input stays v2"),Input->Version,2);
    TestEqual(TEXT("Two migrated records"),Output->BeaconRecords.Num(),2);
    TestTrue(TEXT("New valid distinct IDs"),Output->BeaconRecords[0].Id.IsValid() && Output->BeaconRecords[0].Id!=Output->BeaconRecords[1].Id);
    TestEqual(TEXT("Location preserved"),Output->BeaconRecords[1].Location,Input->Beacons[1]);
    TestEqual(TEXT("Payload preserved"),Output->Inventory.FindRef(TEXT("Scrap")),7);
    TestTrue(TEXT("Old save has default timestamp"),Output->SavedAt==FDateTime());
    Input->SavedAt=FDateTime(2026,11,13,21,14,7);
    TestTrue(TEXT("Timestamp migration accepted"),UDustfallExplorationSave::ValidateAndMigrate(*Input,*Output));
    TestTrue(TEXT("Timestamp copied"),Output->SavedAt==Input->SavedAt);
    const FGuid InitialId=Output->BeaconRecords[0].Id;
    TestTrue(TEXT("v3 round trip in place"),UDustfallExplorationSave::ValidateAndMigrate(*Output,*Output));
    TestEqual(TEXT("Stable ID retained"),Output->BeaconRecords[0].Id,InitialId);
    TestTrue(TEXT("Timestamp retained in place"),Output->SavedAt==Input->SavedAt);
    FFloatProperty* Strain=FindFProperty<FFloatProperty>(UDustfallExplorationSave::StaticClass(),TEXT("PrivateStrain"));
    if (!TestNotNull(TEXT("Private strain property exists"),Strain)) return false;
    double UDustfallExplorationSave::* Resources[]={&UDustfallExplorationSave::Oxygen,&UDustfallExplorationSave::Power,
        &UDustfallExplorationSave::Integrity,&UDustfallExplorationSave::Stamina};
    for (auto Resource : Resources)
    {
        Input->*Resource=-5;
        TestTrue(TEXT("Negative resource accepted"),UDustfallExplorationSave::ValidateAndMigrate(*Input,*Output));
        TestEqual(TEXT("Negative resource clamps to zero"),Output->*Resource,0.0);
        Input->*Resource=150;
        TestTrue(TEXT("Upgraded resource accepted"),UDustfallExplorationSave::ValidateAndMigrate(*Input,*Output));
        TestEqual(TEXT("Upgraded resource preserved"),Output->*Resource,150.0);
        Input->*Resource=100;
    }
    for (float Value : {-5.f,150.f})
    {
        Strain->SetPropertyValue_InContainer(Input,Value);
        TestTrue(TEXT("Finite strain accepted"),UDustfallExplorationSave::ValidateAndMigrate(*Input,*Output));
        TestEqual(TEXT("Strain clamped"),Strain->GetPropertyValue_InContainer(Output),Value<0 ? 0.f : 100.f);
    }
    Strain->SetPropertyValue_InContainer(Input,0.f);
    for (float Value : {-1.f,2.f,std::numeric_limits<float>::quiet_NaN(),std::numeric_limits<float>::infinity()})
    {
        Input->SymptomIntensity=Value;
        TestTrue(TEXT("Intensity accepted"),UDustfallExplorationSave::ValidateAndMigrate(*Input,*Output));
        TestEqual(TEXT("Intensity normalized"),Output->SymptomIntensity,Value==2.f ? 1.f : 0.f);
    }
    Input->SymptomIntensity=0.5f; Input->CloneGeneration=0;
    TestTrue(TEXT("Low clone generation accepted in place"),UDustfallExplorationSave::ValidateAndMigrate(*Input,*Input));
    TestEqual(TEXT("Clone generation clamps to one"),Input->CloneGeneration,1);
    TestEqual(TEXT("In-range intensity preserved"),Input->SymptomIntensity,0.5f);
    Input->Version=2;
    const FGuid Id=Output->BeaconRecords[0].Id;
    auto Reject=[&](const TCHAR* Label)
    {
        TestFalse(Label,UDustfallExplorationSave::ValidateAndMigrate(*Input,*Output));
        TestEqual(TEXT("Rejected load leaves output payload"),Output->Inventory.FindRef(TEXT("Scrap")),7);
        TestEqual(TEXT("Rejected load leaves output ID"),Output->BeaconRecords[0].Id,Id);
    };
    Input->Version=1; Reject(TEXT("Reject old version"));
    Input->Version=4; Reject(TEXT("Reject future version")); Input->Version=2;
    Input->Inventory[TEXT("Scrap")]=-1; Reject(TEXT("Reject negative quantity")); Input->Inventory[TEXT("Scrap")]=7;
    Input->RecoveryInventory[TEXT("Wiring")]=0; Reject(TEXT("Reject zero quantity")); Input->RecoveryInventory[TEXT("Wiring")]=3;
    for (auto Resource : Resources)
    {
        Input->*Resource=std::numeric_limits<double>::quiet_NaN(); Reject(TEXT("Reject NaN resource"));
        Input->*Resource=std::numeric_limits<double>::infinity(); Reject(TEXT("Reject infinite resource"));
        Input->*Resource=100;
    }
    Strain->SetPropertyValue_InContainer(Input,std::numeric_limits<float>::quiet_NaN()); Reject(TEXT("Reject NaN strain"));
    Strain->SetPropertyValue_InContainer(Input,std::numeric_limits<float>::infinity()); Reject(TEXT("Reject infinite strain"));
    Strain->SetPropertyValue_InContainer(Input,0.f);
    Input->Inventory.Add(NAME_None,1); Reject(TEXT("Reject unnamed item")); Input->Inventory.Remove(NAME_None);
    Input->Beacons[0].X=std::numeric_limits<double>::infinity(); Reject(TEXT("Reject infinite beacon")); Input->Beacons[0]=FVector::ZeroVector;
    Input->PlayerLocation.X=std::numeric_limits<double>::quiet_NaN(); Reject(TEXT("Reject NaN position")); Input->PlayerLocation=FVector::ZeroVector;
    Input->Version=3; Input->BeaconRecords=Output->BeaconRecords; Input->BeaconRecords[1].Id=Id; Reject(TEXT("Reject duplicate IDs"));
    Input->BeaconRecords[1].Id.Invalidate(); Reject(TEXT("Reject invalid ID"));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallPayloadTest, "Dustfall.Core.PayloadOverflow",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDustfallPayloadTest::RunTest(const FString& Parameters)
{
    TMap<FName,int32> Target={{TEXT("Scrap"),MAX_int32-2}};
    const TMap<FName,int32> Source={{TEXT("Scrap"),10},{TEXT("Wiring"),3},{TEXT("Glass"),-1},{NAME_None,8}};
    ADustfallExplorationDirector::MergePayload(Target,Source);
    TestEqual(TEXT("Overflow saturates"),Target.FindRef(TEXT("Scrap")),MAX_int32);
    TestEqual(TEXT("Other payload transfers"),Target.FindRef(TEXT("Wiring")),3);
    TestFalse(TEXT("Invalid payload ignored"),Target.Contains(TEXT("Glass")) || Target.Contains(NAME_None));
    return true;
}
#endif
