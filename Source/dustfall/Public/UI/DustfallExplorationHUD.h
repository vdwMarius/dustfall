#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "DustfallExplorationHUD.generated.h"

UCLASS()
class DUSTFALL_API ADustfallExplorationHUD : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
private:
    TWeakObjectPtr<class ADustfallExplorationDirector> CachedDirector;
};
