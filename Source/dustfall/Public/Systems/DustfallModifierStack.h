#pragma once
#include "CoreMinimal.h"

/** Named, multiplicative modifiers. Invalid updates leave the previous value intact. */
struct DUSTFALL_API FDustfallModifierStack
{
    bool Set(FName Source, float Multiplier)
    {
        if (Source.IsNone() || !FMath::IsFinite(Multiplier) || Multiplier < 0) return false;
        Modifiers.Add(Source, Multiplier); return true;
    }
    void Clear(FName Source) { Modifiers.Remove(Source); }
    float Evaluate(float Base) const
    {
        if (!FMath::IsFinite(Base) || Base <= 0) return 0;
        TArray<FName> Keys; Modifiers.GetKeys(Keys); Keys.Sort(FNameLexicalLess());
        for (FName Key : Keys) if (Modifiers[Key] == 0) return 0;
        double Result = Base;
        for (FName Key : Keys) Result *= Modifiers[Key];
        return float(FMath::Min(Result, double(MAX_flt)));
    }
private:
    TMap<FName, float> Modifiers;
};
