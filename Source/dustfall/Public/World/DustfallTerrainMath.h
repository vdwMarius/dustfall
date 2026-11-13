#pragma once
#include "CoreMinimal.h"

/** Pure centimetre-space terrain maths, independent of Landscape/editor state. */
struct DUSTFALL_API FDustfallTerrainMath
{
    struct FProjection
    {
        double Distance = TNumericLimits<double>::Max();
        double SignedDistance = 0;
        double Arc = 0;
        FVector2D Point = FVector2D::ZeroVector;
        FVector2D Tangent = FVector2D(1,0);
    };
    static double Smooth(double A, double B, double X);
    static FProjection Project(const FVector2D& Point, const TArray<FVector2D>& Line);
    static FVector2D AtArc(const TArray<FVector2D>& Line, double Arc);
    // Knots are [normalised horizontal distance, normalised rise], including (0,0),(1,1).
    static double Wall(double T, const TArray<FVector2D>& Knots);
    // Deterministic feasible envelope. Optionally preserves both endpoints; false if impossible.
    static bool LimitGrade(const TArray<FVector2D>& Points, TArray<double>& Heights,
        double MaximumGrade, bool bPinEndpoints);
};
