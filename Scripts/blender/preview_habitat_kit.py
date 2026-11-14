"""Re-render the exported kit without rebuilding geometry (same art cameras).

blender -b -P Scripts/blender/preview_habitat_kit.py -- [--assembled-only]
"""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix

sys.path.insert(0,str(Path(__file__).resolve().parent))
import habitat_kit as kit
import habitat_art as art


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=kit.ROOT/'Saved/AssetInbox/HabitatKit')
    parser.add_argument('--assembled-only',action='store_true')
    parser.add_argument('--skip-assembled',action='store_true')
    parser.add_argument('--only',default='',help='Comma-separated piece names; assembled views are also rendered')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    kit.material_setup(); art.install(kit)
    manifest=json.loads((args.out/'manifest.json').read_text())
    for name in manifest['pieces']:
        bpy.ops.import_scene.fbx(filepath=str(args.out/(name+'.fbx')),use_custom_normals=True)
        obj=bpy.data.objects[name]
        # Undo the exporter target-handedness reflection to recover author coordinates.
        obj.data.transform(Matrix.Diagonal((1,-1,1,1))@obj.matrix_world)
        obj.data.flip_normals(); obj.matrix_world=Matrix.Identity(4)
        for i,mat in enumerate(obj.data.materials):
            obj.data.materials[i]=bpy.data.materials[mat.name.split('.')[0]]
        p=kit.Piece(name.removeprefix(kit.PREFIX)); p.mesh=obj
        for other in list(bpy.context.scene.objects):
            if other!=obj and (other.type=='EMPTY' or other.name.startswith('UCX_')):
                bpy.data.objects.remove(other,do_unlink=True)
    kit.ASSEMBLED_ONLY=args.assembled_only
    kit.SKIP_ASSEMBLED=args.skip_assembled
    selected={name if name.startswith(kit.PREFIX) else kit.PREFIX+name
              for name in args.only.split(',')} if args.only else set(kit.PIECES)
    assert selected<=set(kit.PIECES),selected-set(kit.PIECES)
    art.previews(args.out/'previews',selected)
    print('PREVIEWS_COMPLETE',flush=True)


if __name__=='__main__': main()
