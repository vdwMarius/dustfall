#include "World/DustfallTerrainMath.h"

double FDustfallTerrainMath::Smooth(double A, double B, double X)
{
    const double T = FMath::Clamp((X-A)/(B-A),0.,1.);
    return T*T*(3.-2.*T);
}
FDustfallTerrainMath::FProjection FDustfallTerrainMath::Project(const FVector2D& P, const TArray<FVector2D>& Line)
{
    FProjection Result;
    double Arc = 0;
    for (int32 I=1; I<Line.Num(); ++I)
    {
        const FVector2D D=Line[I]-Line[I-1];
        const double Length=D.Size();
        if (Length<=UE_SMALL_NUMBER) continue;
        const double T=FMath::Clamp(FVector2D::DotProduct(P-Line[I-1],D)/(Length*Length),0.,1.);
        const FVector2D Q=Line[I-1]+T*D;
        const double Distance=(P-Q).Size();
        if (Distance<Result.Distance)
        {
            Result.Distance=Distance; Result.Arc=Arc+T*Length; Result.Point=Q; Result.Tangent=D/Length;
            Result.SignedDistance=(D.X*(P-Q).Y-D.Y*(P-Q).X)/Length;
        }
        Arc+=Length;
    }
    return Result;
}
FVector2D FDustfallTerrainMath::AtArc(const TArray<FVector2D>& Line, double Arc)
{
    for (int32 I=1; I<Line.Num(); ++I)
    {
        const double Length=(Line[I]-Line[I-1]).Size();
        if (Arc<=Length && Length>UE_SMALL_NUMBER) return FMath::Lerp(Line[I-1],Line[I],FMath::Clamp(Arc/Length,0.,1.));
        Arc-=Length;
    }
    return Line.Last();
}
double FDustfallTerrainMath::Wall(double T, const TArray<FVector2D>& Knots)
{
    T=FMath::Clamp(T,0.,1.);
    for (int32 I=1; I<Knots.Num(); ++I)
        if (T<=Knots[I].X) return FMath::Lerp(Knots[I-1].Y,Knots[I].Y,
            FMath::Clamp((T-Knots[I-1].X)/(Knots[I].X-Knots[I-1].X),0.,1.));
    return Knots.Last().Y;
}
bool FDustfallTerrainMath::LimitGrade(const TArray<FVector2D>& Points, TArray<double>& Z, double Grade, bool bPin)
{
    if (Points.Num()!=Z.Num() || Z.Num()<2 || Grade<=0) return false;
    double Length=0;
    for (int32 I=1; I<Points.Num(); ++I) Length+=(Points[I]-Points[I-1]).Size();
    const double First=Z[0], Last=Z.Last();
    if (bPin && FMath::Abs(Last-First)>Grade*Length) return false;
    if (bPin)
    {
        double Arc=0;
        for (int32 I=0; I<Z.Num(); ++I)
        {
            if (I) Arc+=(Points[I]-Points[I-1]).Size();
            Z[I]=FMath::Clamp(Z[I], FMath::Max(First-Grade*Arc,Last-Grade*(Length-Arc)),
                FMath::Min(First+Grade*Arc,Last+Grade*(Length-Arc)));
        }
    }
    for (int32 I=1; I<Z.Num(); ++I)
    {
        const double Step=Grade*(Points[I]-Points[I-1]).Size();
        Z[I]=FMath::Clamp(Z[I],Z[I-1]-Step,Z[I-1]+Step);
    }
    for (int32 I=Z.Num()-2; I>=0; --I)
    {
        const double Step=Grade*(Points[I+1]-Points[I]).Size();
        Z[I]=FMath::Clamp(Z[I],Z[I+1]-Step,Z[I+1]+Step);
    }
    return !bPin || (FMath::IsNearlyEqual(Z[0],First,.001) && FMath::IsNearlyEqual(Z.Last(),Last,.001));
}

FDustfallTerrainMath::FSwitchback FDustfallTerrainMath::Switchback(
    const FVector2D& Top, const FVector2D& Bottom, const FVector2D& WallTangent,
    double RequiredRun, double CorridorWidth, double MinimumRadius,
    double MinimumSpacing, double SampleStep)
{
    FSwitchback Result;
    const FVector2D Along=WallTangent.GetSafeNormal();
    FVector2D Across(-Along.Y,Along.X);
    if (FVector2D::DotProduct(Bottom-Top,Across)<0) Across=-Across;
    const double Span=FVector2D::DotProduct(Bottom-Top,Across);
    const double Offset=FVector2D::DotProduct(Bottom-Top,Along);
    const double MinPitch=FMath::Max(2*MinimumRadius,MinimumSpacing);
    if (Along.IsNearlyZero() || MinPitch<=0 || SampleStep<=0 || Span<MinPitch || CorridorWidth<=MinPitch)
    {
        Result.Error=TEXT("Invalid switchback corridor: anchors must span at least one safe turn");
        return Result;
    }
    const int32 MaxTurns=FMath::FloorToInt(Span/MinPitch);
    for (int32 Turns=1; Turns<=MaxTurns; ++Turns)
    {
        const double Radius=Span/(2*Turns);
        // MinimumSpacing includes the complete cut footprint (tread, shoulders,
        // raster support), so reserve half at both corridor edges as well.
        const double Capacity=(CorridorWidth-MinimumSpacing)*.5-Radius-FMath::Abs(Offset)*.5;
        // Semicircle chords are slightly shorter than analytic arcs. Generate
        // only the run needed, with margin, while avoiding reversed short legs.
        const double HalfLeg=FMath::Max(FMath::Abs(Offset)/(2*Turns)+SampleStep,
            (RequiredRun*1.002-Turns*PI*Radius)/(2*Turns));
        if (HalfLeg<=0 || HalfLeg>Capacity) continue;
        TArray<FVector2D> Line;
        auto Add=[&](double X,double Y) { Line.Add(Top+Across*X+Along*Y); };
        Add(0,0);
        for (int32 I=0; I<Turns; ++I)
        {
            const double Sign=I%2==0?1.:-1.;
            const double CentreOffset=Offset*(I+.5)/Turns;
            const int32 Segments=FMath::Max(32,FMath::CeilToInt(PI*Radius/SampleStep));
            for (int32 J=0; J<=Segments; ++J)
            {
                const double Angle=PI*J/Segments;
                Add(2*Radius*I+Radius*(1-FMath::Cos(Angle)),CentreOffset+Sign*(HalfLeg+Radius*FMath::Sin(Angle)));
            }
        }
        Add(Span,Offset);
        double Run=0;
        for (int32 I=1; I<Line.Num(); ++I) Run+=(Line[I]-Line[I-1]).Size();
        if (Run>=RequiredRun)
        {
            Result.Line=MoveTemp(Line); Result.Length=Run; Result.TurnRadius=Radius;
            Result.LaneSpacing=2*Radius; Result.Turns=Turns;
            return Result;
        }
    }
    Result.Error=TEXT("Safe hairpins cannot fit corridor/anchor span; widen corridor or move anchors");
    return Result;
}
