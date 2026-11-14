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
FDustfallTerrainMath::FProjection FDustfallTerrainMath::ProjectTread(
    const FVector2D& P, const TArray<FVector2D>& Line)
{
    FProjection Result;
    if (Line.Num()<2) return Result;
    auto Tangent=[&](int32 I)
    {
        if (I==0) return (Line[1]-Line[0]).GetSafeNormal();
        if (I==Line.Num()-1) return (Line[I]-Line[I-1]).GetSafeNormal();
        return ((Line[I]-Line[I-1]).GetSafeNormal()+(Line[I+1]-Line[I]).GetSafeNormal()).GetSafeNormal();
    };
    double Arc=0;
    for (int32 I=1; I<Line.Num(); ++I)
    {
        const FVector2D D=Line[I]-Line[I-1], R=P-Line[I-1];
        const double Run=D.Size();
        if (Run<=UE_SMALL_NUMBER) continue;
        const FVector2D A=Tangent(I-1), B=Tangent(I)-A;
        const double C0=FVector2D::DotProduct(R,A);
        const double C1=FVector2D::DotProduct(R,B)-FVector2D::DotProduct(D,A);
        const double C2=-FVector2D::DotProduct(D,B);
        auto Consider=[&](double T, bool bExtension)
        {
            if (!FMath::IsFinite(T) || (!bExtension && (T<-1.e-8 || T>1+1.e-8))) return;
            if (!bExtension) T=FMath::Clamp(T,0.,1.);
            const FVector2D Q=Line[I-1]+D*T;
            const double Distance=(P-Q).Size();
            if (Distance>=Result.Distance) return;
            Result.Distance=Distance; Result.Point=Q; Result.Arc=Arc+T*Run;
            Result.Tangent=(A+B*FMath::Clamp(T,0.,1.)).GetSafeNormal();
            Result.SignedDistance=Result.Tangent.X*(P-Q).Y-Result.Tangent.Y*(P-Q).X;
        };
        if (FMath::Abs(C2)<1.e-10)
        {
            if (FMath::Abs(C1)>1.e-10) Consider(-C0/C1,false);
        }
        else
        {
            const double Disc=C1*C1-4*C2*C0;
            if (Disc>=0)
            {
                // Stable quadratic formula also retains the small root on long legs.
                const double Q=-.5*(C1+(C1>=0?1.:-1.)*FMath::Sqrt(Disc));
                if (FMath::Abs(Q)>1.e-10) { Consider(Q/C2,false); Consider(C0/Q,false); }
                else Consider(-C1/(2*C2),false);
            }
        }
        if (I==1 && C0<0) Consider(C0/Run,true);
        const FVector2D EndT=Tangent(I);
        const double Beyond=FVector2D::DotProduct(P-Line[I],EndT);
        if (I==Line.Num()-1 && Beyond>0) Consider(1+Beyond/Run,true);
        Arc+=Run;
    }
    return Result.Distance<TNumericLimits<double>::Max()?Result:Project(P,Line);
}

bool FDustfallTerrainMath::IsTreadArcSupported(double Arc, double Total, double EndpointSupport)
{
    return FMath::IsFinite(Arc) && Arc>=-EndpointSupport && Arc<=Total+EndpointSupport;
}

