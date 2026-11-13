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
