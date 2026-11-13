#pragma once

#include "CoreMinimal.h"
#include "Systems/DustfallModifierStack.h"

/** Pure suit maths shared by the director and world-free automation tests. */
struct DUSTFALL_API FDustfallSurvivalRules
{
    static double EffectiveRate(double Base, const FDustfallModifierStack& Stack)
    {
        return Stack.EvaluateDouble(Base);
    }

    static bool SetCapacityBonus(TMap<FName, double>& Bonuses, FName Source, double Bonus)
    {
        if (Source.IsNone() || !FMath::IsFinite(Bonus) || Bonus < 0.0) return false;
        Bonuses.Add(Source, Bonus);
        return true;
    }

    static double Capacity(double Base, const TMap<FName, double>& Bonuses)
    {
        double Result = FMath::IsFinite(Base) ? FMath::Max(0.0, Base) : 0.0;
        TArray<FName> Keys; Bonuses.GetKeys(Keys); Keys.Sort(FNameLexicalLess());
        for (FName Key : Keys)
        {
            const double Bonus = Bonuses[Key];
            if (FMath::IsFinite(Bonus) && Bonus >= 0.0)
                Result = Bonus > TNumericLimits<double>::Max() - Result
                    ? TNumericLimits<double>::Max() : Result + Bonus;
        }
        return Result;
    }
};
