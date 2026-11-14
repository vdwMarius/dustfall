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
    TestTrue(TEXT("Dawn dusk symmetry"), FMath::IsNearlyEqual(M::Night(.25f, -.2f, .2f), M::Night(.75f, -.2f, .2f), 1.e-6f));
    TestEqual(TEXT("Clock wrap"), M::Night(1, -.2f, .2f), M::Night(0, -.2f, .2f));
    TestEqual(TEXT("Storm blend midpoint"), M::Weather(FVector(0, 2, 4), 1, .5f), 3.f);
    TestEqual(TEXT("Storm exit keeps tail"), M::Weather(FVector(0, 2, 4), 0, .5f), 2.f);
    TestEqual(TEXT("Storm blend clamps"), M::Weather(FVector(0, 2, 4), 2, 5), 4.f);
    TestEqual(TEXT("No fade on negative delta"), M::Approach(1, 0, 4, -1), 1.f);
    TestTrue(TEXT("Interior fade independent of subdivision"), FMath::IsNearlyEqual(M::Approach(1, 0, 4, 1),
        M::Approach(M::Approach(1, 0, 4, .5f), 0, 4, .5f), 1.e-6f));
    TestEqual(TEXT("Negative dust wrap"), M::Wrap(-12, 10), 8.f);
    TestEqual(TEXT("Positive dust wrap"), M::Wrap(12, 10), -8.f);
    // These are physical model predictions, not visual acceptance. Round-4 live
    // captures prove a .263 transmission floor can still yield ~0 sky contrast
    // when homogeneous source radiance dominates the very dim background.
    TestTrue(TEXT("Storm near 5m detail remains readable"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 500, 0, .40f, 1000, .5f), .662f, .001f));
    TestTrue(TEXT("Storm human detail is faint at 15m"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 1500, 0, .40f, 1000, .5f), .26294f, .001f));
    TestTrue(TEXT("Storm 150m silhouette floor includes near volumetric loss"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 15000, 0, .40f, 1000, .5f), .26294f, .001f));
    TestTrue(TEXT("Volumetric/analytic boundary has no transmission jump"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 999.99f, 0, .40f, 1000, .5f),
                            M::CombinedTransmittance(3.3f, 1000.01f, 0, .40f, 1000, .5f), .0001f));
    TestTrue(TEXT("Storm analytic cap is already reached at 15m"),
        FMath::IsNearlyEqual(M::CombinedTransmittance(3.3f, 1500, 0, .40f, 1000, .5f),
            M::CombinedTransmittance(3.3f, 15000, 0, .40f, 1000, .5f)));
    TestEqual(TEXT("Legacy component emissive includes renderer unit conversion"), M::EmissiveSetting(3.3f, .5f), 8.25f);
    for (float Source : {.018f, .24f, .34f})
    {
        for (float NearT : {1.f, .99f, .438f, .01f})
        {
            for (float FarT : {1.f, .999f, .6f})
                TestTrue(TEXT("Matched fog source composes to one radiance, day and night"),
                    FMath::IsNearlyEqual(M::MatchedRadiance(Source, NearT, FarT), Source * (1.f - NearT * FarT), .000001f));
        }
    }
    TestEqual(TEXT("Low dust disappears above 1.5m"), M::GroundHeightFade(150, 150), 0.f);
    TestTrue(TEXT("Low dust fades with height"), M::GroundHeightFade(25, 150) > M::GroundHeightFade(115, 150));
    TestEqual(TEXT("Storm streak reference length"), M::StreakLength(900, 900, .2f), 1.f);
    TestTrue(TEXT("Wind stretches streaks"), M::StreakLength(900, 900, .2f) > M::StreakLength(100, 900, .2f));
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
