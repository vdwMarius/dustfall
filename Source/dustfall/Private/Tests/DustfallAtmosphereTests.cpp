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
    TestTrue(TEXT("Storm near 5m detail remains readable"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 500, 0, .51f, 1000, .96f), .453f, .001f));
    TestTrue(TEXT("Storm human detail is faint at 15m"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 1500, 0, .51f, 1000, .96f), .1005f, .001f));
    TestTrue(TEXT("Storm 150m silhouette floor includes near volumetric loss"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 15000, 0, .51f, 1000, .96f), .1005f, .001f));
    TestTrue(TEXT("Volumetric/analytic boundary has no transmission jump"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 999.99f, 0, .51f, 1000, .96f),
                            M::CombinedTransmittance(3.3f, 1000.01f, 0, .51f, 1000, .96f), .0001f));
    TestTrue(TEXT("Haze preserves far contrast"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(.6f, 15000, 0, .86f, 4000, .3f), .09767f, .001f));
    TestTrue(TEXT("Calm preserves far contrast"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(.3f, 15000, 0, .82f, 6000, .2f), .2284f, .001f));
    TestEqual(TEXT("Zero volumetric extent recovers analytic model"),
        M::CombinedTransmittance(3.3f, 1500, 50, .92f, 0, 1), M::HorizontalTransmittance(3.3f, 1500, 50, .92f));
    TestEqual(TEXT("Before fog start keeps full contrast"), M::HorizontalTransmittance(3.3f, 25, 50, .92f), 1.f);
    TestEqual(TEXT("Sheet centre has full shape opacity"), M::SheetEdge(.5f, .5f), 1.f);
    for (float V : {0.f, .25f, .5f, .75f, 1.f})
    {
        TestEqual(TEXT("Left border has hard zero"), M::SheetEdge(.04f, V), 0.f);
        TestEqual(TEXT("Right border has hard zero"), M::SheetEdge(.96f, V), 0.f);
        TestEqual(TEXT("Top border has hard zero"), M::SheetEdge(V, .04f), 0.f);
        TestEqual(TEXT("Bottom border has hard zero"), M::SheetEdge(V, .96f), 0.f);
    }
    return true;
}
#endif
