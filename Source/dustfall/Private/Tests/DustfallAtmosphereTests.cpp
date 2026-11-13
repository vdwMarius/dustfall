#if WITH_DEV_AUTOMATION_TESTS
#include "World/DustfallAtmosphereMath.h"
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallAtmosphereBlendTest, "Dustfall.Core.AtmosphereBlends",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FDustfallAtmosphereBlendTest::RunTest(const FString& Parameters)
{
    using M = FDustfallAtmosphereMath;
    TestEqual(TEXT("Midnight floor"), M::Night(0, -.2f, .2f), 1.f);
    TestEqual(TEXT("Noon has no night correction"), M::Night(.5f, -.2f, .2f), 0.f);
    TestTrue(TEXT("Dawn dusk symmetry"), FMath::IsNearlyEqual(M::Night(.25f, -.2f, .2f), M::Night(.75f, -.2f, .2f)));
    TestEqual(TEXT("Clock wrap"), M::Night(1, -.2f, .2f), M::Night(0, -.2f, .2f));
    TestEqual(TEXT("Storm blend midpoint"), M::Weather(FVector(0, 2, 4), 1, .5f), 3.f);
    TestEqual(TEXT("Storm exit keeps tail"), M::Weather(FVector(0, 2, 4), 0, .5f), 2.f);
    TestEqual(TEXT("Storm blend clamps"), M::Weather(FVector(0, 2, 4), 2, 5), 4.f);
    TestEqual(TEXT("No fade on negative delta"), M::Approach(1, 0, 4, -1), 1.f);
    TestTrue(TEXT("Interior fade independent of subdivision"), FMath::IsNearlyEqual(M::Approach(1, 0, 4, 1),
        M::Approach(M::Approach(1, 0, 4, .5f), 0, 4, .5f)));
    TestEqual(TEXT("Negative dust wrap"), M::Wrap(-12, 10), 8.f);
    TestEqual(TEXT("Positive dust wrap"), M::Wrap(12, 10), -8.f);
    TestTrue(TEXT("Storm detail around ten percent at 15m at reference height"),
        FMath::IsNearlyEqual(M::HorizontalTransmittance(3.3f, 1500, 50, .92f), .10f, .002f));
    TestTrue(TEXT("Far silhouette retains eight percent contrast"),
        FMath::IsNearlyEqual(M::HorizontalTransmittance(3.3f, 15000, 50, .92f), .08f));
    TestEqual(TEXT("Before fog start keeps full contrast"), M::HorizontalTransmittance(3.3f, 25, 50, .92f), 1.f);
    return true;
}
#endif
