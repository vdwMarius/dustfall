"""Apply Phase 3 persistent dust / readable daylight tuning in the sole editor.

Keeps the Phase 2 runtime director contract. This is authoring only, not runtime
Python. Run before PCG generation, then verify actual gameplay appearance.
"""
import json
import pathlib
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
TUNING = {'CalmFogDensity': .30, 'HazeFogDensity': .60, 'StormFogDensity': 2.2,
          'SunIntensity': 42., 'DaySkyIntensity': .95, 'NightSkyIntensity': .0005,
          'StormLightMultiplier': 2.0, 'WeatherBlendSpeed': .2,
          'FogRed': .46, 'FogGreen': .23, 'FogBlue': .09,
          'WindBaseVolume': .25, 'WindStormVolume': .8}
DAY_EXPOSURE_EV100 = 0.


def main():
    override_path = ROOT/'Saved/Codex/atmosphere_override.json'
    override = json.loads(override_path.read_text()) if override_path.exists() else {}
    if not isinstance(override, dict):
        raise ValueError('Atmosphere override must be a JSON object')
    unknown = set(override) - set(TUNING)
    if unknown:
        raise ValueError('Unknown atmosphere override keys: ' + ', '.join(sorted(unknown)))
    TUNING.update(override)
    world = unreal.EditorLevelLibrary.get_editor_world()
    if '/Game/World/Maps/L_Dustfall_Foundation' not in world.get_path_name():
        raise RuntimeError('Open the foundation map first')
    data = unreal.load_asset('/Game/Data/DA_Environment_Phase2')
    if not data:
        raise RuntimeError('Phase 2 environment data missing')
    data.modify()
    for name, value in TUNING.items():
        data.set_editor_property(name, value)
    unreal.EditorAssetLibrary.save_loaded_asset(data)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    director_bp = unreal.load_asset('/Game/World/Blueprints/BP_DustfallEnvironmentDirector')
    director_cdo = unreal.get_default_object(director_bp.generated_class())
    for target in [director_cdo] + [a for a in actors if a.get_class() == director_bp.generated_class()]:
        target.modify()
        target.set_editor_property('TimeOfDay', .5)
        target.set_editor_property('CurrentFogDensity', TUNING['HazeFogDensity'])
        target.set_editor_property('EnvironmentData', data)
    unreal.EditorAssetLibrary.save_loaded_asset(director_bp)
    for actor in actors:
        if isinstance(actor, unreal.ExponentialHeightFog):
            actor.modify()
            fog = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
            fog.modify()
            fog.set_fog_density(TUNING['HazeFogDensity'])
            fog.set_fog_height_falloff(.035)
            fog.set_volumetric_fog(True)
            fog.set_fog_inscattering_color(unreal.LinearColor(.46,.29,.16,1.))
            fog.set_editor_property('volumetric_fog_scattering_distribution', .35)
            fog.set_editor_property('volumetric_fog_albedo', unreal.Color(205,169,130,255))
            fog.set_editor_property('volumetric_fog_extinction_scale', .8)
            fog.set_editor_property('volumetric_fog_distance', 18000.)
            fog.set_editor_property('start_distance', 100.)
            # Restore the known working light-energy path; the earlier warm
            # physical-scattering trial overexposed the scene into whiteout.
            fog.set_editor_property('override_light_colors_with_fog_inscattering_colors',True)
            fog.set_directional_inscattering_color(unreal.LinearColor(.3,.2,.11,1.))
        elif isinstance(actor, unreal.SkyAtmosphere):
            actor.modify()
            atmosphere = actor.get_component_by_class(unreal.SkyAtmosphereComponent)
            atmosphere.modify()
            # Reapply the project's build_world.py atmosphere, including the
            # untouched engine coefficients that the previous trial changed.
            # The project uses unusually strong absorption; changing its
            # normalized coefficient AND scale radically changed light energy.
            defaults = unreal.get_default_object(unreal.SkyAtmosphereComponent)
            atmosphere.set_rayleigh_scattering(defaults.get_editor_property('rayleigh_scattering'))
            atmosphere.set_mie_absorption(defaults.get_editor_property('mie_absorption'))
            atmosphere.set_mie_anisotropy(defaults.get_editor_property('mie_anisotropy'))
            atmosphere.set_sky_luminance_factor(defaults.get_editor_property('sky_luminance_factor'))
            atmosphere.set_rayleigh_scattering_scale(.05)
            atmosphere.set_mie_scattering_scale(3.)
            atmosphere.set_mie_scattering(unreal.LinearColor(.04,.018,.008,1.))
            atmosphere.set_mie_absorption_scale(2.)
        elif isinstance(actor, unreal.DirectionalLight):
            actor.modify()
            actor.set_actor_rotation(unreal.Rotator(pitch=-65.,yaw=-35.),False)
            light = actor.get_component_by_class(unreal.DirectionalLightComponent)
            light.modify()
            light.set_intensity(TUNING['SunIntensity'])
            light.set_light_color(unreal.LinearColor(1.,.78,.56,1.))
            light.set_editor_property('light_source_angle', 3.)
        elif isinstance(actor, unreal.SkyLight):
            actor.modify()
            sky = actor.get_component_by_class(unreal.SkyLightComponent)
            sky.modify()
            sky.set_intensity(TUNING['DaySkyIntensity'])
            sky.set_editor_property('real_time_capture', True)
        elif isinstance(actor, unreal.PostProcessVolume) and 'DF_Phase1_Exposure' in [str(t) for t in actor.tags]:
            actor.modify()
            post = actor.get_editor_property('settings')
            # The inherited EV2 lock crushed dusty daylight even after the
            # atmospheric intensities were raised. Keep exposure deterministic.
            post.set_editor_property('override_auto_exposure_min_brightness',True)
            post.set_editor_property('override_auto_exposure_max_brightness',True)
            post.set_editor_property('auto_exposure_min_brightness',DAY_EXPOSURE_EV100)
            post.set_editor_property('auto_exposure_max_brightness',DAY_EXPOSURE_EV100)
            post.set_editor_property('override_scene_color_tint',True)
            post.set_editor_property('scene_color_tint',unreal.LinearColor(1.,.65,.35,1.))
            post.set_editor_property('override_color_saturation',True)
            post.set_editor_property('color_saturation',unreal.Vector4(.75,.75,.75,1.))
            actor.set_editor_property('settings',post)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    report = {'status':'authored; visual validation required', 'tuning':TUNING,
              'exposure_ev100':DAY_EXPOSURE_EV100,
              'volumetric_extinction_scale':.8,
              'scene_color_tint':[1.,.65,.35],
              'color_saturation':.75,
              'volumetric_light_color_override':True,
              'atmosphere_baseline_restored':True,
              'visibility_target_m':{'calm_haze':40, 'storm':20},
              'applied_override':override, 'runtime_contract_preserved':True}
    (ROOT/'Saved/Codex/phase3_environment_build.json').write_text(json.dumps(report,indent=2))
    unreal.log('Phase 3 atmosphere tuned: dust-filtered daylight; verify 40 m calm/haze and 20 m storm silhouettes')


if __name__ == '__main__':
    main()
