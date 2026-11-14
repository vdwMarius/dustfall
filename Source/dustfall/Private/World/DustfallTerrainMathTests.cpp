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

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallTerrainSwitchbackTest,"Dustfall.Core.Terrain.Switchback",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDustfallTerrainSwitchbackTest::RunTest(const FString& Parameters)
{
    using M=FDustfallTerrainMath;
    const FVector2D Top(0,0), Bottom(10000,0), Wall(0,1);
    const double Drop=6000, Grade=.1, Required=Drop/Grade*1.01;
    const auto A=M::Switchback(Top,Bottom,Wall,Required,26000,1500,1600,100);
    const auto B=M::Switchback(Top,Bottom,Wall,Required,26000,1500,1600,100);
    TestTrue(TEXT("Safe corridor generates sufficient run"),A.Error.IsEmpty() && A.Length>=Required);
    if (A.Line.Num()<2) return false;
    TestTrue(TEXT("Multiple alternating hairpins generated"),A.Turns>1);
    TestTrue(TEXT("Top anchor preserved"),A.Line[0].Equals(Top));
    TestTrue(TEXT("Bottom anchor preserved"),A.Line.Last().Equals(Bottom));
    TestTrue(TEXT("Minimum turn radius respected"),A.TurnRadius>=1500);
    TestTrue(TEXT("Hairpin spacing supports tread and shoulders"),A.LaneSpacing>=1600);
    TestEqual(TEXT("Deterministic vertex count"),A.Line.Num(),B.Line.Num());
    double Arc=0;
    TArray<FVector2D> Legs;
    for (int32 I=0; I<A.Line.Num(); ++I)
    {
        TestTrue(TEXT("Deterministic geometry"),A.Line[I].Equals(B.Line[I],0));
        TestTrue(TEXT("Within configured corridor"),FMath::Abs(A.Line[I].Y)+800<=13000.00001);
        if (!I) continue;
        const FVector2D Segment=A.Line[I]-A.Line[I-1];
        if (FMath::Abs(Segment.X)<1.e-6 && FMath::Abs(Segment.Y)>100)
            Legs.Emplace(A.Line[I].X,Segment.Y);
        const double Run=Segment.Size();
        const double PreviousZ=Drop*(1-Arc/A.Length); Arc+=Run;
        const double Z=Drop*(1-Arc/A.Length);
        TestTrue(TEXT("Every generated profile segment meets grade"),FMath::Abs(Z-PreviousZ)/Run<=Grade);
        // All generated turns are circular. Check curvature from the actual
        // vertices, including straight/turn transitions, rather than metadata.
        if (I+1<A.Line.Num())
        {
            const FVector2D U=A.Line[I]-A.Line[I-1], V=A.Line[I+1]-A.Line[I];
            const double Cross=FMath::Abs(U.X*V.Y-U.Y*V.X);
            if (Cross>1.e-6)
            {
                const double Radius=U.Size()*V.Size()*(U+V).Size()/(2*Cross);
                TestTrue(TEXT("Actual turn radius is walkable"),Radius>=1499.9);
            }
        }
    }
    TestEqual(TEXT("One straight tread per lane"),Legs.Num(),A.Turns+1);
    for (int32 I=1; I<Legs.Num(); ++I)
    {
        TestTrue(TEXT("Actual adjacent legs have safe separation"),Legs[I].X-Legs[I-1].X>=1600);
        TestTrue(TEXT("Actual legs alternate direction"),Legs[I].Y*Legs[I-1].Y<0);
    }
    // Different wall direction and offset anchors still connect deterministically.
    const auto Offset=M::Switchback(FVector2D(53000,50500),FVector2D(44000,43500),
        FVector2D(.658,-.753),6000/.225*1.01,60000,1500,1600,100);
    TestTrue(TEXT("Shelf notch 60m drop solves automatically"),Offset.Error.IsEmpty() && Offset.Length>=6000/.225);
    const auto Invalid=M::Switchback(Top,Bottom,Wall,Required,1000,1500,1600,100);
    TestTrue(TEXT("Physically impossible corridor has actionable error"),!Invalid.Error.IsEmpty());
    return true;
}
#endif
