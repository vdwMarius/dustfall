#include "DustfallSurvivalLibrary.h"

double UDustfallSurvivalLibrary::IntegrateResource(double Current, double RatePerSecond,
    double DeltaSeconds, double Maximum)
{
    const double Capacity = FMath::IsFinite(Maximum) ? FMath::Max(0.0, Maximum) : 0.0;
    const double Value = FMath::IsFinite(Current) ? FMath::Clamp(Current, 0.0, Capacity) : 0.0;
    if (!FMath::IsFinite(RatePerSecond) || !FMath::IsFinite(DeltaSeconds) || DeltaSeconds <= 0.0)
    {
        return Value;
    }
    const double Integrated = Value + RatePerSecond * DeltaSeconds;
    if (!FMath::IsFinite(Integrated))
    {
        return RatePerSecond > 0.0 ? Capacity : 0.0;
    }
    return FMath::Clamp(Integrated, 0.0, Capacity);
}

bool UDustfallSurvivalLibrary::IsWithinHabitat(FVector Point, FVector Origin, FVector HalfExtent)
{
    if (Point.ContainsNaN() || Origin.ContainsNaN() || HalfExtent.ContainsNaN()
        || HalfExtent.X < 0.0 || HalfExtent.Y < 0.0 || HalfExtent.Z < 0.0)
    {
        return false;
    }
    const FVector Offset = (Point - Origin).GetAbs();
    return Offset.X <= HalfExtent.X && Offset.Y <= HalfExtent.Y && Offset.Z <= HalfExtent.Z;
}

bool UDustfallSurvivalLibrary::UpdateSprintExhaustion(double CurrentStamina, double StaminaBeforeTick,
    bool bWasExhausted, double RecoveryThreshold)
{
    if (!FMath::IsFinite(CurrentStamina) || !FMath::IsFinite(StaminaBeforeTick))
    {
        return true;
    }
    const double Threshold = FMath::IsFinite(RecoveryThreshold) ? FMath::Max(0.0, RecoveryThreshold) : 25.0;
    return CurrentStamina <= 0.0 || StaminaBeforeTick <= 0.0 || (bWasExhausted && CurrentStamina < Threshold);
}
