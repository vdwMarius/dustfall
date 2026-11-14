#if WITH_EDITOR
#include "World/DustfallTerrainMath.h"
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "LandscapeEdit.h"
#include "LandscapeEditLayer.h"
#include "LandscapeComponent.h"
#include "Engine/World.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

namespace DustfallTerrainV2
{
using Math = FDustfallTerrainMath;
using Object = TSharedPtr<FJsonObject>;
using Value = TSharedPtr<FJsonValue>;
double N(const Object& O, const TCHAR* Key) { return O->GetNumberField(Key); }
FString S(const Object& O, const TCHAR* Key) { return O->GetStringField(Key); }
TArray<double> Numbers(const Object& O, const TCHAR* Key)
{
    TArray<double> Result;
    for (const Value& V : O->GetArrayField(Key)) Result.Add(V->AsNumber());
    return Result;
}
TArray<FVector2D> Points(const Object& O, const TCHAR* Key)
{
    TArray<FVector2D> Result;
    for (const Value& V : O->GetArrayField(Key))
    {
        const auto& A=V->AsArray(); Result.Emplace(A[0]->AsNumber(),A[1]->AsNumber());
    }
    return Result;
}
Value Number(double X) { return MakeShared<FJsonValueNumber>(X); }
Value Array(const TArray<Value>& X) { return MakeShared<FJsonValueArray>(X); }
Value Obj(const Object& X) { return MakeShared<FJsonValueObject>(X); }
bool Save(const Object& O, const FString& Path)
{
    FString Text;
    if (!FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<>::Create(&Text))) return false;
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);
    return FFileHelper::SaveStringToFile(Text,*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}
double Length(const TArray<FVector2D>& Line)
{
    double Total=0;
    for (int32 I=1; I<Line.Num(); ++I) Total+=(Line[I]-Line[I-1]).Size();
    return Total;
}
double Gaussian(const FVector2D& P, const TArray<double>& A)
{
    const double C=FMath::Cos(A[5]), Sine=FMath::Sin(A[5]);
    const FVector2D D=P-FVector2D(A[0],A[1]);
    return FMath::Exp(-2.*(FMath::Square((D.X*C+D.Y*Sine)/A[2])+FMath::Square((-D.X*Sine+D.Y*C)/A[3])));
}
struct FFeature
{
    Object Data;
    FString Id, Type, Stage;
    TArray<double> Params, Rim, Floor, Target;
    TArray<FVector2D> Line, Samples, North, South, Wall;
    double Total=0, OriginalRun=0, AnchorDrop=0, RequiredGrade=0, BaselineGrade=0;
    bool bGenerated=false, bGeometryValid=true, bInside=true;
    Object Generation;
    TArray<bool> Pinned;
    TArray<Value> GuardCrossings, Overlaps;
    FVector2D BoundsMin, BoundsMax;
};
struct FGrid
{
    int32 X1=0,Y1=0,X2=0,Y2=0,W=0,H=0;
    FTransform Transform;
    TArray<double> Z, Base;
    FVector2D World(int32 X, int32 Y) const
    {
        const FVector P=Transform.TransformPosition(FVector(X,Y,0)); return FVector2D(P.X,P.Y);
    }
    double Sample(const FVector2D& P, bool bBaseline=false) const
    {
        const TArray<double>& Heights=bBaseline?Base:Z;
        const FVector Q=Transform.InverseTransformPosition(FVector(P.X,P.Y,Transform.GetLocation().Z));
        const double X=FMath::Clamp(Q.X-X1,0.,double(W-1)), Y=FMath::Clamp(Q.Y-Y1,0.,double(H-1));
        const int32 IX=FMath::Min(FMath::FloorToInt(X),W-2), IY=FMath::Min(FMath::FloorToInt(Y),H-2);
        return FMath::Lerp(FMath::Lerp(Heights[IY*W+IX],Heights[IY*W+IX+1],X-IX),
            FMath::Lerp(Heights[(IY+1)*W+IX],Heights[(IY+1)*W+IX+1],X-IX),Y-IY);
    }
    bool Contains(const FVector2D& P) const
    {
        const FVector Q=Transform.InverseTransformPosition(FVector(P.X,P.Y,Transform.GetLocation().Z));
        return Q.X>=X1 && Q.X<=X2 && Q.Y>=Y1 && Q.Y<=Y2;
    }
};
double Relief(const FFeature& F, const FVector2D& P)
{
    const auto& A=F.Params;
    if (F.Type==TEXT("gaussian_hill") || F.Type==TEXT("spire_base")) return A[4]*Gaussian(P,A);
    if (F.Type==TEXT("ridged_noise"))
    {
        if (A.Num()==7) return A[0]*FMath::Pow(FMath::Max(0.,FMath::Sin(P.X*A[1]+FMath::Sin(P.Y*A[2]))),A[3])*(A[4]+A[5]*FMath::Abs(FMath::Sin(P.Y*A[6])));
        const TArray<double> G={A[1],A[2],A[3],A[4],1,A[5]};
        return A[0]*Gaussian(P,G)*FMath::Abs(FMath::Sin(P.X*A[6]+P.Y*A[7]));
    }
    if (F.Type==TEXT("ravine"))
    {
        const double Y=A[0]+A[1]*FMath::Sin((P.X-A[2])*A[3]);
        return -A[9]*FMath::Exp(-FMath::Pow((P.X-A[4])/A[5],A[6]))*
            FMath::Exp(-FMath::Square((P.Y-Y)/(P.Y>Y?A[7]:A[8]))*A[10]);
    }
    if (F.Type==TEXT("crater"))
    {
        const double R=(P-FVector2D(A[0],A[1])).Size();
        return A[2]*FMath::Exp(-FMath::Square((R-A[3])/A[4]))-A[5]*FMath::Exp(-FMath::Square(R/A[6]));
    }
    if (F.Type==TEXT("pit"))
    {
        const TArray<double> Ramp={A[6],A[7],A[8],A[9],1,A[10]};
        return -A[2]*(1-Math::Smooth(A[3],A[4],(P-FVector2D(A[0],A[1])).Size()))+A[5]*Gaussian(P,Ramp);
    }
    const auto Q=Math::Project(P,F.Line);
    const double T=Q.Arc/F.Total;
    double EndWidth=N(F.Data,TEXT("end_blend_cm"));
    if (F.Type==TEXT("escarpment"))
        EndWidth=FMath::Lerp(EndWidth,N(F.Data,TEXT("plateau_blend_cm")),
            Math::Smooth(0,N(F.Data,TEXT("face_width_cm")),Q.SignedDistance*N(F.Data,TEXT("high_side"))));
    const double End=Math::Smooth(0,EndWidth,Q.Arc)*Math::Smooth(0,EndWidth,F.Total-Q.Arc);
    if (F.Type==TEXT("canyon"))
    {
        const double Rim=FMath::Lerp(F.Rim[0],F.Rim[1],T)*.5, Floor=FMath::Lerp(F.Floor[0],F.Floor[1],T)*.5;
        const double Cross=(Q.Distance-Floor)/(Rim-Floor);
        return -N(F.Data,TEXT("depth_cm"))*(1-Math::Wall(Cross,Q.SignedDistance>=0?F.North:F.South))*End;
    }
    if (F.Type==TEXT("escarpment"))
    {
        const double D=Q.SignedDistance*N(F.Data,TEXT("high_side"));
        const double Face=N(F.Data,TEXT("face_width_cm")), Talus=N(F.Data,TEXT("talus_width_cm"));
        // Broad high-side plateau, flat low side; rise is a step, never a narrow Gaussian spike.
        double Rise=Math::Wall((D+Talus)/(Talus+Face),F.Wall);
        if (D>Face) Rise=1; // Sustained plateau, including the far dense field.
        return (N(F.Data,TEXT("drop_cm"))*Rise+N(F.Data,TEXT("vertical_offset_cm")))*End;
    }
    return 0;
}
}

