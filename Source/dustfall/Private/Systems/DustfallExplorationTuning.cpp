#include "Systems/DustfallExplorationTuning.h"

UDustfallExplorationTuning::UDustfallExplorationTuning()
{
    FDustfallSymptomDefinition Text;
    Text.Id = TEXT("CarrierOverlap"); Text.Text = TEXT("COMMS / faint carrier overlap");
    Symptoms.Add(Text);
    FDustfallSymptomDefinition Echo;
    Echo.Id = TEXT("UnresolvedEcho"); Echo.Kind = EDustfallSymptomKind::ScannerEcho;
    Echo.Text = TEXT("UNRESOLVED ECHO"); Symptoms.Add(Echo);
}
