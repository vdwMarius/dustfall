#include "UI/DustfallExplorationHUD.h"
#include "Systems/DustfallExplorationDirector.h"
#include "Engine/Canvas.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

void ADustfallExplorationHUD::DrawHUD()
{
    Super::DrawHUD();
    if (!Canvas || !PlayerOwner) return;
    if (!CachedDirector.IsValid())
        for (TActorIterator<ADustfallExplorationDirector> It(GetWorld()); It; ++It) { CachedDirector=*It; break; }
    ADustfallExplorationDirector* D=CachedDirector.Get();
    if (!D || !D->Tuning) return;
    const FLinearColor Amber(.95f,.72f,.38f,1), Cyan(.45f,.8f,.86f,1), Red(1,.28f,.12f,1);
    const float W=Canvas->SizeX, H=Canvas->SizeY;
    auto Text=[&](const FString& S,float X,float Y,float Scale=1.f,FLinearColor C=FLinearColor(.95f,.72f,.38f,1))
    { DrawText(S,C,X,Y,nullptr,Scale,false); };
    auto Panel=[&](float X,float Y,float Width,float Height) { DrawRect(FLinearColor(.012f,.018f,.022f,.86f),X,Y,Width,Height); };
    Panel(18,18,282,202);
    Text(TEXT("DUSTFALL / SUIT TELEMETRY"),30,28,.9f);
    const TCHAR* Names[]={TEXT("Oxygen"),TEXT("Power"),TEXT("Integrity"),TEXT("Stamina")};
    for(int32 I=0; I<4; ++I)
    {
        float Y=58+I*29;
        Text(FString(Names[I]).ToUpper(),30,Y,.8f);
        DrawRect(FLinearColor(.11f,.12f,.12f,1),122,Y+5,160,8);
        DrawRect(I==0 ? Cyan : Amber,122,Y+5,160*FMath::Clamp(float(D->SuitValue(Names[I]))/100.f,0.f,1.f),8);
        Text(FString::Printf(TEXT("%.0f"),D->SuitValue(Names[I])),253,Y-10,.6f);
    }
    Text(D->SuitValue(TEXT("InHabitat")) ? TEXT("HABITAT / PRESSURIZED") : TEXT("EXTERIOR / SUIT SEALED"),30,182,.8f);
    Text(FString::Printf(TEXT("CLONE %03d"),int32(D->SuitValue(TEXT("CloneGeneration")))),20,226,.8f);
    if (D->SuitValue(TEXT("Oxygen"))<=D->Tuning->HudLowOxygenThreshold) Text(TEXT("LOW OXYGEN - RETURN TO HABITAT"),20,254,1,Red);
    if (D->SuitValue(TEXT("Integrity"))<=D->Tuning->HudCriticalIntegrityThreshold) Text(TEXT("CRITICAL SUIT INTEGRITY"),20,278,1,Red);
    APawn* Pawn=UGameplayStatics::GetPlayerPawn(this,0);
    if (!Pawn) return;
    FVector HomeDelta=D->HomeLocation()-Pawn->GetActorLocation();
    float Relative=FMath::FindDeltaAngleDegrees(PlayerOwner->GetControlRotation().Yaw,HomeDelta.Rotation().Yaw);
    const FString Direction=FMath::Abs(Relative)<12 ? TEXT("AHEAD") : Relative<0 ? TEXT("LEFT") : TEXT("RIGHT");
    Text(FString::Printf(TEXT("HOME  %dm  /  %s %.0f deg"),int32(HomeDelta.Size2D()/100),*Direction,FMath::Abs(Relative)),FMath::Max(320.f,W*.5f-140),22,.9f,Cyan);
    auto Marker=[&](FVector Location,const FString& Name,FLinearColor Color,bool bAlways)
    {
        FVector2D Screen;
        const float Distance=FVector::Dist(Pawn->GetActorLocation(),Location)/100;
        if (PlayerOwner->ProjectWorldLocationToScreen(Location+FVector(0,0,80),Screen) && Screen.X>15 && Screen.X<W-120 && Screen.Y>50 && Screen.Y<H-120)
        {
            DrawRect(Color,Screen.X-4,Screen.Y-4,8,8);
            Text(FString::Printf(TEXT("%s  %.0fm"),*Name,Distance),Screen.X+10,Screen.Y-6,.8f,Color);
        }
        else if (bAlways) Text(Name+TEXT(" / offscreen"),W-195,55,.8f,Color);
    };
    Marker(D->HomeLocation(),TEXT("HOME"),Cyan,false);
    for(int32 I=0;I<D->Beacons.Num();++I) Marker(D->Beacons[I],FString::Printf(TEXT("BEACON %d"),I+1),Cyan,false);
    if(D->ScannerRemaining>0)
    {
        Text(FString::Printf(TEXT("SCANNER ACTIVE %.1fs"),D->ScannerRemaining),W*.5f-110,50,.8f,Cyan);
        for(const auto& Entry : D->GetNodes())
            if(auto* It=Entry.Get(); It && !It->bClaimed && FVector::Dist(Pawn->GetActorLocation(),It->GetActorLocation())<=D->Tuning->ScannerRange)
                Marker(It->GetActorLocation(),It->DisplayName,It->LoreText.IsEmpty()?Amber:Cyan,false);
    }
    if (const auto* Symptom=D->ActiveSymptom())
    {
        if (Symptom->Kind==EDustfallSymptomKind::ScannerEcho && D->ScannerRemaining>0)
            Marker(Pawn->GetActorLocation()+PlayerOwner->GetControlRotation().Vector()*D->Tuning->ScannerEchoOffset.X+FVector(0,D->Tuning->ScannerEchoOffset.Y,D->Tuning->ScannerEchoOffset.Z),Symptom->Text,FLinearColor(.55f,.65f,.62f,.55f),false);
        else if (Symptom->Kind==EDustfallSymptomKind::HudText)
            Text(Symptom->Text,W-285,H-125,.75f,FLinearColor(.6f,.65f,.58f,.6f));
    }
    if(auto* Node=D->NearestNode()) Text(TEXT("E  ")+Node->DisplayName,W*.5f-100,H*.68f,1,Amber);
    Text(D->StatusMessage,22,H-84,.8f);
    Text(TEXT("Q SCAN   E INTERACT   TAB INVENTORY   J JOURNAL   B BEACON   F5 SAVE / F9 LOAD   F8 SYMPTOMS"),22,H-56,.7f);
    Text(TEXT("F LIGHT   V VIEW   SHIFT SPRINT    /    Survival continues while reading"),22,H-34,.7f);
    if(D->bInventoryOpen)
    {
        const float X=FMath::Max(315.f,W*.55f), Y=100;
        Panel(X,Y,FMath::Min(410.f,W-X-20),340);
        Text(FString::Printf(TEXT("CARRIED INVENTORY  %d / %d"),D->InventoryCount(),D->Tuning->InventoryCapacity),X+16,Y+14,.9f);
        TArray<FName> Keys;D->Inventory.GetKeys(Keys);Keys.Sort(FNameLexicalLess());
        int32 I=0; for(FName Key:Keys)
        {
            const float CellX=X+16+(I%2)*175, CellY=Y+54+(I/2)*56;
            DrawRect(FLinearColor(.10f,.13f,.14f,.95f),CellX,CellY,164,46);
            Text(Key.ToString(),CellX+8,CellY+5,.85f);
            Text(FString::FromInt(D->Inventory[Key]),CellX+8,CellY+24,.8f,Cyan);++I;
        }
        if(Keys.IsEmpty()) Text(TEXT("No carried salvage. Q finds nearby supplies."),X+16,Y+64,.8f);
        if(D->HasRecoveredPayload()) Text(TEXT("Pending items remain in recovery crate."),X+16,Y+304,.75f,Cyan);
    }
    if(D->bJournalOpen)
    {
        float X=FMath::Max(315.f,W*.37f), Y=H*.38f;
        Panel(X,Y,FMath::Min(670.f,W-X-20),FMath::Min(340.f,H-Y-100));
        Text(TEXT("ARCHIVED RECORDS / J CLOSES"),X+16,Y+14,.9f,Cyan);
        TArray<FName> Keys;D->Journal.GetKeys(Keys);Keys.Sort(FNameLexicalLess());
        float LineY=Y+46;
        if(Keys.IsEmpty()) Text(TEXT("No records. Search the wreck and abandoned stations."),X+16,LineY,.8f);
        for(FName Key:Keys)
        {
            TArray<FString> Lines;D->Journal[Key].ParseIntoArrayLines(Lines);
            for(const FString& Line:Lines) { Text(Line,X+16,LineY,.78f);LineY+=19; }
            LineY+=12;
            if(LineY>H-150) break;
        }
    }
}
