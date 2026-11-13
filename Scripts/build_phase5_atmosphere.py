"""M6 authoring; Lead/editor-lock holder only, after closed-editor native build.

Run this, Dustfall.Core.AtmosphereBlends, brief smoke, then capture_phase5_atmosphere.py.
No Niagara: the prescribed ISM path is fully script authored; Niagara is deferred,
and no claim is made that UE5.8 Python can author a complete Niagara emitter.
Override: Saved/Codex/atmosphere_fx_override.json, object of tuning property names
(snake_case); vector/color values are arrays. Optional environment object accepts
StormFogDensity. The existing atmosphere_override.json is also honored for that
key, using build_phase3_environment.py's TUNING/override convention. Starting storm
density is 3.3 (about 10% reference-height contrast at 15m before the 8% cap).
Only that DA field changes; the Phase3 builder's graph/lighting passes do not run.
Material graph constants describe shape/algorithm; runtime tuning is in the DA.

Unreal Python API inventory: NONE verified live in this worktree (no editor lock).
Engine source and existing project usage were inspected; generated Python names,
material compilation, external-package saving and PIE callbacks require Lead QA.
Shared module APIs/types:
  Paths.project_dir; get_editor_subsystem; get_default_object; load_asset;
  load_class; Name; Vector; Vector2D; LinearColor; Rotator;
  UObject.modify/get_editor_property/set_editor_property/get_path_name/get_name/
  get_class/call_method; UClass.get_name.
Authoring APIs/types:
  UnrealEditorSubsystem.get_game_world/get_editor_world;
  EditorActorSubsystem.get_all_level_actors/spawn_actor_from_class;
  AssetToolsHelpers.get_asset_tools; AssetTools.create_asset;
  Material; MaterialFactoryNew; DataAssetFactory;
  EditorAssetLibrary.save_loaded_asset;
  EditorLoadingAndSavingUtils.get_dirty_map_packages/get_dirty_content_packages/
  save_dirty_packages/save_map;
  MaterialEditingLibrary.create_material_expression/delete_all_material_expressions/
  connect_material_expressions/connect_material_property/recompile_material;
  BlendMode.BLEND_TRANSLUCENT; MaterialShadingModel.MSM_UNLIT;
  NoiseFunction.NOISEFUNCTION_GRADIENT_TEX3D;
  MaterialProperty.MP_EMISSIVE_COLOR/MP_OPACITY;
  MaterialExpressionConstant/Constant2Vector/ScalarParameter/VectorParameter/
  TextureCoordinate/SphereMask/PerInstanceCustomData/VertexInterpolator/
  ComponentMask/Panner/AppendVector/Noise/CameraPositionWS/WorldPosition/
  Distance/Subtract/Divide/Max/Saturate/Add/Multiply/DepthFade;
  Actor.set_actor_label/set_folder_path;
  native DustfallAtmosphereFX and DustfallAtmosphereTuning reflected properties.
Capture APIs/types (capture_phase5_atmosphere.py):
  EditorActorSubsystem.destroy_actor;
  LevelEditorSubsystem.editor_request_begin_play/editor_request_end_play;
  EditorLevelLibrary.get_pie_worlds;
  GameplayStatics.delete_game_in_slot/get_actor_of_class/get_player_pawn/
  get_player_controller/get_all_actors_of_class;
  GameplayStatics CDO.call_method('BreakHitResult');
  SystemLibrary.line_trace_single/is_valid/execute_console_command;
  TraceTypeQuery.TRACE_TYPE_QUERY1; DrawDebugTrace.NONE;
  register_slate_post_tick_callback/unregister_slate_post_tick_callback;
  Actor.get_component_by_class/get_components_by_class/set_actor_scale3d/
  set_actor_location/set_actor_rotation/tags;
  StaticMeshComponent.set_static_mesh/set_collision_profile_name/set_material;
  CameraComponent.set_field_of_view;
  PlayerController.set_control_rotation/set_view_target_with_blend;
  CharacterMovementComponent.disable_movement; SpotLightComponent.set_visibility;
  LandscapeProxy; StaticMeshActor; StaticMeshComponent; CameraActor;
  CameraComponent; CharacterMovementComponent; SpotLightComponent.
Also validate Blueprint reflection names: SaveSlotName, EnvironmentData, TimeOfDay,
Weather, StormIntensity, WeatherElapsed, CurrentFogDensity, Oxygen/Power/Integrity;
and material/node/property names set below. HighResShot filename routing is unrun.
"""
import json
import math
import pathlib
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
OUT = ROOT/'Saved/Codex/phase5_atmosphere_build.json'
FOLDER = '/Game/World/Phase5/Atmosphere'
MAP = '/Game/World/Maps/L_Dustfall_Foundation'


def require(value, message):
    if not value:
        raise RuntimeError(message)
    return value


