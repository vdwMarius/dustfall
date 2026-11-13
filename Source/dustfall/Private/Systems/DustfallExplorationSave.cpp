#include "Systems/DustfallExplorationSave.h"

bool UDustfallExplorationSave::ValidateAndMigrate(const UDustfallExplorationSave& Input, UDustfallExplorationSave& Output)
{
    if (Input.Version < 2 || Input.Version > 3) return false;
    auto ValidPayload=[](const TMap<FName,int32>& Payload)
    {
        for (const auto& Item : Payload) if (Item.Key.IsNone() || Item.Value<=0) return false;
        return true;
    };
    if (!ValidPayload(Input.Inventory) || !ValidPayload(Input.RecoveryInventory) ||
        !FMath::IsFinite(Input.Oxygen) || !FMath::IsFinite(Input.Power) || !FMath::IsFinite(Input.Integrity) || !FMath::IsFinite(Input.Stamina) ||
        !FMath::IsFinite(Input.PrivateStrain) ||
        Input.PlayerLocation.ContainsNaN() || Input.CrateLocation.ContainsNaN()) return false;
    for (FName Id : Input.ClaimedNodes) if (Id.IsNone()) return false;
    for (const auto& Entry : Input.Journal) if (Entry.Key.IsNone()) return false;
    for (const FVector& Position : Input.Beacons) if (Position.ContainsNaN()) return false;
    TArray<FDustfallBeaconRecord> Records;
    if (Input.Version==2)
    {
        for (const FVector& Position : Input.Beacons)
        {
            FDustfallBeaconRecord Record; Record.Id=FGuid::NewGuid(); Record.Location=Position; Records.Add(Record);
        }
    }
    else
    {
        TSet<FGuid> Ids;
        for (const auto& Record : Input.BeaconRecords)
        {
            if (!Record.Id.IsValid() || Ids.Contains(Record.Id) || Record.Location.ContainsNaN()) return false;
            Ids.Add(Record.Id);
        }
        Records=Input.BeaconRecords;
    }
    // All checks precede writes, including when Input and Output alias.
    Output.SavedAt=Input.SavedAt;
    Output.Inventory=Input.Inventory; Output.RecoveryInventory=Input.RecoveryInventory;
    Output.ClaimedNodes=Input.ClaimedNodes; Output.Journal=Input.Journal;
    Output.PrivateStrain=FMath::Clamp(Input.PrivateStrain,0.f,100.f);
    Output.SymptomIntensity=FMath::IsFinite(Input.SymptomIntensity) ? FMath::Clamp(Input.SymptomIntensity,0.f,1.f) : 0.f;
    Output.PlayerLocation=Input.PlayerLocation; Output.CrateLocation=Input.CrateLocation;
    Output.bCrateActive=Input.bCrateActive; Output.CloneGeneration=FMath::Max(Input.CloneGeneration,1);
    Output.Oxygen=FMath::Max(Input.Oxygen,0.0); Output.Power=FMath::Max(Input.Power,0.0);
    Output.Integrity=FMath::Max(Input.Integrity,0.0); Output.Stamina=FMath::Max(Input.Stamina,0.0);
    Output.BeaconRecords=MoveTemp(Records); Output.Beacons.Reset();
    for (const auto& Record : Output.BeaconRecords) Output.Beacons.Add(Record.Location);
    Output.Version=3;
    return true;
}
