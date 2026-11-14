#include "DustfallTerrainLibrary.h"
#if WITH_EDITOR
#include "Landscape.h"
#include "LandscapeInfo.h"
#include "LandscapeEdit.h"
#include "LandscapeEditLayer.h"
#include "LandscapeComponent.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Engine/World.h"
#endif

FString UDustfallTerrainLibrary::AuthorHostileRelief(AActor* LandscapeActor, const FString& BaselineFile,
    const TArray<FVector>& ProtectionDiscs, const TArray<FVector>& RouteEndpoints)
{
#if WITH_EDITOR
    ALandscape* Landscape = Cast<ALandscape>(LandscapeActor);
    if (!Landscape || !Landscape->GetWorld() || Landscape->GetWorld()->IsGameWorld())
        return TEXT("ERROR: requires Landscape actor in editor world, PIE stopped");
    ULandscapeInfo* Info = Landscape->GetLandscapeInfo();
    int32 X1,Y1,X2,Y2;
    if (!Info || !Info->GetLandscapeExtent(X1,Y1,X2,Y2)) return TEXT("ERROR: no loaded landscape extent");
    const int32 Width=X2-X1+1, Height=Y2-Y1+1;
    if (Width<100 || Height<100 || int64(Width)*Height>20000000) return TEXT("ERROR: invalid extent");
    const FLandscapeLayer* Layer = Landscape->GetLayerConst(0);
    if (!Layer || !Layer->EditLayer) return TEXT("ERROR: landscape base edit layer missing");
    FLandscapeEditDataInterface Edit(Info, Layer->EditLayer->GetGuid());
    TArray<uint16> Baseline;
    Baseline.SetNumUninitialized(Width*Height);
    TArray<uint8> Bytes;
    // Header binds backup to exact section extent, avoiding accidental cross-map use.
    const int32 Header[4]={X1,Y1,X2,Y2};
    if (FPaths::FileExists(BaselineFile))
    {
        if (!FFileHelper::LoadFileToArray(Bytes,*BaselineFile) || Bytes.Num()!=16+Baseline.Num()*2 ||
            FMemory::Memcmp(Bytes.GetData(),Header,16)!=0) return TEXT("ERROR: baseline extent/size mismatch");
        FMemory::Memcpy(Baseline.GetData(),Bytes.GetData()+16,Baseline.Num()*2);
    }
    else
    {
        Edit.GetHeightDataFast(X1,Y1,X2,Y2,Baseline.GetData(),0);
        Bytes.SetNumUninitialized(16+Baseline.Num()*2);
        FMemory::Memcpy(Bytes.GetData(),Header,16);
        FMemory::Memcpy(Bytes.GetData()+16,Baseline.GetData(),Baseline.Num()*2);
        IFileManager::Get().MakeDirectory(*FPaths::GetPath(BaselineFile),true);
        if (!FFileHelper::SaveArrayToFile(Bytes,*BaselineFile)) return TEXT("ERROR: cannot save original baseline");
    }
    auto Smooth=[](double A,double B,double V) { double T=FMath::Clamp((V-A)/(B-A),0.,1.); return T*T*(3.-2.*T); };
    auto Gaussian=[](double X,double Y,double CX,double CY,double RX,double RY,double Yaw) {
        double C=FMath::Cos(Yaw),S=FMath::Sin(Yaw), DX=X-CX,DY=Y-CY;
        double U=(DX*C+DY*S)/RX,V=(-DX*S+DY*C)/RY;
        return FMath::Exp(-2.*(U*U+V*V));
    };
    const FTransform ToWorld=Landscape->LandscapeActorToWorld();
    const double ScaleZ=ToWorld.GetScale3D().Z;
    if (ScaleZ<=0.) return TEXT("ERROR: invalid landscape scale");
    TArray<uint16> Output; Output.SetNumUninitialized(Baseline.Num());
    double MinDelta=0.,MaxDelta=0.; int32 Changed=0;
    for(int32 Y=Y1;Y<=Y2;++Y) for(int32 X=X1;X<=X2;++X)
    {
        const int32 I=(Y-Y1)*Width+X-X1;
        const FVector P=ToWorld.TransformPosition(FVector(X,Y,0));
        const double PX=P.X,PY=P.Y;
        double Guard=1.;
        for(const FVector& D:ProtectionDiscs)
            Guard=FMath::Min(Guard,Smooth(D.Z,D.Z+2800.,FVector2D(PX-D.X,PY-D.Y).Size()));
        for(int32 R=0;R+1<RouteEndpoints.Num();R+=2)
        {
            FVector2D A(RouteEndpoints[R].X,RouteEndpoints[R].Y), B(RouteEndpoints[R+1].X,RouteEndpoints[R+1].Y), Q(PX,PY);
            const FVector2D AB=B-A;
            double T=FMath::Clamp(FVector2D::DotProduct(Q-A,AB)/FMath::Max(AB.SizeSquared(),1.),0.,1.);
            Guard=FMath::Min(Guard,Smooth(850.,3200.,(Q-A-AB*T).Size()));
        }
        // Mesoscale hills and asymmetric ridge masses: centimetres, fixed world seed.
        double Z=0.;
        const double Hills[][6]={
            {8000,-11000,11000,7000,1750,.35},{-18000,-13000,14000,6500,2500,-.6},
            {23000,23000,16000,9000,3100,.4},{-12000,17000,7500,12000,1900,-.8},
            {48000,-5000,17000,10000,3000,.7},{-34000,-29000,18000,8000,3700,-.3},
            {3000,43000,22000,9500,4300,.2},{65000,45000,23000,14000,5200,-.8},
            {-68000,-43000,20000,13000,4800,.4},{57000,-59000,22000,17000,4200,-.5},
            {-30000,61000,27000,12000,6100,.5},{-77000,65000,18000,19000,5400,.6}};
        for(const auto& H:Hills) Z+=H[4]*Gaussian(PX,PY,H[0],H[1],H[2],H[3],H[5]);
        // Windward mounds and sharp erosion teeth within the large hills.
        Z+=220.*FMath::Pow(FMath::Max(0.,FMath::Sin(PX*.00029+FMath::Sin(PY*.00015))),3.)*
            (.35+.65*FMath::Abs(FMath::Sin(PY*.00011)));
        Z+=460.*Gaussian(PX,PY,16000,-12000,16000,7000,.2)*FMath::Abs(FMath::Sin(PX*.0011+PY*.00065));
        // Dry ravine has steep north wall and a broad walkable south-bank escape.
        const double RavineY=-18500.+1400.*FMath::Sin((PX-7000.)*.00018);
        double Along=FMath::Exp(-FMath::Pow((PX-18000.)/15000.,4.));
        double Cross=(PY-RavineY)/(PY>RavineY?1050.:2900.);
        Z-=1250.*Along*FMath::Exp(-Cross*Cross*1.7);
        // Crater and readable terraced sinkhole away from protected paths.
        double CR=FVector2D(PX-28000.,PY-2000.).Size();
        Z+=350.*FMath::Exp(-FMath::Square((CR-4200.)/1000.));
        Z-=800.*FMath::Exp(-FMath::Square(CR/3200.));
        double PitR=FVector2D(PX+8500.,PY+6500.).Size();
        Z-=980.*(1.-Smooth(1000.,3000.,PitR));
        // An escape ramp carved into the east rim, never a vertical inescapable hole.
        double Ramp=Gaussian(PX,PY,-6300.,-6500.,2500.,850.,0.);
        Z+=550.*Ramp;
        Z*=Guard;
        MinDelta=FMath::Min(MinDelta,Z); MaxDelta=FMath::Max(MaxDelta,Z);
        Output[I]=uint16(FMath::Clamp(FMath::RoundToInt(double(Baseline[I])+Z*128./ScaleZ),0,65535));
        if(Output[I]!=Baseline[I]) ++Changed;
    }
    Landscape->Modify();
    TSet<ULandscapeComponent*> Components;
    Edit.GetComponentsInRegion(X1,Y1,X2,Y2,&Components);
    for(ULandscapeComponent* C:Components) { C->Modify(); C->RequestHeightmapUpdate(); }
    Edit.SetHeightData(X1,Y1,X2,Y2,Output.GetData(),0,true);
    Edit.Flush();
    Landscape->RequestLayersContentUpdateForceAll(ELandscapeLayerUpdateMode::Update_All,true);
    Landscape->ForceLayersFullUpdate();
    return FString::Printf(TEXT("OK extent=%d,%d,%d,%d vertices=%d changed=%d relief_cm=%.2f..%.2f components=%d"),
        X1,Y1,X2,Y2,Output.Num(),Changed,MinDelta,MaxDelta,Components.Num());
#else
    return TEXT("ERROR: terrain authoring is editor-only");
#endif
}

#if WITH_EDITOR
FString DustfallAuthorTerrainV2(AActor*, const FString&, const FString&, const FString&, bool);
#endif

FString UDustfallTerrainLibrary::AuthorTerrainFromFeatures(AActor* Actor, const FString& Baseline,
    const FString& Features, const FString& Report)
{
#if WITH_EDITOR
    return DustfallAuthorTerrainV2(Actor, Baseline, Features, Report, false);
#else
    return TEXT("ERROR: terrain authoring is editor-only");
#endif
}

FString UDustfallTerrainLibrary::ValidateTerrainFeatures(AActor* Actor, const FString& Baseline,
    const FString& Features, const FString& Report)
{
#if WITH_EDITOR
    return DustfallAuthorTerrainV2(Actor, Baseline, Features, Report, true);
#else
    return TEXT("ERROR: terrain validation is editor-only");
#endif
}