def material(name):
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    m = unreal.load_asset(FOLDER+'/'+name)
    if not m:
        m = require(tools.create_asset(name, FOLDER, unreal.Material, unreal.MaterialFactoryNew()), 'Material creation failed')
    m.modify()
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('used_with_instanced_static_meshes', True)
    g = unreal.MaterialEditingLibrary
    g.delete_all_material_expressions(m)
    count = [0]

    def node(kind, **props):
        count[0] += 1
        n = require(g.create_material_expression(m, getattr(unreal, 'MaterialExpression'+kind),
                    (count[0] % 7)*210-1500, (count[0] // 7)*220), 'Expression creation failed: '+kind)
        for key, value in props.items():
            n.set_editor_property(key, value)
        return n

    def link(a, b, pin, output=''):
        require(g.connect_material_expressions(a, output, b, pin), 'Material connection failed: '+pin)

    def scalar(name, value):
        return node('ScalarParameter', parameter_name=name, default_value=value)

    def binary(kind, a, b):
        n = node(kind)
        link(a, n, 'A'); link(b, n, 'B')
        return n

    uv = node('TextureCoordinate')
    center = node('Constant2Vector', r=.5, g=.5)
    edge = node('SphereMask', attenuation_radius=.5, hardness_percent=15.)
    link(uv, edge, 'A'); link(center, edge, 'B')
    custom = node('PerInstanceCustomData', data_index=0, const_default_value=1.)
    variation = node('VertexInterpolator')
    link(custom, variation, 'VS')
    pan = node('VectorParameter', parameter_name='Pan', default_value=unreal.LinearColor(.06, .025, 0, 0))
    mask = node('ComponentMask', r=True, g=True, b=False, a=False)
    link(pan, mask, '')
    panner = node('Panner')
    link(binary('Add', uv, variation), panner, 'Coordinate'); link(mask, panner, 'Speed')
    position = node('AppendVector')
    link(panner, position, 'A'); link(node('Constant', r=0.), position, 'B')
    # Engine source documents Fast Gradient at ~16 instructions and 1 lookup/level.
    noise = node('Noise', noise_function=unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX3D,
                 levels=1, quality=1, scale=4., output_min=0., output_max=1.)
    link(position, noise, 'Position')
    camera = node('CameraPositionWS')
    world = node('WorldPosition')
    distance = binary('Distance', camera, world)
    start = scalar('NearStart', 80.)
    near = node('Saturate')
    link(binary('Divide', binary('Subtract', distance, start),
                binary('Max', binary('Subtract', scalar('NearEnd', 200.), start), node('Constant', r=1.))), near, '')
    opacity = binary('Multiply', binary('Multiply', edge, noise), binary('Multiply', variation, near))
    opacity = binary('Multiply', opacity, scalar('Opacity', .1))
    depth = node('DepthFade')
    link(opacity, depth, 'Opacity'); link(scalar('DepthFade', 120.), depth, 'FadeDistance')
    color = node('VectorParameter', parameter_name='DustColor', default_value=unreal.LinearColor(.25, .17, .10, 1))
    require(g.connect_material_property(color, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR), 'Emissive connection failed')
    require(g.connect_material_property(depth, '', unreal.MaterialProperty.MP_OPACITY), 'Opacity connection failed')
    g.recompile_material(m)
    require(unreal.EditorAssetLibrary.save_loaded_asset(m, False), 'Material save failed')
    return m


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {'status': 'running', 'niagara': 'deferred; prescribed ISM path', 'errors': []}
    try:
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        require(not editor.get_game_world(), 'Stop PIE first')
        require(MAP in editor.get_editor_world().get_path_name(), 'Open foundation map first')
        require(hasattr(unreal, 'DustfallAtmosphereFX'), 'Compile/restart native editor first')
        # Never save unrelated user work, including external actor/component packages.
        dirty = list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        require(not dirty, 'Resolve existing dirty packages before authoring; nothing saved: '+str(dirty))
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        current = list(subsystem.get_all_level_actors())
        existing = [a for a in current if isinstance(a, unreal.DustfallAtmosphereFX)]
        require(len(existing) <= 1, 'Duplicate AtmosphereFX actors: resolve explicitly before authoring')
        path = ROOT/'Saved/Codex/atmosphere_fx_override.json'
        override = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        require(isinstance(override, dict), 'Override must be an object')
        fx_values = dict(override)
        environment_override = fx_values.pop('environment', {})
        require(isinstance(environment_override, dict) and not set(environment_override)-{'StormFogDensity'},
                'environment only accepts StormFogDensity')
        # Reuse the existing TUNING/JSON mechanism without executing its main(),
        # which would also reauthor unrelated fog/sky/exposure actors and save them.
        environment_tuning = runpy.run_path(str(ROOT/'Scripts/build_phase3_environment.py'))['TUNING']
        environment_tuning['StormFogDensity'] = 3.3
        legacy_path = ROOT/'Saved/Codex/atmosphere_override.json'
        legacy_override = json.loads(legacy_path.read_text(encoding='utf-8')) if legacy_path.exists() else {}
        require(isinstance(legacy_override, dict) and not set(legacy_override)-set(environment_tuning), 'Invalid existing atmosphere override')
        if 'StormFogDensity' in legacy_override:
            environment_tuning['StormFogDensity'] = legacy_override['StormFogDensity']
        environment_tuning.update(environment_override)
        density = environment_tuning['StormFogDensity']
        require(isinstance(density, (int, float)) and not isinstance(density, bool) and math.isfinite(density) and 0 <= density <= 10,
                'StormFogDensity must be finite in 0..10')
        # Validate against a fresh native CDO, so removing an override resets defaults.
        defaults = unreal.get_default_object(unreal.DustfallAtmosphereTuning)
        scalar_names = ['twilight_start', 'twilight_end', 'night_sky_minimum', 'night_exposure_bias', 'night_black_lift',
                        'post_process_priority', 'moon_lux', 'moon_elevation_scale', 'moon_yaw_offset',
                        'moon_disc_degrees', 'volume_forward', 'sheet_size', 'sheet_opacity_scale',
                        'sheet_drift_fraction', 'bounds_fade_fraction', 'density_feather',
                        'mote_fraction', 'mote_diameter',
                        'interior_fade_speed', 'near_fade_start', 'near_fade_end', 'depth_fade_distance']
        vectors = ['fog_max_opacity', 'fog_start_distance', 'volumetric_extinction', 'dust_density',
                   'dust_opacity', 'dust_speed', 'wind_direction', 'volume_half_extent', 'sheet_distances']
        pairs = ['mote_size', 'noise_pan']
        colors = ['night_fog_color', 'night_scene_tint', 'moon_color', 'moon_disc_scale', 'day_dust_color', 'night_dust_color']
        allowed = scalar_names + vectors + pairs + colors + ['seed', 'mote_count', 'moon_shadows']
        require(not set(fx_values)-set(allowed), 'Unknown override keys: '+str(set(fx_values)-set(allowed)))
        values = {name: defaults.get_editor_property(name) for name in allowed}
        for name, value in fx_values.items():
            if name in vectors + pairs + colors:
                expected = 4 if name in colors else 2 if name in pairs else 3
                require(isinstance(value, list) and len(value) == expected and all(isinstance(x, (int, float)) and math.isfinite(x) for x in value), 'Invalid vector/color: '+name)
                value = (unreal.LinearColor if name in colors else unreal.Vector2D if name in pairs else unreal.Vector)(*value)
            elif name == 'moon_shadows':
                require(isinstance(value, bool), 'moon_shadows must be boolean')
            else:
                require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value), 'Invalid number: '+name)
                if name in ['seed', 'mote_count']:
                    require(int(value) == value, 'Integer required: '+name)
                    value = int(value)
            values[name] = value
        require(0 <= values['mote_count'] <= 256, 'mote_count outside 0..256')
        require(values['near_fade_end'] > values['near_fade_start'] >= 0, 'Invalid near fade')
        require(values['twilight_end'] > values['twilight_start'], 'Invalid twilight interval')
        require(min(values['volume_half_extent'].x, values['volume_half_extent'].y, values['volume_half_extent'].z) > 0, 'Invalid dust volume')
        env_data = require(unreal.load_asset('/Game/Data/DA_Environment_Phase2'), 'Environment tuning missing')
        mote = material('M_DustfallMotes')
        sheet = material('M_DustfallSheets')
        tuning = unreal.load_asset('/Game/Data/DA_Atmosphere_Phase5')
        if not tuning:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property('data_asset_class', unreal.DustfallAtmosphereTuning)
            tuning = require(unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_Atmosphere_Phase5', '/Game/Data', unreal.DustfallAtmosphereTuning, factory), 'Tuning creation failed')
        tuning.modify()
        for name, value in values.items():
            tuning.set_editor_property(name, value)
        plane = require(unreal.load_asset('/Engine/BasicShapes/Plane'), 'Engine plane missing')
        for name, value in [('dust_plane', plane), ('mote_material', mote), ('sheet_material', sheet)]:
            tuning.set_editor_property(name, value)
        require(unreal.EditorAssetLibrary.save_loaded_asset(tuning, False), 'Tuning save failed')
        env_data.modify()
        env_data.set_editor_property('StormFogDensity', density)
        require(unreal.EditorAssetLibrary.save_loaded_asset(env_data, False), 'Environment tuning save failed')
        actor = existing[0] if existing else require(subsystem.spawn_actor_from_class(unreal.DustfallAtmosphereFX, unreal.Vector()), 'Actor spawn failed')
        actor.modify()
        actor.set_actor_label('Dustfall Atmosphere FX')
        actor.set_folder_path('DUSTFALL/Phase5')
        actor.set_editor_property('is_spatially_loaded', False)
        actor.set_editor_property('tuning', tuning)
        # Save dirty external actor AND component packages along with the map.
        # Entry required a clean workspace, so these all belong to this operation.
        require(unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True), 'Package save failed')
        require(unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(), MAP), 'Map save failed')
        report.update(status='authored; compile/PIE/visual/GPU acceptance required', actor=actor.get_path_name(),
                      tuning=tuning.get_path_name(), overrides=override, storm_density=density,
                      values={k: str(v) for k, v in values.items()}, silhouette_floor='1-FogMaxOpacity; default storm .08')
    except Exception as exc:
        report.update(status='failed', errors=[str(exc)])
        raise
    finally:
        OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
