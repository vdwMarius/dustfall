"""M6 authoring; Lead/editor-lock holder only, after closed-editor native build.

Run this, Dustfall.Core.AtmosphereBlends, brief smoke, then capture_phase5_atmosphere.py.
No Niagara: the prescribed ISM path is fully script authored; Niagara is deferred,
and no claim is made that UE5.8 Python can author a complete Niagara emitter.
Override: Saved/Codex/atmosphere_fx_override.json, object of tuning property names
(snake_case); vector/color values are arrays. Optional environment object accepts
StormFogDensity. The existing atmosphere_override.json is also honored for that
key, using build_phase3_environment.py's TUNING/override convention. Starting storm
density is 3.3, with matched-source 10m volumetrics and a .263 far transmission floor.
Only that DA field changes; the Phase3 builder's graph/lighting passes do not run.
Material graph constants describe shape/algorithm; runtime tuning is in the DA.

Unreal Python API inventory: no worker live validation (no editor lock).
The Noise World Position pin was already live-probed by the Lead; preserve it.
Engine source and existing project usage were inspected; generated Python names,
material compilation, external-package saving and PIE callbacks require Lead QA.
Shared module APIs/types:
  Paths.project_dir; get_editor_subsystem; get_default_object; load_asset;
  load_class; Name; Vector; Vector2D; LinearColor; Rotator;
  UObject.modify/get_editor_property/set_editor_property/get_path_name/get_name/
  get_class/call_method/get_package; UClass.get_name.
Authoring APIs/types:
  UnrealEditorSubsystem.get_game_world/get_editor_world;
  EditorActorSubsystem.get_all_level_actors/spawn_actor_from_class;
  AssetToolsHelpers.get_asset_tools; AssetTools.create_asset;
  Material; MaterialFactoryNew; DataAssetFactory;
  EditorAssetLibrary.save_loaded_asset;
  EditorLoadingAndSavingUtils.get_dirty_map_packages/get_dirty_content_packages/
  save_packages;
  MaterialEditingLibrary.create_material_expression/delete_all_material_expressions/
  connect_material_expressions/connect_material_property/recompile_material;
  BlendMode.BLEND_TRANSLUCENT; MaterialShadingModel.MSM_UNLIT;
  NoiseFunction.NOISEFUNCTION_GRADIENT_TEX3D;
  MaterialProperty.MP_EMISSIVE_COLOR/MP_OPACITY;
  MaterialDomain.MD_POST_PROCESS; BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING;
  SceneTextureId.PPI_POST_PROCESS_INPUT0; MaterialExpressionSceneTexture/SceneDepth/
  CameraVectorWS/Abs/DotProduct;
  MaterialExpressionConstant/Constant2Vector/ScalarParameter/VectorParameter/
  TextureCoordinate/SphereMask/PerInstanceCustomData/VertexInterpolator/
  ComponentMask/Panner/AppendVector/Noise/CameraPositionWS/WorldPosition/
  Distance/Subtract/Divide/Max/Saturate/Add/Multiply/DepthFade/Normalize/Length;
  Actor.set_actor_label/set_folder_path;
  Actor.get_folder_path; native DustfallAtmosphereFX.get_authoring_packages;
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
  GameplayStatics.begin_deferred_actor_spawn_from_class/finish_spawning_actor/
  get_player_camera_manager; Transform; SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN;
  PlayerCameraManager.get_camera_location/get_camera_rotation/get_fov_angle;
  DustfallAtmosphereFX.set_capture_save_slot; SkeletalMeshComponent.set_owner_no_see;
  SpringArmComponent.target_arm_length; CameraComponent.relative_location;
  StaticMeshComponent.set_mobility; ComponentMobility.MOVABLE;
  DA_PlayerFoundation_Phase1.FirstPersonEyeOffset;
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
    # Compact radial support: opacity is EXACTLY zero outside radius .42,
    # leaving an 8% completely transparent border on all four sides of the quad.
    radius = binary('Divide', binary('Distance', uv, center), node('Constant', r=.42))
    edge = node('Saturate')
    link(binary('Subtract', node('Constant', r=1.), binary('Multiply', radius, radius)), edge, '')
    edge = binary('Multiply', edge, edge)
    custom = node('PerInstanceCustomData', data_index=0, const_default_value=1.)
    variation = node('VertexInterpolator')
    link(custom, variation, 'VS')
    pan = node('VectorParameter', parameter_name='Pan', default_value=unreal.LinearColor(.06, .025, 0, 0))
    mask = node('ComponentMask', r=True, g=True, b=False, a=False)
    link(pan, mask, '')
    # Local Y is aligned with projected world wind in C++; stretch noise along Y.
    # Two inexpensive single-level texture-noise octaves scroll at different speeds.
    noises = []
    for frequency, speed in [(1., 1.), (1.93, 1.67)]:
        panner = node('Panner')
        link(binary('Add', uv, variation), panner, 'Coordinate')
        link(binary('Multiply', mask, node('Constant', r=speed)), panner, 'Speed')
        stretched = binary('Multiply', panner, node('Constant2Vector', r=8.*frequency, g=frequency))
        position = node('AppendVector')
        link(stretched, position, 'A'); link(node('Constant', r=0.), position, 'B')
        noise = node('Noise', noise_function=unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX3D,
                     levels=1, quality=1, scale=4., output_min=0., output_max=1.)
        link(position, noise, 'World Position')  # Lead's live-probed 5.8 pin.
        noises.append(noise)
    noise = binary('Add', node('Constant', r=.15), binary('Add',
                   binary('Multiply', noises[0], node('Constant', r=.55)),
                   binary('Multiply', noises[1], node('Constant', r=.30))))
    # Feather particles further; thin, low-opacity filaments rather than bright lenses.
    if name == 'M_DustfallMotes':
        noise = node('Constant', r=1.)
        edge = binary('Multiply', edge, edge)
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
    # Cheap flashlight scattering on existing dust geometry. Read-only runtime
    # spotlight parameters; smooth cone/range/depth fades, no extra light or pass.
    def vector(name, value):
        v = node('VectorParameter', parameter_name=name, default_value=value)
        rgb = node('ComponentMask', r=True, g=True, b=True, a=False)
        link(v, rgb, '')
        return rgb

    offset = binary('Subtract', world, vector('FlashlightPosition', unreal.LinearColor(0, 0, 0, 0)))
    normalized = node('Normalize'); link(offset, normalized, 'VectorInput')
    cosine = binary('DotProduct', normalized, vector('FlashlightDirection', unreal.LinearColor(1, 0, 0, 0)))
    outer = scalar('FlashlightCosOuter', .85)
    cone = node('Saturate')
    link(binary('Divide', binary('Subtract', cosine, outer), binary('Max',
        binary('Subtract', scalar('FlashlightCosInner', .95), outer), node('Constant', r=.001))), cone, '')
    # smoothstep cone, finite support at attenuation radius
    cone = binary('Multiply', binary('Multiply', cone, cone), binary('Subtract', node('Constant', r=3.), binary('Multiply', node('Constant', r=2.), cone)))
    length = node('Length'); link(offset, length, '')
    radial = node('Saturate')
    link(binary('Subtract', node('Constant', r=1.), binary('Divide', length,
        binary('Max', scalar('FlashlightRange', 2000.), node('Constant', r=1.)))), radial, '')
    beam = binary('Multiply', binary('Multiply', cone, binary('Multiply', radial, radial)), scalar('FlashlightGain', 0.))
    color = binary('Add', color, binary('Multiply', vector('FlashlightColor', unreal.LinearColor(1, 1, 1, 1)), beam))
    require(g.connect_material_property(color, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR), 'Emissive connection failed')
    require(g.connect_material_property(depth, '', unreal.MaterialProperty.MP_OPACITY), 'Opacity connection failed')
    g.recompile_material(m)
    require(unreal.EditorAssetLibrary.save_loaded_asset(m, False), 'Material save failed')
    return m


def horizon_material():
    """Sky-only band and halo after tonemapping, using explicit graph inputs.

    Default zero colors make this blendable neutral at weight zero. Scene depth
    gates the effect away from terrain/probes; the band never washes out silhouettes.
    HorizonColor is an additive display-space lift, not a physical fog luminance.
    """
    name = 'M_DustfallNightHorizon'
    m = unreal.load_asset(FOLDER+'/'+name)
    if not m:
        m = require(unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, FOLDER, unreal.Material, unreal.MaterialFactoryNew()), 'Horizon material creation failed')
    m.modify()
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property('blendable_location', unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    g = unreal.MaterialEditingLibrary
    g.delete_all_material_expressions(m)
    count = [0]

    def node(kind, **props):
        count[0] += 1
        n = require(g.create_material_expression(m, getattr(unreal, 'MaterialExpression'+kind),
                    (count[0] % 7)*210, (count[0] // 7)*220), 'Horizon node failed: '+kind)
        for key, value in props.items():
            n.set_editor_property(key, value)
        return n

    def link(a, b, pin, output=''):
        require(g.connect_material_expressions(a, output, b, pin), 'Horizon connection failed: '+pin)

    def binary(kind, a, b):
        n = node(kind); link(a, n, 'A'); link(b, n, 'B'); return n

    def unary(kind, a):
        n = node(kind); link(a, n, ''); return n

    def scalar(name, value):
        return node('ScalarParameter', parameter_name=name, default_value=value)

    def color(name):
        return node('VectorParameter', parameter_name=name, default_value=unreal.LinearColor(0, 0, 0, 0))

    scene = node('SceneTexture', scene_texture_id=unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    # SceneTexture's default output is float4; mask RGB for all color arithmetic.
    rgb = node('ComponentMask', r=True, g=True, b=True, a=False); link(scene, rgb, '', 'Color')
    ray = binary('Multiply', node('CameraVectorWS'), node('Constant', r=-1.))
    z = node('ComponentMask', r=False, g=False, b=True, a=False); link(ray, z, '')
    band = unary('Saturate', binary('Subtract', node('Constant', r=1.),
        binary('Divide', unary('Abs', z), scalar('HorizonWidth', .12))))
    band = binary('Multiply', band, band)
    depth = node('SceneDepth')
    sky = unary('Saturate', binary('Divide', binary('Subtract', depth, node('Constant', r=1000000.)), node('Constant', r=1000000.)))
    # Add a small display-space lift so the band remains lighter even when
    # the underlying sky already exceeds a fixed color floor. Zero is neutral.
    result = binary('Add', rgb, binary('Multiply', color('HorizonColor'), binary('Multiply', band, sky)))
    dot = binary('DotProduct', ray, node('VectorParameter', parameter_name='MoonDirection', default_value=unreal.LinearColor(0, 0, 1, 0)))
    angle = scalar('HaloRadians', .035)
    halo = unary('Saturate', binary('Subtract', node('Constant', r=1.), binary('Divide',
        binary('Subtract', node('Constant', r=1.), dot), binary('Multiply', node('Constant', r=.5), binary('Multiply', angle, angle)))))
    halo = binary('Multiply', halo, halo)
    result = binary('Add', result, binary('Multiply', color('HaloColor'), binary('Multiply', halo, sky)))
    require(g.connect_material_property(result, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR), 'Horizon emissive failed')
    g.recompile_material(m)
    require(unreal.EditorAssetLibrary.save_loaded_asset(m, False), 'Horizon material save failed')
    return m


def expected_transmittance(densities, values):
    """Horizontal, reference-height, centre ray; excludes sheets/terrain/tonemapping."""
    distances = [5, 10, 15, 25, 150]
    rows = {}
    for i, weather in enumerate(['calm', 'haze', 'storm']):
        rho = densities[i]
        extent = [values['volumetric_fog_distance'].x, values['volumetric_fog_distance'].y, values['volumetric_fog_distance'].z][i]
        extinction = [values['volumetric_extinction'].x, values['volumetric_extinction'].y, values['volumetric_extinction'].z][i]
        start = [values['fog_start_distance'].x, values['fog_start_distance'].y, values['fog_start_distance'].z][i]
        cap = [values['fog_max_opacity'].x, values['fog_max_opacity'].y, values['fog_max_opacity'].z][i]
        rows[weather] = {str(d): round(math.exp(-rho/1000*.5*extinction*min(d*100, extent))*
            max(math.exp(-rho/1000*math.log(2)**2*max(0, d*100-max(start, extent))), 1-cap), 5) for d in distances}
    return {'distances_m': distances, 'reference': 'horizontal at fog reference height, centre ray; predicted transmission, not measured contrast',
            'values': rows,
            'engine': 'HeightFogCommon.ush GetExponentialHeightFog/CalculateHeightFog/CombineVolumetricFog: analytic excludes V/cos(angle); StartDistance is an exclusion, not a blend. VolumetricFog.usf MaterialSetup/FinalIntegration: sigma=.5*rho/1000*ext, Cv=(j/sigma)*(1-Tv). Homogeneous medium, black albedo and j=C*sigma match source radiance: Cv+Tv*Ca=C*(1-Tv*Ta). NearFadeInDistance is camera-side only; no far crossfade. SceneCore.cpp divides legacy emissive settings by 10000, so component setting=10000*C*sigma. Optional read-only r.SupportExpFogMatchesVolumetricFog=1 requires effective ext=1 for source matching; table assumes project default 0.',
            'contrast_target': 'Lead measured ~4%; aim ~8%. Previous C++ .96/.51 floor=.101; baked .5/.40 floor=.263. Predicted transmission is not measured contrast; capture required.',
            'seam_option': 'Both fog systems, matched emissive source. Height falloff and second density zero; directional/sky extra inscattering off. Flashlight cone approximated on dust geometry; no physical volumetric shafts.'}


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
        initial_dirty = {p.get_path_name() for p in dirty}
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        current = list(subsystem.get_all_level_actors())
        existing = [a for a in current if isinstance(a, unreal.DustfallAtmosphereFX)]
        require(len(existing) <= 1, 'Duplicate AtmosphereFX actors: resolve explicitly before authoring')
        owned_names = {FOLDER+'/'+n for n in ['M_DustfallMotes', 'M_DustfallSheets', 'M_DustfallNightHorizon']}
        owned_names.update(['/Game/Data/DA_Atmosphere_Phase5', '/Game/Data/DA_Environment_Phase2'])
        if existing:
            owned_names.update(p.get_path_name() for p in existing[0].get_authoring_packages(False))
        else:
            # New actor/folder placement changes map structure. Existing external
            # actors can be refreshed while unrelated map edits remain unsaved.
            owned_names.add(editor.get_editor_world().get_package().get_path_name())
        folder_changed = not existing or str(existing[0].get_folder_path()) != 'DUSTFALL/Phase5'
        if existing and folder_changed:
            owned_names.add(editor.get_editor_world().get_package().get_path_name())
        conflicts = initial_dirty & owned_names
        require(not conflicts, 'Atmosphere target packages have unsaved edits; nothing changed: '+str(sorted(conflicts)))
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
        scalar_names = ['twilight_start', 'twilight_end', 'night_sky_minimum', 'night_saturation', 'night_exposure_bias', 'night_black_lift',
                        'horizon_width', 'moon_halo_degrees', 'post_process_priority', 'moon_lux', 'moon_elevation_scale', 'moon_yaw_offset',
                        'moon_disc_degrees', 'volume_forward', 'sheet_size', 'sheet_opacity_scale',
                        'sheet_drift_fraction', 'bounds_fade_fraction', 'density_feather',
                        'mote_fraction', 'mote_diameter', 'streak_width_scale', 'streak_opacity_scale', 'speck_opacity_scale',
                        'streak_reference_speed', 'streak_minimum_length_scale', 'flashlight_dust_gain',
                        'ground_dust_height', 'ground_sheet_size', 'ground_trace_distance',
                        'interior_fade_speed', 'near_fade_start', 'near_fade_end', 'depth_fade_distance']
        vectors = ['fog_max_opacity', 'fog_start_distance', 'volumetric_extinction', 'volumetric_fog_distance', 'dust_density',
                   'dust_opacity', 'dust_speed', 'wind_direction', 'volume_half_extent', 'sheet_distances',
                   'ground_dust_opacity', 'ground_sheet_heights']
        pairs = ['mote_size', 'noise_pan', 'particle_size_variation']
        colors = ['calm_fog_color', 'haze_fog_color', 'storm_fog_color', 'night_horizon_color', 'moon_halo_color', 'night_fog_color', 'night_scene_tint', 'moon_color', 'moon_disc_scale', 'day_dust_color', 'night_dust_color']
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
        require(0 <= values['mote_count'] <= 512, 'mote_count outside 0..512')
        require(values['near_fade_end'] > values['near_fade_start'] >= 0, 'Invalid near fade')
        require(values['twilight_end'] > values['twilight_start'], 'Invalid twilight interval')
        require(min(values['volume_half_extent'].x, values['volume_half_extent'].y, values['volume_half_extent'].z) > 0, 'Invalid dust volume')
        require(values['horizon_width'] > 0 and values['moon_halo_degrees'] > 0 and values['sheet_size'] > 0, 'Invalid sky/sheet dimensions')
        require(min(values['volumetric_fog_distance'].x, values['volumetric_fog_distance'].y, values['volumetric_fog_distance'].z) > 0, 'Volumetric range must be positive')
        require(min(values['volumetric_extinction'].x, values['volumetric_extinction'].y, values['volumetric_extinction'].z) >= 0, 'Negative extinction')
        require(all(0 <= v <= 1 for v in [values['fog_max_opacity'].x, values['fog_max_opacity'].y, values['fog_max_opacity'].z]), 'Fog cap outside 0..1')
        require(values['particle_size_variation'].y >= values['particle_size_variation'].x > 0, 'Invalid particle size variation')
        require(values['ground_dust_height'] > 0 and values['ground_sheet_size'] > 0 and values['ground_trace_distance'] > 0, 'Invalid ground dust dimensions')
        require(all(0 <= v < values['ground_dust_height'] for v in [values['ground_sheet_heights'].x, values['ground_sheet_heights'].y, values['ground_sheet_heights'].z]), 'Ground sheets must be below ground_dust_height')
        require(values['ground_dust_height'] <= 150, 'Ground dust must stay within 1.5m')
        require(values['streak_reference_speed'] > 0 and values['streak_width_scale'] > 0, 'Invalid streak dimensions')
        require(all(0 <= values[k] <= 1 for k in ['mote_fraction', 'streak_opacity_scale', 'speck_opacity_scale', 'sheet_opacity_scale']), 'Invalid dust opacity/fraction')
        env_data = require(unreal.load_asset('/Game/Data/DA_Environment_Phase2'), 'Environment tuning missing')
        mote = material('M_DustfallMotes')
        sheet = material('M_DustfallSheets')
        horizon = horizon_material()
        tuning = unreal.load_asset('/Game/Data/DA_Atmosphere_Phase5')
        if not tuning:
            factory = unreal.DataAssetFactory()
            factory.set_editor_property('data_asset_class', unreal.DustfallAtmosphereTuning)
            tuning = require(unreal.AssetToolsHelpers.get_asset_tools().create_asset('DA_Atmosphere_Phase5', '/Game/Data', unreal.DustfallAtmosphereTuning, factory), 'Tuning creation failed')
        tuning.modify()
        for name, value in values.items():
            tuning.set_editor_property(name, value)
        plane = require(unreal.load_asset('/Engine/BasicShapes/Plane'), 'Engine plane missing')
        for name, value in [('dust_plane', plane), ('mote_material', mote), ('sheet_material', sheet), ('horizon_material', horizon)]:
            tuning.set_editor_property(name, value)
        require(unreal.EditorAssetLibrary.save_loaded_asset(tuning, False), 'Tuning save failed')
        env_data.modify()
        env_data.set_editor_property('StormFogDensity', density)
        require(unreal.EditorAssetLibrary.save_loaded_asset(env_data, False), 'Environment tuning save failed')
        actor = existing[0] if existing else require(subsystem.spawn_actor_from_class(unreal.DustfallAtmosphereFX, unreal.Vector()), 'Actor spawn failed')
        actor.modify()
        actor.set_actor_label('Dustfall Atmosphere FX')
        if str(actor.get_folder_path()) != 'DUSTFALL/Phase5':
            require(editor.get_editor_world().get_package().get_path_name() not in initial_dirty, 'Changing actor folder needs a clean map')
            actor.set_folder_path('DUSTFALL/Phase5')
        actor.set_editor_property('is_spatially_loaded', False)
        actor.set_editor_property('tuning', tuning)
        # Only save exact target packages; material compilation may dirty dependent
        # assets and those are never swept into a global save. Folder packages are
        # included only when this operation changes the actor's folder.
        owned_names.update(p.get_path_name() for p in actor.get_authoring_packages(folder_changed))
        if not existing or folder_changed:
            owned_names.add(editor.get_editor_world().get_package().get_path_name())
        now_dirty = list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
        require(not initial_dirty & owned_names, 'Newly resolved target folder packages have unsaved edits: '+str(sorted(initial_dirty & owned_names)))
        targets = [p for p in now_dirty if p.get_path_name() in owned_names]
        require(unreal.EditorLoadingAndSavingUtils.save_packages(targets, True), 'Target package save failed')
        report['saved_packages'] = [p.get_path_name() for p in targets]
        report['preserved_dirty_packages'] = sorted(initial_dirty)
        report.update(status='authored; compile/PIE/visual/GPU acceptance required', actor=actor.get_path_name(),
                      tuning=tuning.get_path_name(), overrides=override, storm_density=density,
                      values={k: str(v) for k, v in values.items()}, transmittance=expected_transmittance([env_data.get_editor_property('CalmFogDensity'), env_data.get_editor_property('HazeFogDensity'), density], values),
                      silhouette_floor='T_volumetric * (1-FogMaxOpacity); default storm ~.263; near 15m unchanged from Lead-tuned .5/.40 split')
    except Exception as exc:
        report.update(status='failed', errors=[str(exc)])
        raise
    finally:
        OUT.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