FString DustfallAuthorTerrainV2(AActor* Actor, const FString& BaselineFile, const FString& FeaturesFile, const FString& ReportFile, bool bValidateOnly)
{
    using namespace DustfallTerrainV2;
    Object Report=MakeShared<FJsonObject>();
    TArray<Value> Problems;
    auto Problem=[&](const FString& Id, const FString& Message)
    {
        Object P=MakeShared<FJsonObject>(); P->SetStringField(TEXT("id"),Id);
        P->SetStringField(TEXT("message"),Message); Problems.Add(Obj(P));
    };
    Report->SetBoolField(TEXT("validate_only"),bValidateOnly);
    auto Fail=[&](const FString& Error) { Report->SetStringField(TEXT("status"),TEXT("failed")); Report->SetStringField(TEXT("error"),Error); Report->SetArrayField(TEXT("problems"),Problems); Save(Report,ReportFile);
        FString Full=TEXT("ERROR: ")+Error;
        for (const Value& P:Problems) Full+=TEXT("\n")+S(P->AsObject(),TEXT("id"))+TEXT(": ")+S(P->AsObject(),TEXT("message"));
        return Full; };
    ALandscape* Landscape=Cast<ALandscape>(Actor);
    if (!Landscape || !Landscape->GetWorld() || Landscape->GetWorld()->IsGameWorld()) return Fail(TEXT("Requires editor Landscape, PIE stopped"));
    FGrid G; ULandscapeInfo* Info=Landscape->GetLandscapeInfo();
    // Baseline extent is authoritative even before World Partition cells are loaded.
    // No edit interface is constructed on the validation path.
    TArray<uint8> Bytes;
    if (!FFileHelper::LoadFileToArray(Bytes,*BaselineFile) || Bytes.Num()<16) return Fail(TEXT("Exact baseline missing"));
    int32 Header[4]; FMemory::Memcpy(Header,Bytes.GetData(),16);
    G.X1=Header[0]; G.Y1=Header[1]; G.X2=Header[2]; G.Y2=Header[3];
    if (!Info) return Fail(TEXT("Landscape info missing"));
    const FLandscapeLayer* Layer=Landscape->GetLayerConst(0);
    if (!Layer || !Layer->EditLayer) Problem(TEXT("landscape"),TEXT("Landscape base edit layer missing"));
    G.W=G.X2-G.X1+1; G.H=G.Y2-G.Y1+1; G.Transform=Landscape->LandscapeActorToWorld();
    if (G.W<2 || G.H<2 || int64(G.W)*G.H>20000000 || !G.Transform.GetRotation().Equals(FQuat::Identity)) return Fail(TEXT("Invalid extent or rotated landscape"));
    const FVector Scale=G.Transform.GetScale3D();
    if (Scale.X<=0 || Scale.Y<=0 || Scale.Z<=0) return Fail(TEXT("Landscape scales must be positive"));
    FString Text; Object Root;
    if (!FFileHelper::LoadFileToString(Text,*FeaturesFile) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root) || !Root) return Fail(TEXT("Cannot read features JSON"));
    if (!Root->HasTypedField<EJson::Number>(TEXT("schema_version")) || N(Root,TEXT("schema_version"))!=2 || S(Root,TEXT("units"))!=TEXT("cm")) return Fail(TEXT("Expected v2 schema in centimetres"));
    if (!Root->HasTypedField<EJson::Array>(TEXT("features")) || !Root->HasTypedField<EJson::Object>(TEXT("resolved"))) return Fail(TEXT("Run build_phase5_terrain.py to validate and resolve schema/routes first"));
    const Object Resolved=Root->GetObjectField(TEXT("resolved"));
    if (!Resolved->GetBoolField(TEXT("validated"))) return Fail(TEXT("Features not validated"));
    const Object Protection=Root->GetObjectField(TEXT("protection")), Sampling=Root->GetObjectField(TEXT("sampling"));
    TArray<FVector> Discs;
    for (const Value& V : Resolved->GetArrayField(TEXT("discs_cm")))
    {
        const auto& A=V->AsArray(); Discs.Emplace(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());
    }
    TArray<TArray<FVector2D>> Routes;
    for (const Value& V : Resolved->GetArrayField(TEXT("routes"))) Routes.Add(Points(V->AsObject(),TEXT("line_cm")));
    auto Guard=[&](const FVector2D& P)
    {
        double V=1;
        for (const FVector& D:Discs) V=FMath::Min(V,Math::Smooth(D.Z,D.Z+N(Protection,TEXT("disc_blend_cm")),(P-FVector2D(D.X,D.Y)).Size()));
        for (const auto& Line:Routes) V=FMath::Min(V,Math::Smooth(N(Protection,TEXT("route_inner_cm")),N(Protection,TEXT("route_outer_cm")),Math::Project(P,Line).Distance));
        return V;
    };
    TArray<FFeature> Features;
    for (const Value& V:Root->GetArrayField(TEXT("features")))
    {
        FFeature F; F.Data=V->AsObject(); F.Id=S(F.Data,TEXT("id")); F.Type=S(F.Data,TEXT("type")); F.Stage=S(F.Data,TEXT("stage"));
        if (F.Data->HasField(TEXT("parameters"))) F.Params=Numbers(F.Data,TEXT("parameters"));
        if (F.Data->HasField(TEXT("line_cm"))) { F.Line=Points(F.Data,TEXT("line_cm")); F.Total=Length(F.Line); }
        if (F.Type==TEXT("canyon")) { F.Rim=Numbers(F.Data,TEXT("rim_width_cm")); F.Floor=Numbers(F.Data,TEXT("floor_width_cm")); F.North=Points(F.Data,TEXT("north_wall")); F.South=Points(F.Data,TEXT("south_wall")); }
        if (F.Type==TEXT("escarpment")) F.Wall=Points(F.Data,TEXT("wall"));
        Features.Add(MoveTemp(F));
    }
    Features.Sort([](const FFeature& A,const FFeature& B){return A.Id<B.Id;});
    if (Bytes.Num()!=16+G.W*G.H*2) return Fail(TEXT("Baseline size does not match its extent"));
    TArray<uint16> Baseline, Output;
    Baseline.SetNumUninitialized(G.W*G.H); FMemory::Memcpy(Baseline.GetData(),Bytes.GetData()+16,Baseline.Num()*2);
    G.Base.SetNumUninitialized(Baseline.Num()); G.Z.SetNumUninitialized(Baseline.Num());
    for (int32 Y=G.Y1; Y<=G.Y2; ++Y) for (int32 X=G.X1; X<=G.X2; ++X)
    {
        const int32 I=(Y-G.Y1)*G.W+X-G.X1; const FVector2D P=G.World(X,Y);
        G.Base[I]=(double(Baseline[I])-32768.)*Scale.Z/128.+G.Transform.GetLocation().Z;
        double Delta=0;
        for (const FFeature& F:Features) if (F.Stage!=TEXT("path")) Delta+=Relief(F,P);
        G.Z[I]=G.Base[I]+Delta*Guard(P);
    }
    // Canonical order also makes floating point accumulation reproducible after
    // reordering the input JSON. No path may read another path's raster output.
    // Every feature is evaluated, even if another feature fails. No landscape edit
    // interface or Modify/dirty call exists until the complete report passes.
    const double Step=N(Sampling,TEXT("path_step_cm"));
    const double RasterMargin=FMath::Sqrt(Scale.X*Scale.X+Scale.Y*Scale.Y);
    for (FFeature& F:Features) if (F.Stage==TEXT("path"))
    {
        F.OriginalRun=F.Total;
        F.AnchorDrop=G.Sample(F.Line[0])-G.Sample(F.Line.Last());
        const bool bRoute=F.Data->HasField(TEXT("route_reference"));
        const double ReservedGrade=N(F.Data,TEXT("max_grade"))*N(Sampling,TEXT("grade_reserve"));
        const double JunctionSupport=N(F.Data,TEXT("width_cm"))*.5+N(F.Data,TEXT("shoulder_cm"))+2*RasterMargin;
        const double RequiredRun=FMath::Abs(F.AnchorDrop)/ReservedGrade*1.01+2*JunctionSupport+2*N(F.Data,TEXT("endpoint_blend_cm"));
        if (F.Type==TEXT("descent") && F.Total<RequiredRun)
        {
            FVector2D Tangent=F.Line.Last()-F.Line[0]; Tangent=FVector2D(-Tangent.Y,Tangent.X);
            for (const FFeature& Parent:Features) if (Parent.Id==S(F.Data,TEXT("parent")))
                Tangent=Math::Project((F.Line[0]+F.Line.Last())*.5,Parent.Line).Tangent;
            double TraverseDirection=1; F.Data->TryGetNumberField(TEXT("traverse_direction"),TraverseDirection);
            Tangent*=TraverseDirection;
            const auto Generated=Math::Switchback(F.Line[0],F.Line.Last(),Tangent,
                RequiredRun,N(F.Data,TEXT("corridor_width_cm")),
                N(F.Data,TEXT("minimum_turn_radius_cm")),
                N(F.Data,TEXT("width_cm"))+2*(N(F.Data,TEXT("shoulder_cm"))+RasterMargin),Step);
            if (Generated.Error.IsEmpty())
            {
                F.Line=Generated.Line; F.Total=Generated.Length; F.bGenerated=true;
                F.Generation=MakeShared<FJsonObject>();
                F.Generation->SetNumberField(TEXT("turns"),Generated.Turns);
                F.Generation->SetNumberField(TEXT("minimum_turn_radius_cm"),Generated.TurnRadius);
                F.Generation->SetNumberField(TEXT("hairpin_spacing_cm"),Generated.LaneSpacing);
            }
            else { Problem(F.Id,Generated.Error); F.bGeometryValid=false; }
        }
        if (F.Type==TEXT("descent"))
        {
            const double Radius=N(F.Data,TEXT("minimum_turn_radius_cm"));
            if (Radius<N(F.Data,TEXT("width_cm"))*.5+N(F.Data,TEXT("shoulder_cm"))+RasterMargin)
            { Problem(F.Id,TEXT("Turn radius cannot support full outer tread and shoulders")); F.bGeometryValid=false; }
        }
        F.BoundsMin=F.Line[0]; F.BoundsMax=F.Line[0];
        const double Padding=N(F.Data,TEXT("width_cm"))*.5+N(F.Data,TEXT("shoulder_cm"))+RasterMargin;
        for (const FVector2D& P:F.Line)
        {
            F.BoundsMin.X=FMath::Min(F.BoundsMin.X,P.X-Padding); F.BoundsMin.Y=FMath::Min(F.BoundsMin.Y,P.Y-Padding);
            F.BoundsMax.X=FMath::Max(F.BoundsMax.X,P.X+Padding); F.BoundsMax.Y=FMath::Max(F.BoundsMax.Y,P.Y+Padding);
        }
        F.RequiredGrade=FMath::Abs(F.AnchorDrop)/F.Total;
        const int32 Count=FMath::Max(1,FMath::CeilToInt(F.Total/Step));
        bool bInside=true;
        for (int32 J=0; J<=Count; ++J)
        {
            const double Arc=F.Total*J/Count; const FVector2D P=Math::AtArc(F.Line,Arc);
            const FVector2D T=Math::ProjectTread(P,F.Line).Tangent, Normal(-T.Y,T.X);
            const double Extent=N(F.Data,TEXT("width_cm"))*.5+N(F.Data,TEXT("shoulder_cm"))+RasterMargin;
            bInside &= G.Contains(P) && G.Contains(P+Normal*Extent) && G.Contains(P-Normal*Extent);
            F.Samples.Add(P); F.Pinned.Add(J==0 || J==Count || Guard(P)==0); F.Target.Add(G.Sample(P)-(bRoute?0:N(F.Data,TEXT("sink_cm"))*Guard(P)*Math::Smooth(0,N(F.Data,TEXT("endpoint_blend_cm")),FMath::Min(Arc,F.Total-Arc))));
            if (J) F.BaselineGrade=FMath::Max(F.BaselineGrade,FMath::Abs(G.Sample(P,true)-G.Sample(F.Samples[J-1],true))/(P-F.Samples[J-1]).Size());
        }
        F.bInside=bInside;
        if (!bInside) { Problem(F.Id,TEXT("Path tread/shoulders leave landscape")); F.bGeometryValid=false; }
        if (N(F.Data,TEXT("width_cm"))<N(F.Data,TEXT("minimum_tread_width_cm")) || N(F.Data,TEXT("minimum_tread_width_cm"))<68)
        { Problem(F.Id,TEXT("Tread too narrow for capsule radius 34cm")); F.bGeometryValid=false; }
        if (F.Type==TEXT("descent"))
        {
            const double Top=F.Target[0], Bottom=F.Target.Last();
            for (int32 J=0; J<F.Target.Num(); ++J) F.Target[J]=FMath::Lerp(Top,Bottom,double(J)/Count);
        }
        // Protection pins are constraints in the solve, never a late reset of a
        // previously solved profile. Include every core crossing in the report.
        const auto Crossings=Math::CoreIntervals(F.Line,Discs,Routes,N(Protection,TEXT("route_inner_cm")));
        for (const FVector2D& Range:Crossings)
        {
            const FVector2D Start=Math::AtArc(F.Line,Range.X),End=Math::AtArc(F.Line,Range.Y);
            Object Crossing=MakeShared<FJsonObject>();
            Crossing->SetArrayField(TEXT("arc_range_cm"),{Number(Range.X),Number(Range.Y)});
            Crossing->SetArrayField(TEXT("start_xy_cm"),{Number(Start.X),Number(Start.Y)});
            Crossing->SetArrayField(TEXT("end_xy_cm"),{Number(End.X),Number(End.Y)});
            F.GuardCrossings.Add(Obj(Crossing));
            for (int32 J=0; J<F.Samples.Num(); ++J)
            {
                const double Arc=F.Total*J/Count;
                if (Arc<Range.X-Step || Arc>Range.Y+Step) continue;
                F.Target[J]=G.Sample(F.Samples[J],true); F.Pinned[J]=true;
            }
        }
    }
    // Find shared treads before solving any profile. Pin a level common junction
    // wide enough to include raster support; shoulders then blend symmetrically.
    TArray<Value> AllOverlaps;
    for (int32 A=0; A<Features.Num(); ++A) for (int32 B=A+1; B<Features.Num(); ++B)
    {
        FFeature& Left=Features[A]; FFeature& Right=Features[B];
        if (Left.Stage!=TEXT("path") || Right.Stage!=TEXT("path")) continue;
        const double Radius=(N(Left.Data,TEXT("width_cm"))+N(Right.Data,TEXT("width_cm")))*.5+2*RasterMargin;
        const TArray<TArray<FVector2D>> RightCorridor={Right.Line};
        const TArray<FVector> NoDiscs;
        const double FootprintRadius=Radius+N(Left.Data,TEXT("shoulder_cm"))+N(Right.Data,TEXT("shoulder_cm"));
        for (const FVector2D& Range:Math::CoreIntervals(Left.Line,NoDiscs,RightCorridor,FootprintRadius))
        {
            Object Shoulder=MakeShared<FJsonObject>();
            Shoulder->SetArrayField(TEXT("features"),{MakeShared<FJsonValueString>(Left.Id),MakeShared<FJsonValueString>(Right.Id)});
            Shoulder->SetArrayField(TEXT("first_arc_range_cm"),{Number(Range.X),Number(Range.Y)});
            Shoulder->SetStringField(TEXT("resolution"),TEXT("full_tread_precedence_then_commutative_shoulder_blend"));
            AllOverlaps.Add(Obj(Shoulder)); Left.Overlaps.Add(Obj(Shoulder)); Right.Overlaps.Add(Obj(Shoulder));
        }
        for (const FVector2D& Range:Math::CoreIntervals(Left.Line,NoDiscs,RightCorridor,Radius))
        {
            double RightFirst=TNumericLimits<double>::Max(),RightLast=0,Closest=TNumericLimits<double>::Max();
            FVector2D Centre=FVector2D::ZeroVector;
            const int32 Count=FMath::Max(1,FMath::CeilToInt((Range.Y-Range.X)/Step));
            for (int32 J=0; J<=Count; ++J)
            {
                const FVector2D P=Math::AtArc(Left.Line,FMath::Lerp(Range.X,Range.Y,double(J)/Count));
                const auto Q=Math::Project(P,Right.Line);
                if (Q.Distance<Closest) { Closest=Q.Distance; Centre=(P+Q.Point)*.5; }
                RightFirst=FMath::Min(RightFirst,Q.Arc); RightLast=FMath::Max(RightLast,Q.Arc);
            }
            const double Height=G.Sample(Centre);
            Object Junction=MakeShared<FJsonObject>();
            Junction->SetArrayField(TEXT("features"),{MakeShared<FJsonValueString>(Left.Id),MakeShared<FJsonValueString>(Right.Id)});
            Junction->SetArrayField(TEXT("xy_cm"),{Number(Centre.X),Number(Centre.Y)});
            Junction->SetArrayField(TEXT("first_arc_range_cm"),{Number(Range.X),Number(Range.Y)});
            Junction->SetArrayField(TEXT("second_arc_range_cm"),{Number(RightFirst),Number(RightLast)});
            const bool bProtected=Left.Data->HasField(TEXT("route_reference")) || Right.Data->HasField(TEXT("route_reference"));
            Junction->SetStringField(TEXT("resolution"),bProtected?TEXT("protected_baseline_pins"):TEXT("common_level_profile_pins_and_simultaneous_weighted_blend"));
            AllOverlaps.Add(Obj(Junction)); Left.Overlaps.Add(Obj(Junction)); Right.Overlaps.Add(Obj(Junction));
            auto Pin=[&](FFeature& F,double From,double To)
            {
                const double Padding=N(F.Data,TEXT("width_cm"))*.5+N(F.Data,TEXT("shoulder_cm"))+2*RasterMargin;
                for (int32 J=0; J<F.Samples.Num(); ++J)
                {
                    const double Arc=F.Total*J/(F.Samples.Num()-1);
                    if (Arc<From-Padding || Arc>To+Padding || Guard(F.Samples[J])<1) continue;
                    if (F.Pinned[J] && FMath::Abs(F.Target[J]-Height)>N(Sampling,TEXT("profile_tolerance_cm")))
                    { Problem(F.Id,TEXT("Incompatible junction pin: ")+Left.Id+TEXT(" / ")+Right.Id); F.bGeometryValid=false; }
                    F.Target[J]=Height; F.Pinned[J]=true;
                }
            };
            if (!bProtected) { Pin(Left,Range.X,Range.Y); Pin(Right,RightFirst,RightLast); }
        }
    }
    Report->SetArrayField(TEXT("path_overlaps"),AllOverlaps);
    for (FFeature& F:Features) if (F.Stage==TEXT("path"))
    {
        const bool bRoute=F.Data->HasField(TEXT("route_reference"));
        const double ReservedGrade=N(F.Data,TEXT("max_grade"))*N(Sampling,TEXT("grade_reserve"));
        if (bRoute) continue; // Protected baseline profile has precedence over target grade.
        double Limit=ReservedGrade;
        if (F.Type!=TEXT("descent"))
        {
            double Ceiling=.20; F.Data->TryGetNumberField(TEXT("hard_max_grade"),Ceiling);
            Limit=FMath::Min(Ceiling*N(Sampling,TEXT("grade_reserve")),FMath::Max(Limit,F.RequiredGrade*1.001));
        }
        if (!Math::LimitPinnedGrade(F.Samples,F.Target,Limit,F.Pinned,N(F.Data,TEXT("endpoint_blend_cm")),N(F.Data,TEXT("sink_cm"))))
        { Problem(F.Id,TEXT("Endpoint grade exceeds available safe corridor / hard ceiling")); F.bGeometryValid=false; }
    }
    // Simultaneous rasterisation: every cut reads immutable relief and contributes
    // to a commutative weighted junction. Route features never write terrain.
    for (int32 Y=G.Y1; Y<=G.Y2; ++Y) for (int32 X=G.X1; X<=G.X2; ++X)
    {
        const FVector2D P=G.World(X,Y); const int32 I=(Y-G.Y1)*G.W+X-G.X1;
        double Sum=0,Weights=0,Coverage=0,TreadSum=0,TreadWeights=0,TreadCoverage=0;
        for (const FFeature& F:Features) if (F.Stage==TEXT("path") && !F.Data->HasField(TEXT("route_reference")))
        {
            if (P.X<F.BoundsMin.X || P.X>F.BoundsMax.X || P.Y<F.BoundsMin.Y || P.Y>F.BoundsMax.Y) continue;
            const auto Q=Math::ProjectTread(P,F.Line);
            const double Half=N(F.Data,TEXT("width_cm"))*.5, Shoulder=N(F.Data,TEXT("shoulder_cm"));
            // Endpoint normal coordinates extrapolate for raster support. A
            // hairpin AABB can contain long backward anchor rays; never carve them.
            if (Q.Distance>Half+Shoulder+RasterMargin ||
                !Math::IsTreadArcSupported(Q.Arc,F.Total,Half+Shoulder+RasterMargin)) continue;
            const double U=Q.Arc/F.Total*(F.Target.Num()-1);
            const int32 J=FMath::Clamp(FMath::FloorToInt(U),0,F.Target.Num()-2);
            const double Target=FMath::Lerp(F.Target[J],F.Target[J+1],U-J);
            const double Weight=(1-Math::Smooth(Half+RasterMargin,Half+RasterMargin+Shoulder,Q.Distance))*Guard(P);
            if (Q.Distance<=Half+RasterMargin)
            { TreadSum+=Weight*Target; TreadWeights+=Weight; TreadCoverage=FMath::Max(TreadCoverage,Weight); }
            else { Sum+=Weight*Target; Weights+=Weight; Coverage=FMath::Max(Coverage,Weight); }
        }
        // A neighbouring shoulder must never tilt a full tread. Multiple full
        // treads share the common junction pins prepared above.
        if (TreadWeights>0) G.Z[I]=FMath::Lerp(G.Z[I],TreadSum/TreadWeights,TreadCoverage);
        else if (Weights>0) G.Z[I]=FMath::Lerp(G.Z[I],Sum/Weights,Coverage);
    }
    Output.SetNumUninitialized(Baseline.Num());
    int32 Changed=0, Clipped=0; double MinDelta=0,MaxDelta=0;
    TArray<Value> ChangedTiles; TSet<FIntPoint> Tiles;
    const double TileSize=N(Resolved,TEXT("pcg_cell_size_cm")), TileOrigin=N(Resolved,TEXT("pcg_origin_cm"));
    for (int32 Y=G.Y1; Y<=G.Y2; ++Y) for (int32 X=G.X1; X<=G.X2; ++X)
    {
        const int32 I=(Y-G.Y1)*G.W+X-G.X1; const FVector2D P=G.World(X,Y);
        const double Encoded=(G.Z[I]-G.Transform.GetLocation().Z)*128./Scale.Z+32768.;
        if (!FMath::IsFinite(Encoded) || Encoded<0 || Encoded>65535) ++Clipped;
        Output[I]=uint16(FMath::RoundToInt(FMath::IsFinite(Encoded)?FMath::Clamp(Encoded,0.,65535.):32768.));
        G.Z[I]=(double(Output[I])-32768.)*Scale.Z/128.+G.Transform.GetLocation().Z;
        MinDelta=FMath::Min(MinDelta,G.Z[I]-G.Base[I]); MaxDelta=FMath::Max(MaxDelta,G.Z[I]-G.Base[I]);
        if (Output[I]!=Baseline[I]) ++Changed;
        if (Output[I]!=Baseline[I])
        {
            Tiles.Add(FIntPoint(FMath::FloorToInt((P.X-TileOrigin)/TileSize),FMath::FloorToInt((P.Y-TileOrigin)/TileSize)));
        }
    }
    Report->SetArrayField(TEXT("landscape_location_cm"),{Number(G.Transform.GetLocation().X),Number(G.Transform.GetLocation().Y),Number(G.Transform.GetLocation().Z)});
    Report->SetArrayField(TEXT("landscape_scale"),{Number(Scale.X),Number(Scale.Y),Number(Scale.Z)});
    Report->SetNumberField(TEXT("clipped_vertices"),Clipped);
    if (Clipped) Problem(TEXT("landscape"),TEXT("Feature exceeds uint16/ScaleZ height range"));
    Report->SetArrayField(TEXT("height_delta_range_cm"),{Number(MinDelta),Number(MaxDelta)});
    Report->SetNumberField(TEXT("changed_vertex_count"),Changed);
    Report->SetNumberField(TEXT("height_quantisation_cm"),Scale.Z/128.);
    TArray<FIntPoint> SortedTiles=Tiles.Array(); SortedTiles.Sort([](const FIntPoint& A,const FIntPoint& B){return A.X==B.X?A.Y<B.Y:A.X<B.X;});
    for (const FIntPoint& Tile:SortedTiles) ChangedTiles.Add(Array({Number(Tile.X),Number(Tile.Y)}));
    Report->SetArrayField(TEXT("changed_pcg_grid_cells"),ChangedTiles);
    Report->SetStringField(TEXT("pcg_cell_basis"),TEXT("difference_from_baseline; apply unions current differences"));
    // One output slope pass shared by feature measurements; avoid resampling the
    // same heightfield once per overlapping legacy mound.
    TArray<float> OutputSlope; OutputSlope.SetNumUninitialized(G.Z.Num());
    for (int32 Y=0; Y<G.H; ++Y) for (int32 X=0; X<G.W; ++X)
    {
        const int32 NX=FMath::Min(G.W-1,X+1), NY=FMath::Min(G.H-1,Y+1);
        const double Z00=G.Z[Y*G.W+X],Z10=G.Z[Y*G.W+NX],Z01=G.Z[NY*G.W+X],Z11=G.Z[NY*G.W+NX];
        const double A=FMath::Square((Z10-Z00)/Scale.X)+FMath::Square((Z01-Z00)/Scale.Y);
        const double B=FMath::Square((Z11-Z01)/Scale.X)+FMath::Square((Z11-Z10)/Scale.Y);
        OutputSlope[Y*G.W+X]=float(FMath::RadiansToDegrees(FMath::Atan(FMath::Sqrt(FMath::Max(A,B)))));
    }
    TArray<Value> Metrics, Paths;
    for (const FFeature& F:Features)
    {
        Object M=MakeShared<FJsonObject>(); M->SetStringField(TEXT("id"),F.Id); M->SetStringField(TEXT("type"),F.Type);
        if (F.Stage==TEXT("path")) M->SetBoolField(TEXT("footprint_leaves_landscape"),!F.bInside);
        else if (!F.Line.IsEmpty())
        {
            bool bCentreInside=true, bFootprintInside=true;
            const int32 Count=FMath::Max(1,FMath::CeilToInt(F.Total/Step));
            for (int32 J=0; J<=Count; ++J)
            {
                const double Arc=F.Total*J/Count; const FVector2D P=Math::AtArc(F.Line,Arc);
                const FVector2D T=Math::ProjectTread(P,F.Line).Tangent, Normal(-T.Y,T.X);
                bCentreInside &= G.Contains(P);
                if (F.Type==TEXT("canyon"))
                {
                    const double Half=FMath::Lerp(F.Rim[0],F.Rim[1],Arc/F.Total)*.5;
                    bFootprintInside &= G.Contains(P+Normal*Half) && G.Contains(P-Normal*Half);
                }
                else if (F.Type==TEXT("escarpment"))
                {
                    const FVector2D High=Normal*N(F.Data,TEXT("high_side"));
                    bFootprintInside &= G.Contains(P+High*N(F.Data,TEXT("face_width_cm"))) && G.Contains(P-High*N(F.Data,TEXT("talus_width_cm")));
                }
            }
            M->SetBoolField(TEXT("centreline_leaves_landscape"),!bCentreInside);
            M->SetBoolField(TEXT("footprint_leaves_landscape"),!bFootprintInside);
            if (!bCentreInside || !bFootprintInside) Problem(F.Id,TEXT("Cliff/canyon centreline or wall footprint leaves landscape"));
        }
        else if (!F.Params.IsEmpty() && (F.Type==TEXT("gaussian_hill") || F.Type==TEXT("spire_base") || F.Type==TEXT("pit") || F.Type==TEXT("crater")))
        {
            const bool bInside=G.Contains(FVector2D(F.Params[0],F.Params[1]));
            M->SetBoolField(TEXT("anchor_leaves_landscape"),!bInside);
            if (!bInside) Problem(F.Id,TEXT("Relief anchor leaves landscape"));
        }
        double Minimum=TNumericLimits<double>::Max(), Maximum=-TNumericLimits<double>::Max(), Slope=0;
        double DeltaMin=TNumericLimits<double>::Max(),DeltaMax=-TNumericLimits<double>::Max();
        if (F.Stage==TEXT("path"))
        {
            double Grade=0, CrossSlope=0, TargetError=0; TArray<Value> Polyline;
            Object WorstGrade, WorstCross, WorstError;
            auto Diagnostic=[&](const FVector2D& P,double Arc,double Measurement)
            {
                Object D=MakeShared<FJsonObject>(); D->SetArrayField(TEXT("xy_cm"),{Number(P.X),Number(P.Y)});
                D->SetNumberField(TEXT("arc_cm"),Arc); D->SetNumberField(TEXT("value"),Measurement);
                FString Cause=TEXT("unknown");
                if (Guard(P)<1) Cause=TEXT("guard_reset");
                else
                {
                    for (const FFeature& Other:Features) if (Other.Stage==TEXT("path") && Other.Id!=F.Id)
                    {
                        if (Other.Data->HasField(TEXT("route_reference")) ||
                            P.X<Other.BoundsMin.X || P.X>Other.BoundsMax.X ||
                            P.Y<Other.BoundsMin.Y || P.Y>Other.BoundsMax.Y) continue;
                        // Inspect the writer's normal coordinates: finite
                        // polyline projection cannot diagnose endpoint rays.
                        const auto Q=Math::ProjectTread(P,Other.Line);
                        const double Support=N(Other.Data,TEXT("width_cm"))*.5+N(Other.Data,TEXT("shoulder_cm"))+RasterMargin;
                        if (Q.Distance>Support) continue;
                        const bool bExtension=Q.Arc<0 || Q.Arc>Other.Total;
                        if (!Math::IsTreadArcSupported(Q.Arc,Other.Total,Support))
                        {
                            D->SetStringField(TEXT("excluded_endpoint_extension"),Other.Id);
                            D->SetNumberField(TEXT("excluded_endpoint_arc_cm"),Q.Arc);
                            continue;
                        }
                        Cause=(bExtension?TEXT("endpoint_extension:"):TEXT("overlap:"))+Other.Id;
                        break;
                    }
                    if (Cause==TEXT("unknown"))
                    {
                        const auto A=Math::ProjectTread(Math::AtArc(F.Line,FMath::Max(0.,Arc-RasterMargin)),F.Line);
                        const auto B=Math::ProjectTread(Math::AtArc(F.Line,FMath::Min(F.Total,Arc+RasterMargin)),F.Line);
                        Cause=FVector2D::DotProduct(A.Tangent,B.Tangent)<.99999?TEXT("bend"):TEXT("raster");
                    }
                }
                D->SetStringField(TEXT("cause"),Cause); return D;
            };
            for (int32 J=0; J<F.Samples.Num(); ++J)
            {
                const FVector2D P=F.Samples[J]; const double Z=G.Sample(P);
                Polyline.Add(Array({Number(P.X),Number(P.Y),Number(Z)}));
                const double Arc=F.Total*J/(F.Samples.Num()-1),Error=FMath::Abs(Z-F.Target[J]);
                if (!WorstError || Error>TargetError) { TargetError=Error; WorstError=Diagnostic(P,Arc,Error); }
                if (J)
                {
                    const double Measured=FMath::Abs(Z-G.Sample(F.Samples[J-1]))/(P-F.Samples[J-1]).Size();
                    if (!WorstGrade || Measured>Grade)
                    { Grade=Measured; WorstGrade=Diagnostic((P+F.Samples[J-1])*.5,Arc-F.Total/(F.Samples.Num()-1)*.5,Grade); }
                }
                const FVector2D T=Math::ProjectTread(P,F.Line).Tangent, Normal(-T.Y,T.X);
                const double Half=N(F.Data,TEXT("width_cm"))*.5;
                const int32 Across=FMath::CeilToInt(2*Half/Step);
                double PreviousZ=G.Sample(P-Normal*Half);
                for (int32 K=1; K<=Across; ++K)
                {
                    const double NextZ=G.Sample(P+Normal*(-Half+2*Half*K/Across));
                    const double Measured=FMath::Abs(NextZ-PreviousZ)/(2*Half/Across);
                    if (!WorstCross || Measured>CrossSlope)
                    { CrossSlope=Measured; WorstCross=Diagnostic(P+Normal*(-Half+2*Half*(K-.5)/Across),Arc,CrossSlope); }
                    PreviousZ=NextZ;
                }
            }
            M->SetObjectField(TEXT("worst_grade"),WorstGrade);
            M->SetObjectField(TEXT("worst_cross_slope"),WorstCross);
            M->SetObjectField(TEXT("worst_profile_error"),WorstError);
            M->SetArrayField(TEXT("guard_core_crossings"),F.GuardCrossings);
            M->SetArrayField(TEXT("overlaps"),F.Overlaps);
            M->SetNumberField(TEXT("maximum_profile_error_cm"),TargetError);
            M->SetNumberField(TEXT("endpoint_connection_error_cm"),FMath::Max(
                FMath::Abs(G.Sample(F.Samples[0])-F.Target[0]),FMath::Abs(G.Sample(F.Samples.Last())-F.Target.Last())));
            M->SetNumberField(TEXT("maximum_grade"),Grade); M->SetNumberField(TEXT("maximum_cross_slope"),CrossSlope);
            M->SetNumberField(TEXT("endpoint_drop_cm"),G.Sample(F.Samples[0])-G.Sample(F.Samples.Last()));
            const bool bRoute=F.Data->HasField(TEXT("route_reference"));
            double Ceiling=.20; F.Data->TryGetNumberField(TEXT("hard_max_grade"),Ceiling);
            if (F.Type==TEXT("descent")) Ceiling=N(F.Data,TEXT("max_grade"));
            const bool bValid=F.bGeometryValid && (bRoute || (TargetError<=Scale.Z/128.+N(Sampling,TEXT("profile_tolerance_cm")) && Grade<=Ceiling && CrossSlope<=N(F.Data,TEXT("max_cross_slope")) && (F.Type!=TEXT("descent") || G.Sample(F.Samples[0])>G.Sample(F.Samples.Last()))));
            M->SetNumberField(TEXT("original_horizontal_run_cm"),F.OriginalRun);
            M->SetNumberField(TEXT("available_horizontal_run_cm"),F.Total);
            M->SetNumberField(TEXT("anchor_height_difference_cm"),F.AnchorDrop);
            M->SetNumberField(TEXT("required_grade"),F.RequiredGrade);
            M->SetNumberField(TEXT("configured_grade_limit"),N(F.Data,TEXT("max_grade")));
            M->SetNumberField(TEXT("hard_grade_ceiling"),Ceiling);
            M->SetNumberField(TEXT("baseline_maximum_grade"),F.BaselineGrade);
            M->SetStringField(TEXT("grade_policy"),bRoute?TEXT("preserve_baseline"):F.Type==TEXT("descent")?TEXT("strict_generated_run"):TEXT("best_effort_hard_ceiling"));
            M->SetBoolField(TEXT("target_grade_met"),Grade<=N(F.Data,TEXT("max_grade")));
            M->SetBoolField(TEXT("generated"),F.bGenerated);
            if (F.Generation) M->SetObjectField(TEXT("generation"),F.Generation);
            M->SetBoolField(TEXT("valid"),bValid);
            if (!bValid) Problem(F.Id,TEXT("Output traversal failed; inspect measured grade, cross slope, profile error and geometry"));
            Object Path=MakeShared<FJsonObject>(); Path->SetStringField(TEXT("id"),F.Id); Path->SetStringField(TEXT("type"),F.Type);
            Path->SetNumberField(TEXT("width_cm"),N(F.Data,TEXT("width_cm"))); Path->SetArrayField(TEXT("polyline_cm"),Polyline); Path->SetBoolField(TEXT("generated"),F.bGenerated); M->SetArrayField(TEXT("polyline_cm"),Polyline); Paths.Add(Obj(Path));
        }
        else
        {
            // Scan each feature footprint, from OUTPUT (after protection/path carving).
            for (int32 Y=G.Y1; Y<=G.Y2; ++Y) for (int32 X=G.X1; X<=G.X2; ++X)
            {
                const FVector2D P=G.World(X,Y);
                if (FMath::Abs(Relief(F,P))<1) continue;
                const double Z=G.Z[(Y-G.Y1)*G.W+X-G.X1]; Minimum=FMath::Min(Minimum,Z); Maximum=FMath::Max(Maximum,Z);
                const double Delta=G.Z[(Y-G.Y1)*G.W+X-G.X1]-G.Base[(Y-G.Y1)*G.W+X-G.X1];
                DeltaMin=FMath::Min(DeltaMin,Delta); DeltaMax=FMath::Max(DeltaMax,Delta);
                Slope=FMath::Max(Slope,double(OutputSlope[(Y-G.Y1)*G.W+X-G.X1]));
            }
            if (F.Type==TEXT("canyon") || F.Type==TEXT("escarpment"))
            {
                double Measured=0;
                const int32 Sections=FMath::CeilToInt(F.Total/N(Sampling,TEXT("probe_step_cm")));
                for (int32 J=1; J<Sections; ++J)
                {
                    const double Arc=F.Total*J/Sections; const FVector2D P=Math::AtArc(F.Line,Arc);
                    const auto Q=Math::Project(P,F.Line); const FVector2D Normal(-Q.Tangent.Y,Q.Tangent.X);
                    double Drop=0;
                    if (F.Type==TEXT("canyon"))
                    {
                        const double Half=FMath::Lerp(F.Rim[0],F.Rim[1],Arc/F.Total)*.5;
                        Drop=FMath::Max(G.Sample(P+Normal*Half),G.Sample(P-Normal*Half))-G.Sample(P);
                    }
                    else
                    {
                        const FVector2D High=Normal*N(F.Data,TEXT("high_side"));
                        Drop=G.Sample(P+High*N(F.Data,TEXT("face_width_cm")))-G.Sample(P-High*N(F.Data,TEXT("talus_width_cm")));
                    }
                    Measured=FMath::Max(Measured,Drop);
                }
                M->SetNumberField(TEXT("measured_cross_section_depth_drop_cm"),Measured);
            }
            if (F.Type==TEXT("crater") || F.Type==TEXT("pit"))
            {
                const FVector2D Centre(F.Params[0],F.Params[1]);
                const double Radius=F.Type==TEXT("crater")?F.Params[3]:F.Params[4];
                double Rim=-TNumericLimits<double>::Max();
                for (int32 J=0; J<72; ++J)
                {
                    const double Angle=2*PI*J/72;
                    Rim=FMath::Max(Rim,G.Sample(Centre+FVector2D(FMath::Cos(Angle),FMath::Sin(Angle))*Radius));
                }
                M->SetNumberField(TEXT("measured_rim_to_floor_depth_cm"),Rim-G.Sample(Centre));
            }
            M->SetArrayField(TEXT("output_delta_range_cm"),{Number(DeltaMin),Number(DeltaMax)});
            M->SetNumberField(TEXT("output_min_z_cm"),Minimum); M->SetNumberField(TEXT("output_max_z_cm"),Maximum);
            M->SetNumberField(TEXT("output_depth_drop_range_cm"),Maximum-Minimum); M->SetNumberField(TEXT("maximum_wall_slope_degrees"),Slope);
        }
        Metrics.Add(Obj(M));
    }
    // Recheck original routes after every overlapping carve and final guard restoration.
    double RouteGrade=0;
    for (const auto& Line:Routes)
    {
        const double Total=Length(Line); const int32 Count=FMath::CeilToInt(Total/Step);
        FVector2D Previous=Line[0]; double Z=G.Sample(Previous);
        for (int32 J=1; J<=Count; ++J)
        {
            const FVector2D P=Math::AtArc(Line,Total*J/Count); const double Next=G.Sample(P);
            RouteGrade=FMath::Max(RouteGrade,FMath::Abs(Next-Z)/(P-Previous).Size()); Previous=P; Z=Next;
        }
    }
    Report->SetArrayField(TEXT("features"),Metrics); Report->SetNumberField(TEXT("protected_route_maximum_grade"),RouteGrade);
    Object PathReport=MakeShared<FJsonObject>(); PathReport->SetArrayField(TEXT("paths"),Paths);
    const FString MaskDirectory=FPaths::Combine(FPaths::ProjectSavedDir(),TEXT("Codex/TerrainMasks"));
    Report->SetArrayField(TEXT("paths"),Paths);
    Report->SetBoolField(TEXT("protected_route_target_met"),RouteGrade<.08);
    const FVector2D Min=G.World(G.X1,G.Y1),Max=G.World(G.X2,G.Y2);
    Report->SetArrayField(TEXT("mask_world_bounds_cm"),{Number(Min.X),Number(Min.Y),Number(Max.X),Number(Max.Y)});
    Report->SetBoolField(TEXT("pcg_rebuild_required"),true);
    const int32 MaskSize=int32(N(Sampling,TEXT("mask_size")));
    TArray<uint8> PathMask,CliffMask; PathMask.Init(0,MaskSize*MaskSize); CliffMask.Init(0,MaskSize*MaskSize);
    for (int32 Y=0; Y<MaskSize; ++Y) for (int32 X=0; X<MaskSize; ++X)
    {
        const FVector2D P(FMath::Lerp(Min.X,Max.X,double(X)/(MaskSize-1)),FMath::Lerp(Min.Y,Max.Y,double(Y)/(MaskSize-1)));
        double Weight=0;
        for (const FFeature& F:Features) if (F.Stage==TEXT("path") && P.X>=F.BoundsMin.X && P.X<=F.BoundsMax.X && P.Y>=F.BoundsMin.Y && P.Y<=F.BoundsMax.Y) Weight=FMath::Max(Weight,1-Math::Smooth(N(F.Data,TEXT("width_cm"))*.5,N(F.Data,TEXT("width_cm"))*.5+N(F.Data,TEXT("shoulder_cm")),Math::Project(P,F.Line).Distance));
        PathMask[Y*MaskSize+X]=uint8(FMath::RoundToInt(Weight*255));
        const int32 SX=FMath::RoundToInt(double(X)*(G.W-1)/(MaskSize-1)),SY=FMath::RoundToInt(double(Y)*(G.H-1)/(MaskSize-1));
        const double Degrees=OutputSlope[SY*G.W+SX];
        bool bTalus=false,bLedge=false;
        for (const FFeature& F:Features) if (F.Type==TEXT("canyon") || F.Type==TEXT("escarpment"))
        {
            const auto Q=Math::Project(P,F.Line);
            if (Q.Arc<=0 || Q.Arc>=F.Total) continue;
            double Cross=0; const TArray<FVector2D>* Knots=nullptr;
            if (F.Type==TEXT("canyon"))
            {
                const double Floor=FMath::Lerp(F.Floor[0],F.Floor[1],Q.Arc/F.Total)*.5;
                const double Rim=FMath::Lerp(F.Rim[0],F.Rim[1],Q.Arc/F.Total)*.5;
                Cross=(Q.Distance-Floor)/(Rim-Floor); Knots=Q.SignedDistance>=0?&F.North:&F.South;
            }
            else
            {
                Cross=(Q.SignedDistance*N(F.Data,TEXT("high_side"))+N(F.Data,TEXT("talus_width_cm")))/
                    (N(F.Data,TEXT("talus_width_cm"))+N(F.Data,TEXT("face_width_cm"))); Knots=&F.Wall;
            }
            if (Cross<=0 || Cross>=1) continue;
            for (int32 J=1; J<Knots->Num(); ++J) if (Cross>=(*Knots)[J-1].X && Cross<=(*Knots)[J].X)
            {
                bLedge|=(*Knots)[J-1].Y==(*Knots)[J].Y && (*Knots)[J].Y>0 && (*Knots)[J].Y<1;
                // Talus is the first rising section below the first strata bench.
                bTalus|=J==1;
                break;
            }
        }
        CliffMask[Y*MaskSize+X]=Degrees>N(Sampling,TEXT("cliff_degrees"))?255:(bTalus && Degrees>=N(Sampling,TEXT("talus_min_degrees")) && Degrees<=N(Sampling,TEXT("talus_max_degrees"))?85:(bLedge || Degrees>N(Sampling,TEXT("talus_max_degrees"))?170:0));
    }
    Report->SetNumberField(TEXT("mask_size"),MaskSize);
    Report->SetStringField(TEXT("mask_directory"),MaskDirectory);
    Report->SetArrayField(TEXT("problems"),Problems);
    if (!Problems.IsEmpty()) return Fail(TEXT("Terrain validation failed; all problems are in report; landscape untouched"));
    if (bValidateOnly)
    {
        Report->SetStringField(TEXT("status"),TEXT("validation_passed"));
        if (!Save(Report,ReportFile)) return TEXT("ERROR: Cannot write validation report");
        return TEXT("OK: terrain validation passed; landscape untouched");
    }
    // Commit prerequisites are checked before any side effects.
    int32 LoadedX1=0,LoadedY1=0,LoadedX2=0,LoadedY2=0;
    if (!Info->GetLandscapeExtent(LoadedX1,LoadedY1,LoadedX2,LoadedY2) || LoadedX1!=G.X1 || LoadedY1!=G.Y1 || LoadedX2!=G.X2 || LoadedY2!=G.Y2)
        return Fail(TEXT("Load full baseline landscape extent before authoring"));
    FLandscapeEditDataInterface Edit(Info,Layer->EditLayer->GetGuid());
    TSet<ULandscapeComponent*> Components;
    if (!Edit.GetComponentsInRegion(G.X1,G.Y1,G.X2,G.Y2,&Components)) return Fail(TEXT("Landscape component level is locked or hidden"));
    int64 LoadedQuads=0;
    for (const ULandscapeComponent* C:Components) LoadedQuads+=int64(C->ComponentSizeQuads)*C->ComponentSizeQuads;
    if (LoadedQuads!=int64(G.W-1)*(G.H-1)) return Fail(TEXT("Missing landscape components; load all authoring cells"));
    TArray<uint16> Current; Current.SetNumUninitialized(Output.Num());
    Edit.GetHeightDataFast(G.X1,G.Y1,G.X2,G.Y2,Current.GetData(),0);
    int32 ChangedCurrent=0;
    for (int32 Y=G.Y1; Y<=G.Y2; ++Y) for (int32 X=G.X1; X<=G.X2; ++X)
    {
        const int32 I=(Y-G.Y1)*G.W+X-G.X1;
        if (Output[I]==Current[I]) continue;
        ++ChangedCurrent; const FVector2D P=G.World(X,Y);
        Tiles.Add(FIntPoint(FMath::FloorToInt((P.X-TileOrigin)/TileSize),FMath::FloorToInt((P.Y-TileOrigin)/TileSize)));
    }
    SortedTiles=Tiles.Array(); SortedTiles.Sort([](const FIntPoint& A,const FIntPoint& B){return A.X==B.X?A.Y<B.Y:A.X<B.X;});
    ChangedTiles.Reset();
    for (const FIntPoint& Tile:SortedTiles) ChangedTiles.Add(Array({Number(Tile.X),Number(Tile.Y)}));
    Report->SetArrayField(TEXT("changed_pcg_grid_cells"),ChangedTiles);
    Report->SetNumberField(TEXT("changed_from_current_vertex_count"),ChangedCurrent);
    IFileManager::Get().MakeDirectory(*MaskDirectory,true);
    if (!Save(PathReport,FPaths::Combine(MaskDirectory,TEXT("polylines.json")))) return Fail(TEXT("Cannot write path polylines"));
    if (!FFileHelper::SaveArrayToFile(PathMask,*FPaths::Combine(MaskDirectory,TEXT("paths.raw"))) || !FFileHelper::SaveArrayToFile(CliffMask,*FPaths::Combine(MaskDirectory,TEXT("cliffs.raw")))) return Fail(TEXT("Cannot write masks"));
    Report->SetArrayField(TEXT("mask_world_bounds_cm"),{Number(Min.X),Number(Min.Y),Number(Max.X),Number(Max.Y)});
    Report->SetNumberField(TEXT("mask_size"),MaskSize); Report->SetStringField(TEXT("mask_directory"),MaskDirectory);
    Report->SetBoolField(TEXT("pcg_rebuild_required"),true); Report->SetStringField(TEXT("status"),TEXT("validated_pending_landscape_update"));
    if (!Save(Report,ReportFile)) return Fail(TEXT("Cannot write report"));
    Landscape->Modify();
    for (ULandscapeComponent* C:Components)
    {
        if (AActor* Owner=C->GetOwner()) Owner->Modify();
        C->Modify(); C->RequestHeightmapUpdate(); C->MarkPackageDirty();
    }
    Edit.SetHeightData(G.X1,G.Y1,G.X2,G.Y2,Output.GetData(),0,true); Edit.Flush();
    Landscape->RequestLayersContentUpdateForceAll(ELandscapeLayerUpdateMode::Update_All,true); Landscape->ForceLayersFullUpdate(); Landscape->MarkPackageDirty();
    return TEXT("OK: terrain v2 applied; collision verification and package save required");
}
#endif
