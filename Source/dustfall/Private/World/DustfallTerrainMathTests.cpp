#if WITH_DEV_AUTOMATION_TESTS
#include "World/DustfallTerrainMath.h"
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallTerrainGeometryTest,"Dustfall.Core.Terrain.Geometry",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDustfallTerrainGeometryTest::RunTest(const FString& Parameters)
{
    using M=FDustfallTerrainMath;
    const TArray<FVector2D> Line={{0,0},{100,0},{100,100}};
    const auto P=M::Project(FVector2D(120,75),Line);
    TestEqual(TEXT("Projection retains accumulated arc"),P.Arc,175.);
    TestEqual(TEXT("Distance to second segment"),P.Distance,20.);
    TestEqual(TEXT("Right side is negative"),P.SignedDistance,-20.);
    TestTrue(TEXT("Arc sampling crosses segment boundary"),M::AtArc(Line,150).Equals(FVector2D(100,50)));
    const TArray<FVector2D> Duplicates={{0,0},{0,0},{100,0}};
    TestEqual(TEXT("Degenerate segment safely skipped"),M::Project(FVector2D(50,10),Duplicates).Arc,50.);
    const TArray<FVector2D> Wall={{0,0},{.6,.3},{.8,.3},{.9,1},{1,1}};
    TestEqual(TEXT("Strata ledge stays level"),M::Wall(.7,Wall),.3);
    TestTrue(TEXT("Upper face is steep"),(M::Wall(.9,Wall)-M::Wall(.8,Wall))/.1>6);
    TestEqual(TEXT("Floor clamps below footprint"),M::Wall(-1,Wall),0.);
    TestEqual(TEXT("Plateau clamps above footprint"),M::Wall(2,Wall),1.);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallTerrainGradeTest,"Dustfall.Core.Terrain.Grade",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDustfallTerrainGradeTest::RunTest(const FString& Parameters)
{
    const TArray<FVector2D> P={{0,0},{100,0},{200,0},{300,0}};
    TArray<double> Z={0,90,-80,30};
    TestTrue(TEXT("Feasible ramp preserves both endpoints"),FDustfallTerrainMath::LimitGrade(P,Z,.2,true));
    TestEqual(TEXT("Rim stays connected"),Z[0],0.); TestEqual(TEXT("Floor stays connected"),Z.Last(),30.);
    for (int32 I=1; I<Z.Num(); ++I) TestTrue(TEXT("All segments respect grade"),FMath::Abs(Z[I]-Z[I-1])<=20.00001);
    TArray<double> Impossible={0,0,0,100};
    TestFalse(TEXT("Insufficient switchback run is rejected"),FDustfallTerrainMath::LimitGrade(P,Impossible,.2,true));
    return true;
}
#endif
