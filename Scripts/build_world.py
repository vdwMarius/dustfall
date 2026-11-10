"""Create the Phase 1 foundation map. Run from Unreal Editor Python.

The Open World template supplies the partitioned landscape. Habitat construction
runs separately. DA_Atmosphere_Phase1 holds the authoring values; the constants
below initialize new fields and leave existing authored values intact.
"""
import unreal

MAP = "/Game/World/Maps/L_Dustfall_Foundation"
TEMPLATE = "/Engine/Maps/Templates/OpenWorld"
ATMOSPHERE = {"FogDensity": 0.045, "FogHeightFalloff": 0.025,
              "FogRed": 0.30, "FogGreen": 0.115, "FogBlue": 0.055,
              "SunIntensity": 3.0, "SunRed": 1.0, "SunGreen": 0.56,
              "SunBlue": 0.32, "SkyIntensity": 0.45, "ExposureEV100": 2.0}


def _atmosphere_data():
    """Create Blueprint data asset type and authoring instance for rebuilds."""
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    blueprint_factory = unreal.BlueprintFactory()
    blueprint_factory.set_editor_property("parent_class", unreal.PrimaryDataAsset)
    bp_path = "/Game/Data/BP_AtmosphereData"
    bp = unreal.EditorAssetLibrary.load_asset(bp_path) if unreal.EditorAssetLibrary.does_asset_exist(bp_path) else None
    if not bp:
        bp = tools.create_asset("BP_AtmosphereData", "/Game/Data", None, blueprint_factory)
    if not bp:
        raise RuntimeError("Could not create atmosphere data Blueprint")
    pin = unreal.BlueprintEditorLibrary.get_basic_type_by_name("real")
    existing = list(unreal.BlueprintEditorLibrary.list_member_variable_names(bp, False))
    added = []
    for name in ATMOSPHERE:
        if name not in existing and not unreal.BlueprintEditorLibrary.add_member_variable(bp, name, pin):
            raise RuntimeError("Could not create atmosphere field " + name)
        if name not in existing:
            added.append(name)
        unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp, name, True)
    if not unreal.BlueprintEditorLibrary.compile_blueprint(bp):
        raise RuntimeError("Could not compile atmosphere data Blueprint")
    factory = unreal.DataAssetFactory()
    factory.set_editor_property("data_asset_class", bp.generated_class())
    data_path = "/Game/Data/DA_Atmosphere_Phase1"
    data = unreal.EditorAssetLibrary.load_asset(data_path) if unreal.EditorAssetLibrary.does_asset_exist(data_path) else None
    new_data = not data
    if new_data:
        data = tools.create_asset("DA_Atmosphere_Phase1", "/Game/Data", None, factory)
    if not data:
        raise RuntimeError("Could not create atmosphere data asset")
    if new_data:
        for name, value in ATMOSPHERE.items():
            data.set_editor_property(name, value)
    elif (abs(data.get_editor_property("FogDensity") - 0.025) < 0.00001 and
          abs(data.get_editor_property("FogHeightFalloff") - 0.12) < 0.00001):
        # Migrate the untouched first-pass defaults, preserving authored changes.
        data.set_editor_property("FogDensity", ATMOSPHERE["FogDensity"])
        data.set_editor_property("FogHeightFalloff", ATMOSPHERE["FogHeightFalloff"])
    if not new_data:
        for name in added:
            data.set_editor_property(name, ATMOSPHERE[name])
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(data)
    return {name: data.get_editor_property(name) for name in ATMOSPHERE}


def _one_actor(actor_type, label):
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    found = [a for a in actors if isinstance(a, actor_type)]
    if found:
        return found[0]
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_type, unreal.Vector())
    if not actor:
        raise RuntimeError("Could not create " + label)
    actor.set_actor_label(label)
    return actor


def _ground_material():
    path = "/Game/World/Materials/M_Dustfall_Ground"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_Dustfall_Ground", "/Game/World/Materials", unreal.Material, unreal.MaterialFactoryNew())
    if not material:
        raise RuntimeError("Could not create ground material")
    graph = unreal.MaterialEditingLibrary
    color = graph.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -400, -100)
    color.set_editor_property("constant", unreal.LinearColor(0.16, 0.073, 0.037, 1.0))
    graph.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    roughness = graph.create_material_expression(material, unreal.MaterialExpressionConstant, -400, 100)
    roughness.set_editor_property("r", 0.92)
    graph.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
    graph.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    return material


