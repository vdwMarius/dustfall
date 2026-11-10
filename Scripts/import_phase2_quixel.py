"""Import the twenty user-downloaded, licensed Quixel ZIPs in the open editor.

Source archives stay under ignored Saved/AssetInbox. Imports are incremental;
only project-owned /Game/World/QuixelPhase2 packages are written.
"""
import hashlib
import json
import pathlib
import zipfile
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
INBOX = ROOT / 'Saved/AssetInbox/Quixel'
DEST = '/Game/World/QuixelPhase2'
SURFACES = ['xgmpdek', 'xgimegf', 'xglmfbr', 'xgkoehf', 'xiqebhm', 'xgindb3', 'xgixbbt', 'xgincgc']
MESHES = ['xgmdcay', 'xgncbgz', 'xgndbge', 'xgkmfcy', 'xgmncdu', 'xgoqfid', 'xgjnech', 'xgjodeb', 'wcljbdb', 'ullibjd', 'wdklears', 'vkzidgds']
REPORT = ROOT / 'Saved/Codex/quixel_import_report.json'


def ensure_collision(mesh, ident):
    # Small scatter and industrial dressing are intentionally nonblocking.
    if ident not in MESHES[3:8]:
        return
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    count = sub.get_simple_collision_count(mesh) + sub.get_convex_collision_count(mesh)
    if count < 0:
        raise RuntimeError('End PIE before authoring mesh collision')
    if count == 0:
        if not sub.set_convex_decomposition_collisions(mesh, 4, 16, 100000):
            raise RuntimeError('Could not build convex rock collision: ' + ident)
        if sub.get_simple_collision_count(mesh) + sub.get_convex_collision_count(mesh) <= 0:
            raise RuntimeError('Rock collision is still empty: ' + ident)


def import_file(source, folder, name, options=None):
    path = folder + '/' + name
    existing = unreal.load_asset(path)
    if existing:
        return existing
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = True
    if options:
        task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset = unreal.load_asset(path)
    if not asset:
        raise RuntimeError('Import failed: ' + str(source) + ' -> ' + path)
    return asset


def material(ident, textures):
    path = DEST + '/' + ident + '/M_' + ident
    existing = unreal.load_asset(path)
    if existing:
        return existing
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'M_' + ident, DEST + '/' + ident, unreal.Material, unreal.MaterialFactoryNew())
    graph = unreal.MaterialEditingLibrary
    for i, (kind, prop) in enumerate([('Albedo', unreal.MaterialProperty.MP_BASE_COLOR),
                                     ('Normal', unreal.MaterialProperty.MP_NORMAL),
                                     ('Roughness', unreal.MaterialProperty.MP_ROUGHNESS)]):
        node = graph.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, i * 220)
        node.texture = textures[kind]
        if kind == 'Normal':
            node.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL
        elif kind == 'Roughness':
            node.sampler_type = unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
        if not graph.connect_material_property(node, 'R' if kind == 'Roughness' else 'RGB', prop):
            raise RuntimeError('Material connection failed: ' + path)
    graph.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return mat


def build():
    report = {'assets': [], 'errors': []}
    for ident in SURFACES + MESHES:
        archives = list(INBOX.glob('*_' + ident + '_2K_*.zip'))
        if len(archives) != 1:
            raise RuntimeError('Expected exactly one ZIP for ' + ident)
        archive = archives[0]
        source = INBOX / 'Extracted' / ident
        source.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for entry in z.infolist():
                target = (source / entry.filename).resolve()
                if not target.is_relative_to(source.resolve()):
                    raise RuntimeError('Archive contains unsafe path: ' + entry.filename)
            z.extractall(source)
        metadata = json.loads((source / (ident + '.json')).read_text(encoding='utf-8'))
        textures = {}
        for kind in ['Albedo', 'Normal', 'Roughness']:
            filename = ident + '_2K_' + kind + (('_LOD0' if kind == 'Normal' and ident in MESHES else '')) + '.jpg'
            candidate = source / filename
            if not candidate.exists() and kind == 'Normal':
                candidate = source / (ident + '_2K_Normal.jpg')
            if not candidate.exists():
                raise RuntimeError('Missing required map: ' + str(candidate))
            tex = import_file(candidate, DEST + '/' + ident, 'T_' + ident + '_' + kind)
            tex.modify()
            if kind != 'Albedo':
                tex.set_editor_property('srgb', False)
            if kind == 'Normal':
                tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            unreal.EditorAssetLibrary.save_loaded_asset(tex)
            textures[kind] = tex
        mat = material(ident, textures)
        mesh_path = None
        if ident in MESHES:
            files = sorted(source.glob('*LOD0.fbx'))
            if not files:
                files = sorted(source.glob('*.fbx'))
            if not files:
                raise RuntimeError('No mesh FBX in ' + archive.name)
            options = unreal.FbxImportUI()
            options.set_editor_property('import_mesh', True)
            options.set_editor_property('import_as_skeletal', False)
            options.set_editor_property('import_materials', False)
            options.set_editor_property('import_textures', False)
            options.set_editor_property('automated_import_should_detect_type', False)
            options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
            options.static_mesh_import_data.set_editor_property('combine_meshes', True)
            options.static_mesh_import_data.set_editor_property('auto_generate_collision', True)
            options.static_mesh_import_data.set_editor_property('build_nanite', True)
            mesh = import_file(files[0], DEST + '/' + ident, 'SM_' + ident, options)
            mesh.modify()
            mesh.set_material(0, mat)
            ensure_collision(mesh, ident)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh)
            mesh_path = mesh.get_path_name()
        report['assets'].append({'id': ident, 'name': metadata.get('name'),
            'archive': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'material': mat.get_path_name(), 'mesh': mesh_path,
            'source': 'User-owned Quixel Purchased library; ZIP supplied by user',
            'publisher': 'Quixel', 'download_date': '2026-11-10'})
        REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
        unreal.log('DUSTFALL imported ' + ident)
    unreal.log('DUSTFALL twenty-asset Quixel import complete')


if __name__ == '__main__':
    build()
