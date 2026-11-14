"""Headless FBX round-trip check. Usage: blender -b -P this.py -- <kit-dir>."""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def main():
    source_root=Path(__file__).resolve().parents[2]
    ast.parse((source_root/'Scripts/import_phase5_habitat_kit.py').read_text())
    parser=argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    parser.add_argument('--compare',type=Path,help='Second independent generation directory')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    root=args.root.resolve()
    manifest=json.loads((root/'manifest.json').read_text())
    results={}
    for name,expected in manifest['pieces'].items():
        bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.fbx(filepath=str(root/(name+'.fbx')),use_custom_normals=True)
        obj=bpy.data.objects.get(name)
        assert obj is not None, name
        def unreal_position(v): return Vector((v.x,-v.y,v.z))*100
        points=[unreal_position(obj.matrix_world@v.co) for v in obj.data.vertices]
        actual=[[min(v[i] for v in points) for i in range(3)],
                [max(v[i] for v in points) for i in range(3)]]
        assert all(abs(actual[j][i]-expected['bounds_cm'][j][i])<.01 for j in range(2) for i in range(3)),(name,actual)
        obj.data.calc_loop_triangles()
        assert len(obj.data.loop_triangles)==expected['triangles'],name
        assert len(obj.data.uv_layers)==1,name
        assert all(math.isfinite(c) for uv in obj.data.uv_layers[0].data for c in uv.uv),name
        assert all(obj.data.corner_normals[li].vector.dot(poly.normal)>0
                   for poly in obj.data.polygons for li in poly.loop_indices), ('Inverted normals',name)
        hulls=[o for o in bpy.context.scene.objects if o.name.startswith('UCX_'+name+'_')]
        assert len(hulls)==expected['convex_hulls'],(name,len(hulls))
        for s in expected['sockets']:
            empty=bpy.data.objects.get(s['name']); assert empty is not None,(name,s['name'])
            assert (unreal_position(empty.matrix_world.translation)-Vector(s['position_cm'])).length<.01
            outward=empty.matrix_world.to_3x3()@Vector((1,0,0))
            outward=Vector((-outward.x,outward.y,outward.z))
            yaw=math.radians(s['yaw_degrees'])
            assert (outward-Vector((math.cos(yaw),math.sin(yaw),0))).length<.0001
        results[name]={'triangles':len(obj.data.loop_triangles),'bounds_cm':actual,
                       'convex_hulls':len(hulls),'sockets':len(expected['sockets']),'uv0':True}
        print('ROUNDTRIP_PASS',name,flush=True)
    report={'status':'passed','pieces':results,'scope':'Blender FBX round trip; Unreal importer not executed'}
    if args.compare:
        first=(root/'manifest.json').read_bytes()
        second=(args.compare/'manifest.json').read_bytes()
        assert first==second,'Independent generation manifests differ'
        report['determinism']={'status':'passed','pieces':len(results),
            'manifest_sha256':hashlib.sha256(first).hexdigest(),
            'scope':'Byte-identical manifests including mesh hashes, counts, bounds, sockets and UCX'}
    (root/'fbx_roundtrip.json').write_text(json.dumps(report,indent=2)+'\n')
    print('ROUNDTRIP_COMPLETE',len(results),flush=True)


if __name__=='__main__': main()