def build_world():
    if unreal.EditorAssetLibrary.does_asset_exist('/Game/World/Blueprints/BP_DustfallEnvironmentDirector'):
        raise RuntimeError('Phase 2 exists. Use its environment/world builders; Phase 1 would reset lighting and spawn.')
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        if not levels.load_level(MAP):
            raise RuntimeError("Unable to load " + MAP)
    elif not levels.new_level_from_template(MAP, TEMPLATE):
        raise RuntimeError("Unable to create map from " + TEMPLATE)

    settings = _atmosphere_data()
    mode = unreal.load_class(None, "/Game/Core/BP_DustfallGameMode.BP_DustfallGameMode_C")
    if not mode:
        raise RuntimeError("Player GameMode class not found")
    unreal.EditorLevelLibrary.get_editor_world().get_world_settings().set_editor_property("default_game_mode", mode)

    # The template cloud layer is a bright terrestrial placeholder.
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        if (isinstance(actor, unreal.VolumetricCloud) or
                (isinstance(actor, unreal.StaticMeshActor) and actor.get_actor_label() == "SM_SkySphere")):
            unreal.EditorLevelLibrary.destroy_actor(actor)

    fog = _one_actor(unreal.ExponentialHeightFog, "Dust Fog")
    component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog.modify()
    component.modify()
    component.set_fog_density(settings["FogDensity"])
    component.set_fog_height_falloff(settings["FogHeightFalloff"])
    component.set_fog_inscattering_color(unreal.LinearColor(settings["FogRed"], settings["FogGreen"], settings["FogBlue"], 1.0))
    component.set_volumetric_fog(True)

    # Replace the template's bright blue Rayleigh sky with suspended warm dust.
    atmosphere = _one_actor(unreal.SkyAtmosphere, "Dustfall Sky")
    sky_atmosphere = atmosphere.get_component_by_class(unreal.SkyAtmosphereComponent)
    atmosphere.modify()
    sky_atmosphere.modify()
    sky_atmosphere.set_rayleigh_scattering_scale(0.05)
    sky_atmosphere.set_mie_scattering_scale(3.0)
    sky_atmosphere.set_mie_scattering(unreal.LinearColor(0.04, 0.018, 0.008, 1.0))
    sky_atmosphere.set_mie_absorption_scale(2.0)

    sun = _one_actor(unreal.DirectionalLight, "Dustfall Sun")
    sun_component = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun.modify()
    sun_component.modify()
    sun_component.set_intensity(settings["SunIntensity"])
    sun_component.set_light_color(unreal.LinearColor(settings["SunRed"], settings["SunGreen"], settings["SunBlue"], 1.0))

    sky = _one_actor(unreal.SkyLight, "Dustfall Skylight")
    sky_component = sky.get_component_by_class(unreal.SkyLightComponent)
    sky.modify()
    sky_component.modify()
    sky_component.set_intensity(settings["SkyIntensity"])

    exposure_volumes = [a for a in unreal.EditorLevelLibrary.get_all_level_actors()
                        if isinstance(a, unreal.PostProcessVolume) and
                        "DF_Phase1_Exposure" in [str(tag) for tag in a.tags]]
    volume = exposure_volumes[0] if exposure_volumes else unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PostProcessVolume, unreal.Vector())
    volume.modify()
    volume.set_actor_label("Dustfall Exposure")
    volume.tags = [unreal.Name("DF_Phase1_Exposure")]
    volume.set_editor_property("unbound", True)
    post = volume.get_editor_property("settings")
    post.set_editor_property("override_auto_exposure_min_brightness", True)
    post.set_editor_property("override_auto_exposure_max_brightness", True)
    post.set_editor_property("auto_exposure_min_brightness", settings["ExposureEV100"])
    post.set_editor_property("auto_exposure_max_brightness", settings["ExposureEV100"])
    post.set_editor_property("override_bloom_intensity", True)
    post.set_editor_property("bloom_intensity", 0.25)
    volume.set_editor_property("settings", post)

    ground_material = _ground_material()
    landscapes = [a for a in unreal.EditorLevelLibrary.get_all_level_actors()
                  if isinstance(a, unreal.LandscapeProxy)]
    for landscape in landscapes:
        landscape.modify()
        landscape.set_editor_property("landscape_material", ground_material)
    if not landscapes:
        unreal.log_warning("No loaded landscape actor; ground material needs assignment in the editor.")

    # Trace the template landscape before placing a solid, flat spawn surface.
    world = unreal.EditorLevelLibrary.get_editor_world()
    # Ignore our own prior blockout when rebuilding.
    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    previous = [a for a in all_actors if "DF_Phase1_World" in [str(tag) for tag in a.tags]]
    ignored = previous + [a for a in all_actors
                          if "DF_Phase1_Habitat_Blockout" in [str(tag) for tag in a.tags]]
    result = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(0, 0, 100000), unreal.Vector(0, 0, -100000),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignored,
        unreal.DrawDebugTrace.NONE, True)
    if result:
        ground = unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method('BreakHitResult', (result,))[5]
    else:
        # Partition cells can be unloaded during a commandlet; verify the spawn
        # against the loaded landscape in PIE and adjust if necessary.
        unreal.log_warning("Landscape trace missed; using Z=0 for the landing pad. Verify in PIE.")
        ground = unreal.Vector(0, 0, 0)
    for actor in previous:
        unreal.EditorLevelLibrary.destroy_actor(actor)
    pad = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(ground.x, ground.y, ground.z + 25.0))
    pad.set_actor_label("Foundation Landing Pad")
    pad.tags = [unreal.Name("DF_Phase1_World")]
    mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
    if not mesh:
        raise RuntimeError("Engine cube mesh is unavailable")
    pad.static_mesh_component.set_static_mesh(mesh)
    pad.static_mesh_component.set_material(0, ground_material)
    pad.set_actor_scale3d(unreal.Vector(20.0, 20.0, 0.5))
    global HABITAT_ORIGIN
    HABITAT_ORIGIN = (ground.x, ground.y, ground.z + 50.0)

    starts = [a for a in unreal.EditorLevelLibrary.get_all_level_actors()
              if isinstance(a, unreal.PlayerStart)]
    start = starts[0] if starts else unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.PlayerStart, unreal.Vector())
    start.modify()
    start.set_actor_location(unreal.Vector(ground.x + 550.0, ground.y, ground.z + 150.0), False, False)
    start.set_actor_rotation(unreal.Rotator(0.0, 0.0, 180.0), False)
    start.set_actor_label("Foundation Player Start")

    if not levels.save_current_level():
        raise RuntimeError("Failed to save " + MAP)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    levels.save_all_dirty_levels()
    unreal.log("DUSTFALL foundation map created: " + MAP)


if __name__ == "__main__":
    build_world()