TArray<FVector2D> FDustfallTerrainMath::CoreIntervals(const TArray<FVector2D>& Line,
    const TArray<FVector>& Discs, const TArray<TArray<FVector2D>>& Routes, double RouteRadius)
{
    TArray<FVector2D> Intervals; double Arc=0;
    for (int32 I=1; I<Line.Num(); ++I)
    {
        const FVector2D P=Line[I-1], D=Line[I]-P; const double Run=D.Size();
        if (Run<=UE_SMALL_NUMBER) continue;
        auto Add=[&](double From,double To)
        {
            From=FMath::Max(0.,From); To=FMath::Min(1.,To);
            if (From<=To) Intervals.Emplace(Arc+From*Run,Arc+To*Run);
        };
        auto Disc=[&](const FVector2D& Centre,double Radius)
        {
            const FVector2D R=P-Centre;
            const double B=FVector2D::DotProduct(R,D), C=R.SizeSquared()-Radius*Radius;
            const double Discriminant=B*B-Run*Run*C;
            if (Discriminant<0) return;
            const double Root=FMath::Sqrt(Discriminant);
            Add((-B-Root)/(Run*Run),(-B+Root)/(Run*Run));
        };
        for (const FVector& C:Discs) Disc(FVector2D(C.X,C.Y),C.Z);
        for (const auto& Route:Routes) for (int32 J=1; J<Route.Num(); ++J)
        {
            Disc(Route[J-1],RouteRadius); Disc(Route[J],RouteRadius);
            const FVector2D Leg=Route[J]-Route[J-1]; const double Length=Leg.Size();
            if (Length<=UE_SMALL_NUMBER) continue;
            const FVector2D T=Leg/Length,N(-T.Y,T.X),R=P-Route[J-1];
            double From=0,To=1;
            auto Clip=[&](double Origin,double Direction,double Low,double High)
            {
                if (FMath::Abs(Direction)<1.e-10) return Origin>=Low && Origin<=High;
                const double A=(Low-Origin)/Direction,B=(High-Origin)/Direction;
                From=FMath::Max(From,FMath::Min(A,B)); To=FMath::Min(To,FMath::Max(A,B));
                return From<=To;
            };
            if (Clip(FVector2D::DotProduct(R,T),FVector2D::DotProduct(D,T),0,Length) &&
                Clip(FVector2D::DotProduct(R,N),FVector2D::DotProduct(D,N),-RouteRadius,RouteRadius)) Add(From,To);
        }
        Arc+=Run;
    }
    Intervals.Sort([](const FVector2D& A,const FVector2D& B){return A.X==B.X?A.Y<B.Y:A.X<B.X;});
    TArray<FVector2D> Merged;
    for (const FVector2D& Range:Intervals)
    {
        if (!Merged.IsEmpty() && Range.X<=Merged.Last().Y+1.e-6) Merged.Last().Y=FMath::Max(Merged.Last().Y,Range.Y);
        else Merged.Add(Range);
    }
    return Merged;
}

bool FDustfallTerrainMath::LimitPinnedGrade(const TArray<FVector2D>& Points,
    TArray<double>& Heights, double MaximumGrade, const TArray<bool>& Pinned, double TransitionRun, double SinkDepth)
{
    if (Points.Num()!=Heights.Num() || Pinned.Num()!=Points.Num() || Points.Num()<2) return false;
    TArray<double> Solved=Heights;
    int32 First=0;
    for (int32 Last=1; Last<Points.Num(); ++Last)
    {
        if (!Pinned[Last] && Last!=Points.Num()-1) continue;
        TArray<FVector2D> Segment; TArray<double> Z;
        for (int32 I=First; I<=Last; ++I) { Segment.Add(Points[I]); Z.Add(Solved[I]); }
        if (!LimitGrade(Segment,Z,MaximumGrade,true)) return false;
        if (TransitionRun>0 && Last>First+1)
        {
            double Run=0;
            for (int32 I=1; I<Segment.Num(); ++I) Run+=(Segment[I]-Segment[I-1]).Size();
            if (Run<=UE_SMALL_NUMBER) return false;
            const double Drop=Z.Last()-Z[0], Top=Z[0];
            // Integrate a smoothstep derivative: zero slope at each pinned
            // landing, constant grade between ramps. Reserve enough area to
            // preserve both pins without exceeding MaximumGrade.
            const double Ramp=FMath::Min3(TransitionRun,Run*.5,
                FMath::Max(0.,Run-FMath::Abs(Drop)/MaximumGrade)*.9);
            auto Integral=[&](double X)
            {
                if (Ramp<=UE_SMALL_NUMBER) return X;
                auto Edge=[&](double T){return Ramp*(T*T*T-.5*T*T*T*T);};
                if (X<Ramp) return Edge(X/Ramp);
                if (X>Run-Ramp) return Run-Ramp-Edge((Run-X)/Ramp);
                return X-Ramp*.5;
            };
            // A sunken tread is a target; constrain its smooth entrance/exit
            // depression by the remaining grade budget rather than losing pins.
            const double Sink=FMath::Min(FMath::Max(0.,SinkDepth),
                FMath::Max(0.,MaximumGrade-FMath::Abs(Drop)/(Run-Ramp))*Ramp/1.5);
            double Arc=0;
            for (int32 I=0; I<Z.Num(); ++I)
            {
                if (I) Arc+=(Segment[I]-Segment[I-1]).Size();
                const double Cut=Ramp>UE_SMALL_NUMBER?Sink*Smooth(0,Ramp,Arc)*Smooth(0,Ramp,Run-Arc):0;
                Z[I]=Top+Drop*Integral(Arc)/(Run-Ramp)-Cut;
            }
        }
        for (int32 I=First; I<=Last; ++I) Solved[I]=Z[I-First];
        First=Last;
    }
    Heights=MoveTemp(Solved);
    return true;
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
