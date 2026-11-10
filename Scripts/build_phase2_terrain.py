"""Import two locally cached Megascans surface sets for future wreck dressing.

Run in Unreal Editor Python with landscape cells loaded. This imports locally
licensed surfaces and places non-colliding engine-sphere mound placeholders;
the source library has neither a desert surface nor scatterable rock meshes.
"""
import os
import random
import json
import hashlib
import shutil
from pathlib import Path
import unreal

ROOT = Path(os.environ.get("DUSTFALL_MEGASCANS_ROOT", r"C:\Users\mario\Documents\Megascans Library\Downloaded"))
DEST = "/Game/World/Megascans/Phase2"
SETS = {
    "StainedConcrete": ("surface/concrete_damaged_vkmjddd", "vkmjddd"),
    "RustyMetal": ("surface/metal_rusty_tjxncc2aw", "tjxncc2aw"),
}


def build():
    if unreal.EditorAssetLibrary.does_asset_exist('/Game/World/Blueprints/BP_DustfallRockCell'):
        raise RuntimeError('Legacy mound builder retired. Use build_phase2_wasteland.py for scanned rock cells.')
    # Validate all source files before importing anything.
    sources = {}
    for label, (folder, ident) in SETS.items():
        sources[label] = {kind: ROOT / folder / (ident + "_2K_" + kind + ".jpg")
                          for kind in ("Albedo", "Normal", "Roughness")}
        for path in sources[label].values():
            if not path.is_file():
                raise RuntimeError("Missing source texture: " + str(path))
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    graph = unreal.MaterialEditingLibrary
    for label, files in sources.items():
        folder = DEST + "/" + label
        textures = {}
        for kind, source in files.items():
            name = "T_" + label + "_" + kind
            asset_path = folder + "/" + name
            texture = unreal.EditorAssetLibrary.load_asset(asset_path)
            if not texture:
                task = unreal.AssetImportTask()
                task.filename = str(source)
                task.destination_path = folder
                task.destination_name = name
                task.automated = True
                task.save = True
                task.replace_existing = False
                tools.import_asset_tasks([task])
                texture = unreal.EditorAssetLibrary.load_asset(asset_path)
            if not texture:
                raise RuntimeError("Texture import failed: " + asset_path)
            if kind == "Normal":
                texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                texture.set_editor_property("srgb", False)
            elif kind == "Roughness":
                texture.set_editor_property("srgb", False)
            unreal.EditorAssetLibrary.save_loaded_asset(texture)
            textures[kind] = texture
        path = folder + "/M_" + label
        material = unreal.EditorAssetLibrary.load_asset(path)
        if not material:
            material = tools.create_asset("M_" + label, folder, unreal.Material, unreal.MaterialFactoryNew())
            if not material:
                raise RuntimeError("Material creation failed: " + path)
            for i, (kind, prop) in enumerate((("Albedo", unreal.MaterialProperty.MP_BASE_COLOR),
                                               ("Normal", unreal.MaterialProperty.MP_NORMAL),
                                               ("Roughness", unreal.MaterialProperty.MP_ROUGHNESS))):
                sample = graph.create_material_expression(material, unreal.MaterialExpressionTextureSample, -500, i * 220)
                sample.set_editor_property("texture", textures[kind])
                if kind == "Normal":
                    sample.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
                elif kind == "Roughness":
                    sample.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
                graph.connect_material_property(sample, "R" if kind == "Roughness" else "RGB", prop)
            graph.recompile_material(material)
            unreal.EditorAssetLibrary.save_loaded_asset(material)
    rock_material = build_shale_material()
    scatter_prototypes(rock_material)


