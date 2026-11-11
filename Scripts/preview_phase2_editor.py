"""Set a PIE-only QA preset without changing saved assets.

Run after starting PIE. runpy init_globals accepts WEATHER (0/1/2), TIME (0..1)
and SNAP (default False). SNAP skips blends for visual review, not blend tests.
"""
import unreal

world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if not world:
    raise RuntimeError('Start PIE before selecting a Phase 2 QA preset')
cls=unreal.load_class(None,'/Game/World/Blueprints/BP_DustfallEnvironmentDirector.BP_DustfallEnvironmentDirector_C')
directors=unreal.GameplayStatics.get_all_actors_of_class(world,cls)
if len(directors)!=1:
    raise RuntimeError('Expected exactly one environment director')
director=directors[0]
if 'WEATHER' in globals():
    weather=int(WEATHER)
    if weather not in (0,1,2): raise ValueError('WEATHER must be 0, 1 or 2')
    director.call_method('SetWeather',(weather,))
    if globals().get('SNAP',False):
        data=director.get_editor_property('EnvironmentData')
        director.set_editor_property('CurrentFogDensity',data.get_editor_property(['CalmFogDensity','HazeFogDensity','StormFogDensity'][weather]))
        director.set_editor_property('StormIntensity',1. if weather==2 else 0.)
if 'TIME' in globals():
    clock=float(TIME)
    if not 0<=clock<=1: raise ValueError('TIME must be between 0 and 1')
    director.call_method('SetTimeOfDay',(clock,))
unreal.log('Phase 2 PIE-only preset applied; saved tuning assets were not edited.')
