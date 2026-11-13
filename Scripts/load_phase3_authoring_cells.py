"""Load/pin saved authoring actors for a full-world build/audit in this editor.

This changes editor loading only, not World Partition runtime streaming flags.
Do not run during PIE. Pins are released with the editor world/session.
"""
import unreal

if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('End PIE before loading authoring cells')
descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
if descs is None:
    raise RuntimeError('Foundation World Partition descriptors unavailable')
guids = [d.guid for d in descs if not d.native_class or 'HLOD' not in d.native_class.get_name()]
unreal.WorldPartitionBlueprintLibrary.load_actors(guids)
unreal.WorldPartitionBlueprintLibrary.pin_actors(guids)
unreal.log('DUSTFALL loaded/pinned %d authoring actors; runtime streaming unchanged' % len(guids))