def build_shale_material():
    """Copy only the three self-contained texture packages at original paths."""
    source = ROOT / 'UAssets' / 'wiqmfcmn' / 'Tier2'
    metadata = json.loads((source / 'wiqmfcmn_2.json').read_text(encoding='utf-8'))
    root = '/Game/Megascans/Surfaces/Cracked_Shale_Beach_Rock_wiqmfcmn'
    if metadata.get('assetRootPath') != root:
        raise RuntimeError('Unexpected shale package root')
    entries = metadata.get('textureSets', [])
    if len(entries) != 3 or {entry['type'] for entry in entries} != {'ARD', 'albedo', 'normal'}:
        raise RuntimeError('Unexpected shale texture metadata')
    project_content = Path(unreal.Paths.project_content_dir()).resolve()
    destination = project_content / root.removeprefix('/Game/')
    files = []
    for entry in entries:
        name = entry['name']
        if not name.replace('_', '').isalnum() or entry['path'] != root + '/' + name + '.' + name:
            raise RuntimeError('Unsafe or unexpected shale texture path')
        src, dst = source / (name + '.uasset'), destination / (name + '.uasset')
        if not src.is_file():
            raise RuntimeError('Missing shale texture ' + str(src))
        if dst.exists() and hashlib.sha256(src.read_bytes()).digest() != hashlib.sha256(dst.read_bytes()).digest():
            raise RuntimeError('Existing shale texture differs; refusing overwrite: ' + str(dst))
        files.append((entry, src, dst))
    destination.mkdir(parents=True, exist_ok=True)
    for entry, src, dst in files:
        if not dst.exists():
            shutil.copy2(src, dst)
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.scan_paths_synchronous([root], True)
    textures = {}
    for entry, _, _ in files:
        texture = unreal.load_asset(entry['path'])
        if not texture or not isinstance(texture, unreal.Texture2D):
            raise RuntimeError('Could not load shale texture ' + entry['path'])
        textures[entry['type']] = texture
    path = DEST + '/M_DustyShale'
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material:
        return material
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_DustyShale', DEST, unreal.Material, unreal.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Could not create dusty shale material')
    graph = unreal.MaterialEditingLibrary
    pos = graph.create_material_expression(material, unreal.MaterialExpressionWorldPosition, -1100, -400)
    mask = graph.create_material_expression(material, unreal.MaterialExpressionComponentMask, -900, -400)
    mask.set_editor_property('r', True)
    mask.set_editor_property('g', True)
    mask.set_editor_property('b', False)
    mask.set_editor_property('a', False)
    graph.connect_material_expressions(pos, '', mask, 'Input')
    scale = graph.create_material_expression(material, unreal.MaterialExpressionMultiply, -700, -400)
    scale.set_editor_property('const_b', 0.002)
    graph.connect_material_expressions(mask, '', scale, 'A')
    samples = {}
    for i, kind in enumerate(('albedo', 'normal', 'ARD')):
        sample = graph.create_material_expression(material, unreal.MaterialExpressionTextureSample, -450, i * 240)
        sample.set_editor_property('texture', textures[kind])
        if kind == 'normal':
            sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        elif kind == 'ARD':
            sample.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
        graph.connect_material_expressions(scale, '', sample, 'UVs')
        samples[kind] = sample
    dust = graph.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, -450, -300)
    dust.set_editor_property('constant', unreal.LinearColor(0.16, 0.073, 0.037, 1))
    blend = graph.create_material_expression(material, unreal.MaterialExpressionLinearInterpolate, -100, 0)
    blend.set_editor_property('const_alpha', 0.65)
    graph.connect_material_expressions(samples['albedo'], 'RGB', blend, 'A')
    graph.connect_material_expressions(dust, '', blend, 'B')
    graph.connect_material_property(blend, '', unreal.MaterialProperty.MP_BASE_COLOR)
    graph.connect_material_property(samples['normal'], 'RGB', unreal.MaterialProperty.MP_NORMAL)
    # ORDp convention: R is occlusion and G roughness; verify visually on import.
    graph.connect_material_property(samples['ARD'], 'R', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    graph.connect_material_property(samples['ARD'], 'G', unreal.MaterialProperty.MP_ROUGHNESS)
    graph.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)
    return material


def scatter_prototypes(material):
    """Place deterministic engine-sphere placeholders only on traced landscape.

    The caller must load the landscape cells for the intended region. Missing
    cells are skipped; this is deliberately not a substitute for rock meshes.
    """
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    current = list(actors.get_all_level_actors())
    landscape = [a for a in current if isinstance(a, unreal.LandscapeProxy)]
    if not landscape:
        raise RuntimeError("Load landscape cells before building terrain prototypes")
    mesh = unreal.load_asset('/Engine/BasicShapes/Sphere.Sphere')
    if not mesh or not material:
        raise RuntimeError("Missing engine sphere or project ground material")
    world = unreal.EditorLevelLibrary.get_editor_world()
    ignore = [a for a in current if not isinstance(a, unreal.LandscapeProxy)]
    rng = random.Random(2042)
    sites = []
    for _ in range(160):
        x, y = rng.uniform(-85000, 85000), rng.uniform(-85000, 85000)
        # Keep the spawn and authored landmarks clear.
        if any((x-cx)**2 + (y-cy)**2 < radius**2 for cx, cy, radius in
               ((0, 0, 9000), (15000, 10000, 4500), (35000, -25000, 4000), (-65000, 40000, 6500))):
            continue
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 100000),
            unreal.Vector(x, y, -100000), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
            False, ignore, unreal.DrawDebugTrace.NONE, True)
        if not hit:
            continue
        z = unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method('BreakHitResult', (hit,))[5].z
        sx, sy, sz = rng.uniform(3, 12), rng.uniform(3, 10), rng.uniform(0.8, 3)
        sites.append((x, y, z, sx, sy, sz, rng.uniform(0, 360)))
    if not sites:
        raise RuntimeError("No landscape traces hit; load cells before scattering")
    for actor in current:
        if 'DF_Phase2_TerrainPrototype' in [str(t) for t in actor.tags]:
            actors.destroy_actor(actor)
    for i, (x, y, z, sx, sy, sz, yaw) in enumerate(sites):
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z - sz * 20))
        if not actor:
            raise RuntimeError('Failed to spawn terrain prototype')
        actor.set_actor_label('P2_Prototype_Mound_%03d' % i)
        actor.tags = [unreal.Name('DF_Phase2_TerrainPrototype')]
        actor.set_folder_path('DUSTFALL/Phase2_TerrainPrototypes')
        actor.static_mesh_component.set_static_mesh(mesh)
        actor.static_mesh_component.set_material(0, material)
        actor.static_mesh_component.set_collision_profile_name('NoCollision')
        actor.set_actor_scale3d(unreal.Vector(sx, sy, sz))
        actor.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    unreal.log('Placed %d traced prototype mounds; skipped unloaded cells.' % len(sites))


if __name__ == "__main__":
    build()
