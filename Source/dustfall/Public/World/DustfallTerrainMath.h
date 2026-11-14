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
    struct FSwitchback
    {
        TArray<FVector2D> Line;
        double Length = 0;
        double TurnRadius = 0;
        double LaneSpacing = 0;
        int32 Turns = 0;
        FString Error;
    };
    // Full cut-footprint corridor centred on anchor traverse, legs parallel to WallTangent.
    static FSwitchback Switchback(const FVector2D& Top, const FVector2D& Bottom,
        const FVector2D& WallTangent, double RequiredRun, double CorridorWidth,
        double MinimumRadius, double MinimumSpacing, double SampleStep);
    static double Smooth(double A, double B, double X);
    static FProjection Project(const FVector2D& Point, const TArray<FVector2D>& Line);
    // Continuous normal coordinates through bends; endpoint profiles extrapolate
    // into raster support instead of becoming flat caps at oblique endpoints.
    static FProjection ProjectTread(const FVector2D& Point, const TArray<FVector2D>& Line);
    // Exact arc intervals in disc/route capsule cores (including sub-sample grazes).
    static TArray<FVector2D> CoreIntervals(const TArray<FVector2D>& Line,
        const TArray<FVector>& Discs, const TArray<TArray<FVector2D>>& Routes, double RouteRadius);
    // Atomic solve between all baseline/junction pins. Optional smooth grade
    // transitions and sunken tread use only the remaining grade budget.
    static bool LimitPinnedGrade(const TArray<FVector2D>& Points, TArray<double>& Heights,
        double MaximumGrade, const TArray<bool>& Pinned, double TransitionRun = 0, double SinkDepth = 0);
    static FVector2D AtArc(const TArray<FVector2D>& Line, double Arc);
    // Knots are [normalised horizontal distance, normalised rise], including (0,0),(1,1).
    static double Wall(double T, const TArray<FVector2D>& Knots);
    // Deterministic feasible envelope. Optionally preserves both endpoints; false if impossible.
    static bool LimitGrade(const TArray<FVector2D>& Points, TArray<double>& Heights,
        double MaximumGrade, bool bPinEndpoints);
};
