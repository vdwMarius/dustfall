"""Build the temporary Phase 1 habitat in the currently open level.

Run in the Unreal Editor's Python environment after opening the target level.
The lead/world setup owns the level, terrain and PlayerStart. Save the level
after reviewing the result. All geometry here is a replaceable blockout.
"""
import unreal


HABITAT_ORIGIN = globals().get("HABITAT_ORIGIN", (0.0, 0.0, 0.0))  # Ground plane; cm.
TAG = "DF_Phase1_Habitat_Blockout"
ASSET_DIR = "/Game/Habitat/Blockout"


def position(x, y, z):
    return unreal.Vector(HABITAT_ORIGIN[0] + x, HABITAT_ORIGIN[1] + y,
                         HABITAT_ORIGIN[2] + z)


def material(name, color, roughness, emissive=None):
    path = ASSET_DIR + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.EditorAssetLibrary.load_asset(path)
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, ASSET_DIR, unreal.Material, unreal.MaterialFactoryNew())
    if not asset:
        raise RuntimeError("Could not create " + path)
    editing = unreal.MaterialEditingLibrary
    base = editing.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector, -400, -100)
    base.set_editor_property("constant", unreal.LinearColor(*color, 1.0))
    editing.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = editing.create_material_expression(asset, unreal.MaterialExpressionConstant, -400, 100)
    rough.set_editor_property("r", roughness)
    editing.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    if emissive:
        glow = editing.create_material_expression(asset, unreal.MaterialExpressionConstant3Vector, -400, 300)
        glow.set_editor_property("constant", unreal.LinearColor(*emissive, 1.0))
        editing.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    editing.recompile_material(asset)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    return asset


def build():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Only replace actors previously created by this script.
    for actor in actors.get_all_level_actors():
        if TAG in [str(tag) for tag in actor.tags]:
            actors.destroy_actor(actor)

    cube = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
    if not cube:
        raise RuntimeError("Engine cube mesh not found")
    shell = material("M_Hab_Blockout_DustyMetal", (0.16, 0.115, 0.085), 0.86)
    dark = material("M_Hab_Blockout_Dark", (0.055, 0.044, 0.035), 0.9)
    amber = material("M_Hab_Beacon_Emissive", (0.48, 0.19, 0.035), 0.65,
                     (2.0, 0.65, 0.10))

    def box(label, center, scale, mat, collision=True):
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, position(*center))
        actor.set_actor_label(label)
        actor.tags = [unreal.Name(TAG)]
        actor.set_folder_path("DUSTFALL/Habitat_Blockout")
        component = actor.static_mesh_component
        component.set_static_mesh(cube)
        component.set_material(0, mat)
        component.set_collision_profile_name("BlockAll" if collision else "NoCollision")
        actor.set_actor_scale3d(unreal.Vector(*scale))
        return actor

    # Unreal's engine cube is 100 cm across with a centred pivot.
    box("Hab_Base_Temporary", (0, 0, 10), (6.4, 4.4, 0.2), dark)
    box("Hab_Shell_Temporary", (0, 0, 150), (6, 4, 2.8), shell)
    box("Hab_Sealed_Entrance_Temporary", (320, 0, 130), (0.4, 1.6, 2.4), dark)
    box("Hab_Roof_Strip_Temporary", (0, 0, 295), (5.2, 0.35, 0.1), dark, False)
    box("Hab_Beacon_Housing_Temporary", (0, 0, 315), (0.35, 0.35, 0.3), amber, False)
    box("Hab_Entrance_Lamp_Temporary", (345, 0, 265), (0.15, 0.65, 0.15), amber, False)

    light = actors.spawn_actor_from_class(unreal.PointLight, position(0, 0, 345))
    light.set_actor_label("Hab_Warm_Landmark_Temporary")
    light.tags = [unreal.Name(TAG)]
    light.set_folder_path("DUSTFALL/Habitat_Blockout")
    component = light.point_light_component
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
    component.set_intensity(850.0)
    component.set_light_color(unreal.LinearColor(1.0, 0.42, 0.12, 1.0))
    component.set_attenuation_radius(1000.0)
    component.set_editor_property("volumetric_scattering_intensity", 0.25)

    entrance_light = actors.spawn_actor_from_class(unreal.PointLight, position(370, 0, 260))
    entrance_light.set_actor_label("Hab_Entrance_Light_Temporary")
    entrance_light.tags = [unreal.Name(TAG)]
    entrance_light.set_folder_path("DUSTFALL/Habitat_Blockout")
    entrance_component = entrance_light.point_light_component
    entrance_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    entrance_component.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
    entrance_component.set_intensity(850.0)
    entrance_component.set_light_color(unreal.LinearColor(1.0, 0.42, 0.12, 1.0))
    entrance_component.set_attenuation_radius(1000.0)
    entrance_component.set_editor_property("volumetric_scattering_intensity", 0.25)
    entrance_component.set_editor_property("cast_shadows", False)
    unreal.log("DUSTFALL habitat blockout built. Review and save the open level.")


if __name__ == "__main__":
    build()
