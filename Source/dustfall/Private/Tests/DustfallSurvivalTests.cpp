#if WITH_DEV_AUTOMATION_TESTS

#include "Systems/DustfallSurvivalRules.h"
#include "DustfallSurvivalLibrary.h"
#include "Misc/AutomationTest.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallSuitModifierTest, "Dustfall.Core.SurvivalModifiers",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDustfallSuitModifierTest::RunTest(const FString& Parameters)
{
    FDustfallModifierStack Stack;
    using Rules = FDustfallSurvivalRules;
    using Core = UDustfallSurvivalLibrary;
    // Use a non-float-exact base to catch accidental precision loss in the empty stack.
    const double Base = 0.12;
    TestEqual(TEXT("Empty stack preserves double base exactly"), Rules::EffectiveRate(Base, Stack), Base);
    TestEqual(TEXT("Unmodified drain matches legacy integration"),
        Core::IntegrateResource(80, -Rules::EffectiveRate(Base, Stack), 3, 100),
        Core::IntegrateResource(80, -Base, 3, 100));
    TestTrue(TEXT("Weather multiplier accepted"), Stack.Set(TEXT("Weather"), 2.f));
    TestTrue(TEXT("Upgrade multiplier accepted"), Stack.Set(TEXT("Upgrade"), 0.5f));
    TestEqual(TEXT("Sources multiply"), Rules::EffectiveRate(Base, Stack), Base);
    TestFalse(TEXT("Negative modifier rejected"), Stack.Set(TEXT("Weather"), -1.f));
    TestFalse(TEXT("NaN modifier rejected"), Stack.Set(TEXT("Weather"), std::numeric_limits<float>::quiet_NaN()));
    TestFalse(TEXT("Infinite modifier rejected"), Stack.Set(TEXT("Weather"), std::numeric_limits<float>::infinity()));
    TestFalse(TEXT("Unnamed modifier rejected"), Stack.Set(NAME_None, 2.f));
    TestEqual(TEXT("Invalid update preserves previous modifiers"), Rules::EffectiveRate(Base, Stack), Base);
    Stack.Clear(TEXT("Upgrade"));
    TestEqual(TEXT("Clearing removes only one source"), Rules::EffectiveRate(Base, Stack), Base * 2.0);
    Stack.Set(TEXT("Weather"), 3.f);
    TestEqual(TEXT("Same source replaces multiplier"), Rules::EffectiveRate(Base, Stack), Base * 3.0);
    Stack.Set(TEXT("Shelter"), 0.f);
    TestEqual(TEXT("Zero multiplier stops drain"), Rules::EffectiveRate(Base, Stack), 0.0);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDustfallSuitCapacityTest, "Dustfall.Core.SurvivalCapacity",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDustfallSuitCapacityTest::RunTest(const FString& Parameters)
{
    TMap<FName, double> Bonuses;
    using Rules = FDustfallSurvivalRules;
    using Core = UDustfallSurvivalLibrary;
    TestEqual(TEXT("No bonus preserves capacity"), Rules::Capacity(100, Bonuses), 100.0);
    TestTrue(TEXT("Upgrade capacity accepted"), Rules::SetCapacityBonus(Bonuses, TEXT("Tank"), 40));
    Rules::SetCapacityBonus(Bonuses, TEXT("Lining"), 10);
    TestEqual(TEXT("Independent capacities add above 100"), Rules::Capacity(100, Bonuses), 150.0);
    TestEqual(TEXT("Refill clamps at upgraded maximum"), Core::IntegrateResource(149, 8, 1, Rules::Capacity(100, Bonuses)), 150.0);
    TestFalse(TEXT("Negative bonus rejected"), Rules::SetCapacityBonus(Bonuses, TEXT("Tank"), -5));
    TestFalse(TEXT("NaN bonus rejected"), Rules::SetCapacityBonus(Bonuses, TEXT("Tank"), std::numeric_limits<double>::quiet_NaN()));
    TestFalse(TEXT("Infinite bonus rejected"), Rules::SetCapacityBonus(Bonuses, TEXT("Tank"), std::numeric_limits<double>::infinity()));
    TestFalse(TEXT("Unnamed bonus rejected"), Rules::SetCapacityBonus(Bonuses, NAME_None, 5));
    TestEqual(TEXT("Invalid bonus preserves previous value"), Rules::Capacity(100, Bonuses), 150.0);
    Rules::SetCapacityBonus(Bonuses, TEXT("Tank"), 20);
    TestEqual(TEXT("Same source replaces bonus"), Rules::Capacity(100, Bonuses), 130.0);
    Rules::SetCapacityBonus(Bonuses, TEXT("Tank"), 0);
    TestEqual(TEXT("Zero clears a source bonus"), Rules::Capacity(100, Bonuses), 110.0);
    TestEqual(TEXT("Bad base capacity clamps to zero"), Rules::Capacity(-5, TMap<FName, double>()), 0.0);
    Rules::SetCapacityBonus(Bonuses, TEXT("LargeA"), TNumericLimits<double>::Max());
    Rules::SetCapacityBonus(Bonuses, TEXT("LargeB"), TNumericLimits<double>::Max());
    TestEqual(TEXT("Capacity sum saturates to finite maximum"), Rules::Capacity(100, Bonuses), TNumericLimits<double>::Max());
    return true;
}

#endif
