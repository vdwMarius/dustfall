#if WITH_DEV_AUTOMATION_TESTS

#include "DustfallSurvivalLibrary.h"
#include "Misc/AutomationTest.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallResourceTest, "Dustfall.Core.ResourceIntegration",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDustfallResourceTest::RunTest(const FString& Parameters)
{
    using Core = UDustfallSurvivalLibrary;
    TestEqual(TEXT("Outside drain uses seconds"), Core::IntegrateResource(80, -2, 3, 100), 74.0);
    TestEqual(TEXT("Refill stops at capacity"), Core::IntegrateResource(95, 8, 3, 100), 100.0);
    TestEqual(TEXT("Depletion stops at zero"), Core::IntegrateResource(1, -8, 3, 100), 0.0);
    TestEqual(TEXT("Negative time cannot refill"), Core::IntegrateResource(80, -2, -3, 100), 80.0);
    TestEqual(TEXT("Invalid capacity is safe"), Core::IntegrateResource(80, 2, 3, -1), 0.0);
    TestEqual(TEXT("Invalid rate cannot corrupt state"), Core::IntegrateResource(80,
        std::numeric_limits<double>::quiet_NaN(), 3, 100), 80.0);
    double Split = 80;
    for (int32 Index = 0; Index < 30; ++Index)
    {
        Split = Core::IntegrateResource(Split, -2, 0.1, 100);
    }
    TestTrue(TEXT("Rate is independent of frame subdivision"), FMath::IsNearlyEqual(Split, 74.0, 0.000001));
    TestTrue(TEXT("Zero before refill enters exhaustion"), Core::UpdateSprintExhaustion(0.2, 0, false, 25));
    TestTrue(TEXT("Exhaustion persists below threshold"), Core::UpdateSprintExhaustion(24, 23, true, 25));
    TestFalse(TEXT("Recovered suit releases exhaustion"), Core::UpdateSprintExhaustion(25, 24, true, 25));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallHabitatTest, "Dustfall.Core.HabitatBoundary",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDustfallHabitatTest::RunTest(const FString& Parameters)
{
    using Core = UDustfallSurvivalLibrary;
    const FVector Origin(100, 200, 300);
    const FVector HalfExtent(475, 325, 185);
    TestTrue(TEXT("Interior is sanctuary"), Core::IsWithinHabitat(Origin, Origin, HalfExtent));
    TestTrue(TEXT("Boundary is inclusive"), Core::IsWithinHabitat(Origin + HalfExtent, Origin, HalfExtent));
    TestFalse(TEXT("Airlock beyond shell is exterior"), Core::IsWithinHabitat(Origin + FVector(750, 0, 0), Origin, HalfExtent));
    TestFalse(TEXT("Negative extent is invalid"), Core::IsWithinHabitat(Origin, Origin, FVector(-1, 2, 3)));
    return true;
}

#endif
