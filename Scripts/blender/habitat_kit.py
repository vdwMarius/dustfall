"""Deterministic DUSTFALL habitat kit. Author in centimetres; export metres/FBX cm.

No external dependencies: run with Blender's Python (see README.md).
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
PALETTE = {
    'PaintedMetal': (.46, .40, .30, 1), 'BareMetal': (.29, .30, .28, 1),
    'DarkMetal': (.055, .065, .065, 1), 'Rubber': (.018, .023, .022, 1),
    'Glass': (.035, .15, .18, 1), 'Emissive_Warm': (1, .48, .12, 1),
    'Emissive_Cool': (.15, .68, 1, 1), 'InteriorPanel': (.37, .35, .29, 1),
    'Fabric': (.16, .12, .075, 1), 'Hazard': (.85, .49, .035, 1),
}
MATS = {}
PIECES = {}
PREFIX = 'SM_Hab_'
FURNISHED_LAYOUT = [
    ('Bunk',(60,-320,0)),('ShelfUnit',(20,270,0)),('Workbench',(450,265,0)),
    ('Fabricator',(520,255,99)),('Locker',(850,280,0)),('Crate_L',(820,-315,0)),
    ('Crate_S',(830,-300,72)),('Stool',(410,220,0)),('O2Tank',(950,270,0)),
    ('WallTerminal',(330,345,180)),('CableBundle',(400,300,5)),
]


def material_setup():
    for key, color in PALETTE.items():
        m = bpy.data.materials.new('M_Hab_' + key)
        m.diffuse_color = color
        m.use_nodes = True
        p = m.node_tree.nodes.get('Principled BSDF')
        p.inputs['Base Color'].default_value = color
        p.inputs['Metallic'].default_value = .65 if 'Metal' in key else .05
        p.inputs['Roughness'].default_value = .62
        if 'Emissive' in key:
            p.inputs['Emission Color'].default_value = color
            p.inputs['Emission Strength'].default_value = 3
        if key == 'Glass':
            p.inputs['Metallic'].default_value = .1
            p.inputs['Roughness'].default_value = .18
            p.inputs['Alpha'].default_value = .25
        MATS[key] = m


class Piece:
    def __init__(self, suffix, length=0):
        self.name = PREFIX + suffix
        self.length = length
        self.objects = []
        self.boxes = []
        self.sockets = []
        self.collision_objects = []
        self.mesh = None
        self.collection = bpy.data.collections.new(self.name)
        bpy.context.scene.collection.children.link(self.collection)
        PIECES[self.name] = self

    def adopt(self, obj, mat='PaintedMetal', bevel=1):
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        self.collection.objects.link(obj)
        obj.data.materials.append(MATS[mat])
        if bevel:
            mod = obj.modifiers.new('Manufactured edge radii', 'BEVEL')
            mod.width = bevel
            mod.segments = 3
        self.objects.append(obj)
        return obj

    def box(self, center, size, mat='PaintedMetal', bevel=1, rot=None):
        sx,sy,sz=(v/2 for v in size)
        o = self.raw([(-sx,-sy,-sz),(-sx,-sy,sz),(-sx,sy,-sz),(-sx,sy,sz),
                      (sx,-sy,-sz),(sx,-sy,sz),(sx,sy,-sz),(sx,sy,sz)],
                     [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)],
                     mat,min(bevel,min(size)*.499))
        o.location = center
        if rot:
            o.rotation_euler = rot
        return o

    def cylinder(self, center, radius, depth, mat='BareMetal', axis='Z', vertices=16):
        vs=[(radius*math.cos(i*2*math.pi/vertices),radius*math.sin(i*2*math.pi/vertices),z)
            for z in [-depth/2,depth/2] for i in range(vertices)]
        fs=[tuple(range(vertices-1,-1,-1)),tuple(range(vertices,2*vertices))]
        fs += [(i,(i+1)%vertices,(i+1)%vertices+vertices,i+vertices) for i in range(vertices)]
        o=self.raw(vs,fs,mat,min(1,radius*.499,depth*.499))
        o.location=center
        o.rotation_euler = {'X': (0, math.pi/2, 0), 'Y': (math.pi/2, 0, 0), 'Z': (0, 0, 0)}[axis]
        return o

    def raw(self, vertices, faces, mat='PaintedMetal', bevel=1):
        mesh = bpy.data.meshes.new(self.name + '_part')
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        o = bpy.data.objects.new('Part', mesh)
        self.collection.objects.link(o)
        return self.adopt(o, mat, bevel)

    def collision(self, center, size, rotation=0):
        # Store analytic OBBs in cm for deterministic capsule validation.
        self.boxes.append({'center': list(center), 'size': list(size), 'yaw': rotation})

    def socket(self, kind, index, position, yaw=0):
        canonical = 'SOCKET_%s_%d' % (kind, index)
        o = bpy.data.objects.new(self.name+'__'+canonical, None)
        o['socket_export_name'] = canonical
        self.collection.objects.link(o)
        o.location = position
        o.rotation_euler.z = yaw
        o.empty_display_type = 'ARROWS'
        o.empty_display_size = 30
        self.sockets.append(o)


def bolt_ring(p, center, width, height, axis='Y'):
    """Eight hex fasteners around a recessed panel, not painted bolt dots."""
    for u, v in [(-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)]:
        a, b = u*(width/2-5), v*(height/2-5)
        x, y, z = center
        pos = (x+a,y,z+b) if axis == 'Y' else ((x,y+a,z+b) if axis == 'X' else (x+a,y+b,z))
        p.cylinder(pos, 2, 2.4, 'DarkMetal', axis, 6)


def panel(p, center, width, height, axis='Y', mat='PaintedMetal', bolts=True, normal=None):
    x,y,z = center
    def shape(w,h,d):
        return (w,d,h) if axis=='Y' else ((d,w,h) if axis=='X' else (w,h,d))
    p.box(center, shape(width,height,3), 'DarkMetal', 1)
    if normal is None:
        normal = (1 if y>400 else -1) if axis=='Y' else ((-1 if x<0 else 1) if axis=='X' else (-1 if z>380 else 1))
    n = {'X':Vector((1,0,0)), 'Y':Vector((0,1,0)), 'Z':Vector((0,0,1))}[axis]*normal
    top = Vector(center)+n*2.5
    p.box(top, shape(width-5,height-5,3), mat, 1)
    if bolts:
        bolt_ring(p, Vector(center)+n*5, width-4,height-4,axis)


def vent(p, center, width=65, height=70, axis='Y'):
    panel(p, center,width,height,axis,'DarkMetal')
    x,y,z=center
    normal=(1 if y>400 else -1) if axis=='Y' else (-1 if x<0 else 1)
    for k in range(7):
        if axis=='Y': p.box((x,y+normal*6,z-height*.35+k*height*.115),(width-18,5,3),'BareMetal')
        else: p.box((x+normal*6,y,z-height*.35+k*height*.115),(5,width-18,3),'BareMetal')


def rail(p, a, b, radius=2.5, mat='BareMetal'):
    a,b=Vector(a),Vector(b)
    o=p.cylinder((a+b)/2,radius,(b-a).length,mat)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return o


def rounded_profile(half_y, bottom, top, radius, steps=8):
    pts=[]
    for cy,cz,start in [(half_y-radius,top-radius,0),(-half_y+radius,top-radius,90),
                         (-half_y+radius,bottom+radius,180),(half_y-radius,bottom+radius,270)]:
        for j in range(steps+1):
            t=math.radians(start+90*j/steps)
            pts.append((cy+radius*math.cos(t),cz+radius*math.sin(t)))
    return pts


def superellipse_loft(p, x0, x1, outer=None, inner=None, mat='PaintedMetal'):
    """Closed rounded-rectangle annular loft; rectangular limit of a superellipse.

    Explicit straight runs preserve the sanctuary's lower corner clearance.
    """
    outer=outer or rounded_profile(420,-40,440,80)
    inner=inner or rounded_profile(370,-12,400,30)
    n=len(outer)
    verts=[(x,y,z) for profile,x in [(outer,x0),(outer,x1),(inner,x0),(inner,x1)] for y,z in profile]
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces += [(i,j,n+j,n+i),(2*n+j,2*n+i,3*n+i,3*n+j),
                  (j,i,2*n+i,2*n+j),(n+i,n+j,3*n+j,3*n+i)]
    o=p.raw(verts,faces,mat,1)
    # Recalculate orientation once; shells are watertight before details are added.
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(o.data); bm.free()
    return o


def cut_box(obj, center, size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    cutter=bpy.context.object; cutter.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.context.view_layer.objects.active=obj
    # Cut before bevel to keep the aperture crisp and the bevel watertight.
    mod=obj.modifiers.new('Real opening', 'BOOLEAN'); mod.operation='DIFFERENCE'; mod.object=cutter
    bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)


def framed_opening(p, x, width=120, height=210, side=False):
    """Portal with no threshold and exactly 120 x 210 cm free space."""
    def box(c,s,mat):
        if side: c=(100+c[1],420+c[0]-x,c[2]); s=(s[1],s[0],s[2])
        p.box(c,s,mat,1.5)
    for layer,depth,spread,mat in [(0,14,0,'DarkMetal'),(1,6,7,'BareMetal'),(2,4,12,'Hazard')]:
        for sign in [-1,1]:
            box((x+layer*9,sign*(width/2+7+spread),height/2),(depth,14,height+14),'%s'%mat)
        box((x+layer*9,0,height+7+spread),(depth,width+28+2*spread,14),mat)
    for z in range(20,205,24):
        for sign in [-1,1]:
            box((x+21,sign*88,z),(3,10,9),'DarkMetal')


def shell_collision(p, length=200, side=False):
    p.collision((length/2,0,-20),(length,740,40))
    p.collision((length/2,0,420),(length,740,40))
    p.collision((length/2,-395,200),(length,50,400))
    if side:
        for x in [20,180]: p.collision((x,395,200),(40,50,400))
        p.collision((100,395,305),(120,50,190))
    else: p.collision((length/2,395,200),(length,50,400))


def hull(suffix):
    p=Piece(suffix,200)
    side=suffix.endswith('SideDoor')
    shell=superellipse_loft(p,0,200,mat='DarkMetal')
    if side: cut_box(shell,(100,405,104.5),(120,180,211))
    if suffix.endswith('_B'):
        for x in [53,147]: cut_box(shell,(x,400,205),(72,150,92))
    # Layered bands divided into serviceable plates with dark seams.
    profile=rounded_profile(423,-43,443,80)
    for i,(a,b) in enumerate(zip(profile,profile[1:]+profile[:1])):
        if (Vector(a)-Vector(b)).length<.01: continue
        mid=(Vector(a)+Vector(b))/2
        # Side flats get gridded panels below; corner plating remains a closed solid strip.
        if abs(a[0]-b[0])<.1 and abs(a[0])>420: continue
        for x0,x1 in [(3,97),(103,197)]:
            if side and mid.x>340 and mid.y<215: continue
            n=Vector((mid.x,mid.y-200)).normalized()*3
            vs=[(x,y,z) for x in [x0,x1] for y,z in [a,b,Vector(b)+n,Vector(a)+n]]
            p.raw(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],bevel=1)
    for sign in [-1,1]:
        for x in [50,150]:
            for z in [95,205,315]:
                if sign==1 and ((side and z<270) or (suffix.endswith('_B') and z==205)): continue
                panel(p,(x,sign*422,z),90,100)
        for x in [4,196]:
            if side and sign==1: continue
            p.box((x,sign*426,200),(6,9,320),'BareMetal')
        if not(side and sign==1):
            rail(p,(18,sign*435,70),(182,sign*435,70),3)
            for x in [22,178]: rail(p,(x,sign*424,70),(x,sign*438,70),4)
    for x in [5,195]:
        p.box((x,0,445),(8,650,8),'DarkMetal')
    if suffix.endswith('_B'):
        for x in [53,147]:
            # Recessed glazed apertures, backing frame does not cover the glass.
            for yy in [373,420,429]:
                for dz in [-49,49]: p.box((x,yy,205+dz),(84,8,9),'BareMetal',2)
                for dx in [-40,40]: p.box((x+dx,yy,205),(8,8,92),'BareMetal',2)
            p.box((x,398,205),(70,2,90),'Glass')
            bolt_ring(p,(x,436,205),88,112)
    if suffix.endswith('_C'):
        for x in [52,148]:
            vent(p,(x,434,190),74,110)
            p.box((x,-438,205),(72,24,90),'DarkMetal',4)
            for z in [170,235]: rail(p,(x-22,-455,z),(x+22,-455,z),3)
    if suffix.endswith('Damaged'):
        rng=random.Random(2042)
        # Torn sacrificial skin; continuous underlying pressure liner stays sealed.
        for i in range(9):
            x=26+i*18; z=255+rng.uniform(-35,35)
            vs=[(x-8,429,z-42),(x+8,430,z-36),(x+13,456+rng.random()*18,z+33),(x-10,447,z+48)]
            vs += [(a,b+3,c) for a,b,c in vs]
            p.raw(vs,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'BareMetal')
        panel(p,(103,440,114),139,84,mat='DarkMetal')
    if side:
        framed_opening(p,420,side=True)
        p.socket('Door',0,(100,420,0),math.pi/2)
    shell_collision(p,side=side)
    p.socket('Hull',0,(0,0,0),math.pi); p.socket('Hull',1,(200,0,0))
    return p


def bulkhead(suffix='EndCap_Door',length=40,half=420):
    p=Piece(suffix,length)
    profile=rounded_profile(half,-40,440,80); n=len(profile)
    verts=[(x,y,z) for x in [0,length] for y,z in profile]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    shell=p.raw(verts,faces,'PaintedMetal',2)
    cut_box(shell,(length/2,0,104.5),(length+80,120,211))
    for sign in [-1,1]:
        p.collision((length/2,sign*(half+60)/2,200),(length,half-60,400))
        for z in [85,225,350]: panel(p,(-2,sign*(half+100)/2,z),half-130,90,'X')
    p.collision((length/2,0,325),(length,120,230))
    p.collision((length/2,0,-20),(length,half*2,40))
    framed_opening(p,1)
    p.socket('Hull',0,(length,0,0)); p.socket('Door',0,(0,0,0),math.pi)
    return p


def dome():
    p=Piece('EndCap_Dome',120)
    # Closed stepped loft, with a full-size -X mating ring and recessed end disk.
    profiles=[rounded_profile(420,-40,440,80),rounded_profile(404,-25,425,78),
              rounded_profile(360,10,390,75),rounded_profile(275,65,335,65)]
    verts=[(x,y,z) for x,pr in zip([0,40,85,120],profiles) for y,z in pr]
    n=len(profiles[0]); faces=[]
    for k in range(3):
        for i in range(n): faces.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
    faces += [tuple(range(n-1,-1,-1)),tuple(3*n+i for i in range(n))]
    p.raw(verts,faces,'PaintedMetal',2)
    for y in [-220,0,220]: panel(p,(122,y,200),180,180,'X')
    p.collision((60,0,200),(120,740,400))
    p.socket('Hull',0,(0,0,0),math.pi)
    return p


def airlock():
    p=Piece('Airlock',400)
    superellipse_loft(p,0,400,rounded_profile(180,-40,300,50),rounded_profile(150,-6,270,30),'DarkMetal')
    shell_collision_air=[((200,0,-20),(400,300,40)),((200,0,285),(400,300,30))]
    for c,s in shell_collision_air: p.collision(c,s)
    for sign in [-1,1]:
        p.collision((200,sign*165,135),(400,30,270))
        for x in [50,150,250,350]: panel(p,(x,sign*181,150),90,170,normal=sign)
        p.box((200,sign*122,48),(250,38,8),'InteriorPanel',2)
        p.collision((200,sign*122,25),(250,38,50))
        rail(p,(42,sign*137,110),(358,sign*137,110),3)
    for x in [0,400]:
        framed_opening(p,x)
        for sign in [-1,1]: p.collision((x,sign*105,105),(14,90,210))
        p.collision((x,0,240),(14,300,60))
        p.socket('Door',0 if x==0 else 1,(x,0,0),math.pi if x==0 else 0)
    for x in range(25,400,50): panel(p,(x,0,-4),46,240,'Z','InteriorPanel')
    return p


def interior(suffix):
    p=Piece(suffix,200)
    if suffix=='Int_FloorPanel':
        p.box((100,0,-10),(200,730,12),'DarkMetal')
        for x in [50,150]:
            for y in [-270,-90,90,270]: panel(p,(x,y,-4),94,174,'Z','InteriorPanel')
        p.collision((100,0,-6),(200,730,12))
    elif suffix.startswith('Int_WallPanel'):
        for z in [80,210,340]: panel(p,(100,366,z),194,116,mat='InteriorPanel')
        for x in [6,194]: p.box((x,365,200),(8,12,390),'DarkMetal')
        if suffix.endswith('_B'):
            for z in [35,365,380]: rail(p,(8,350,z),(192,350,z),3)
            for x in [25,175]: panel(p,(x,347,220),34,65,mat='DarkMetal')
        if suffix.endswith('_C'):
            for x in [50,150]:
                panel(p,(x,350,205),88,270,mat='PaintedMetal')
                rail(p,(x+28,339,175),(x+28,339,220),2)
                vent(p,(x,356,280),50,45)
        p.collision((100,365,200),(200,10,400))
    elif suffix=='Int_CeilingPanel':
        for y in [-255,-85,85,255]: panel(p,(100,y,394),192,162,'Z','InteriorPanel')
        for y in [-180,180]: rail(p,(0,y,384),(200,y,384),3)
        p.collision((100,0,400),(200,680,12))
    elif suffix=='Int_CeilingLight':
        p.box((50,0,0),(100,30,12),'DarkMetal',3)
        p.box((50,0,-8),(86,19,5),'Emissive_Warm')
        for x in range(12,100,15): rail(p,(x,-14,-12),(x,14,-12),1.5)
    elif suffix=='Int_WindowFrame':
        for z in [0,105]: p.box((45,0,z),(90,14,10),'DarkMetal',3)
        for x in [4,86]: p.box((x,0,52),(8,14,104),'BareMetal',2)
        bolt_ring(p,(45,9,52),90,112)
    return p


def furniture(suffix):
    p=Piece(suffix)
    if suffix in ['Crate_S','Crate_L','Locker','Fabricator','WallTerminal']:
        w,d,h={'Crate_S':(62,52,48),'Crate_L':(115,75,72),'Locker':(80,65,210),
               'Fabricator':(125,95,125),'WallTerminal':(75,18,85)}[suffix]
        if suffix=='Fabricator':
            # Empty glazed chamber surrounded by a heavy chamfered frame.
            p.box((w/2,d/2,12),(w,d,24),'DarkMetal',5)
            p.box((w/2,d/2,h-10),(w,d,20),'PaintedMetal',5)
            for x in [10,w-10]: p.box((x,d/2,h/2),(20,d,h-28),'PaintedMetal',5)
            p.box((w/2,d-5,h/2),(w-36,10,h-30),'DarkMetal',2)
            p.box((w/2,4,65),(w-42,3,75),'Glass')
            p.box((w/2,d/2,34),(w-46,d-30,8),'BareMetal')
            for x in [32,w-32]: rail(p,(x,d-22,35),(x,d-22,99),2)
            rail(p,(32,d-22,88),(w-32,d-22,88),3)
            p.cylinder((w/2,d/2,43),20,10,'BareMetal')
            panel(p,(w-11,-3,63),16,70,'Y','DarkMetal',False)
            for z in range(38,94,8): p.box((w-11,-8,z),(7,3,3),'Emissive_Warm')
            rail(p,(34,30,h+10),(90,30,h+10),3)
            for x in [34,90]: rail(p,(x,30,h),(x,30,h+10),3)
            p.collision((w/2,d/2,h/2),(w,d,h))
        else:
            p.box((w/2,d/2,h/2),(w,d,h),'DarkMetal',4)
            panel(p,(w/2,-2,h/2),w-6,h-7,'Y','PaintedMetal')
            for z in [8,h-8]: p.box((w/2,d/2,z),(w+3,d+3,7),'BareMetal')
            if suffix=='WallTerminal':
                p.box((w/2,-9,h*.62),(w*.75,4,h*.45),'Glass')
                for x in range(12,65,8): p.box((x,-12,15),(4,3,3),'Emissive_Cool')
            else:
                rail(p,(w*.3,-10,h*.55),(w*.7,-10,h*.55),2.5)
                for x in [w*.3,w*.7]: rail(p,(x,-3,h*.55),(x,-10,h*.55),2)
                vent(p,(w/2,-5,h*.77),w*.6,min(45,h*.3))
            p.collision((w/2,d/2,h/2),(w,d,h))
    elif suffix in ['Workbench','ShelfUnit','Bunk']:
        w,d,h={'Workbench':(240,90,95),'ShelfUnit':(160,65,240),'Bunk':(230,115,65)}[suffix]
        for x in [8,w-8]:
            for y in [8,d-8]: p.box((x,y,h/2),(9,9,h),'DarkMetal',2)
        levels=[h] if suffix!='ShelfUnit' else [10,75,145,220]
        for z in levels:
            p.box((w/2,d/2,z),(w,d,8),'BareMetal',2)
            for y in [4,d-4]: p.box((w/2,y,z-8),(w,6,16),'DarkMetal')
            bolt_ring(p,(w/2,d/2,z+5),w,d,'Z')
        if suffix=='Bunk':
            p.box((w/2,d/2,h+15),(w-12,d-10,25),'Fabric',6)
            p.box((35,d/2,h+33),(50,d-20,18),'Fabric',7)
            for x in range(80,225,24): p.box((x,d/2,h+29),(2,d-8,2),'DarkMetal')
            p.collision((w/2,d/2,(h+28)/2),(w,d,h+28))
        else:
            p.collision((w/2,d/2,h/2),(w,d,h+8))
            if suffix=='Workbench':
                for x in [45,120,195]:
                    panel(p,(x,-2,65),68,35,mat='PaintedMetal')
                    rail(p,(x-17,-12,65),(x+17,-12,65),2)
    elif suffix=='Stool':
        p.cylinder((25,25,52),27,10,'Fabric',vertices=32)
        for x in [8,42]:
            for y in [8,42]: rail(p,(x,y,0),(x,y,48),3)
        for y in [8,42]: rail(p,(8,y,20),(42,y,20),2)
        p.collision((25,25,27),(54,54,54))
    elif suffix=='O2Tank':
        p.cylinder((24,24,65),23,112,'PaintedMetal',vertices=32)
        for z in [13,33,100,118]: p.cylinder((24,24,z),25,7,'DarkMetal',vertices=32)
        p.cylinder((24,24,128),7,18,'BareMetal')
        rail(p,(10,24,140),(38,24,140),3,'Hazard')
        p.collision((24,24,70),(50,50,140))
    elif suffix=='CableBundle':
        for j in range(5):
            for i in range(24):
                a=(i*8,20+j*4+12*math.sin(i*.23),8+3*math.sin(i*.37+j))
                b=((i+1)*8,20+j*4+12*math.sin((i+1)*.23),8+3*math.sin((i+1)*.37+j))
                rail(p,a,b,1.5,'Rubber')
        for x in [30,100,170]: p.box((x,30,7),(8,48,18),'BareMetal')
    return p


def accessory(suffix):
    p=Piece(suffix)
    if suffix=='DoorLeaf':
        p.box((8,0,105),(16,132,214),'DarkMetal',6)
        panel(p,(18,0,105),118,196,'X')
        vent(p,(23,0,55),66,60,'X')
        p.box((25,0,156),(4,70,30),'Glass')
        rail(p,(31,47,90),(31,47,128),3)
        p.collision((8,0,105),(16,132,210))
    elif suffix=='Collar':
        p.length=80
        superellipse_loft(p,0,80,rounded_profile(100,-20,250,25),rounded_profile(60,0,210,1),'DarkMetal')
        for x in [0,70]: framed_opening(p,x)
        for y in [-80,80]: p.collision((40,y,105),(80,40,210))
        p.collision((40,0,-10),(80,200,20)); p.collision((40,0,230),(80,200,40))
        p.socket('Door',0,(0,0,0),math.pi); p.socket('Door',1,(80,0,0))
    elif suffix=='Skid':
        p.box((80,0,-78),(160,150,20),'DarkMetal',7)
        for y in [-45,45]:
            p.box((80,y,-43),(24,25,60),'BareMetal',3)
            rail(p,(15,y,-68),(80,y,-18),7)
        p.box((80,0,-12),(150,140,16),'PaintedMetal',4)
        bolt_ring(p,(80,0,-2),145,135,'Z')
        p.collision((80,0,-50),(160,150,90))
    elif suffix=='Ramp':
        length=400; rise=math.tan(math.radians(7.5))*length
        # Ramp local -X plane is the lower end; top surface rises towards +X.
        p.length=length
        p.raw([(0,-85,-12),(0,85,-12),(400,-85,rise-12),(400,85,rise-12),
               (0,-85,0),(0,85,0),(400,-85,rise),(400,85,rise)],
              [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)],'DarkMetal')
        for x in range(10,395,18): p.box((x,0,x*rise/400+1),(4,160,2),'BareMetal')
        for y in [-89,89]: rail(p,(0,y,4),(400,y,rise+4),4,'Hazard')
        p.ramp_hull=True
        p.socket('Door',0,(400,0,rise))
    elif suffix=='RoofRack':
        for y in [-250,250]:
            rail(p,(0,y,20),(200,y,20),5)
            rail(p,(0,y,65),(200,y,65),3)
            for x in [12,188]: rail(p,(x,y,0),(x,y,65),4)
        for x in [10,65,135,190]: rail(p,(x,-250,20),(x,250,20),4)
    elif suffix=='SolarPanel':
        p.box((100,0,15),(200,180,10),'BareMetal',3)
        for x in range(8,200,24):
            for y in range(-80,90,28):
                p.box((x,y,22),(21,25,3),'Glass')
        for x in [15,185]:
            for y in [-65,65]: rail(p,(x,y,0),(x,y,14),4)
    elif suffix=='AntennaMast':
        p.box((20,0,7),(40,40,14),'DarkMetal',3)
        rail(p,(20,0,10),(20,0,300),3)
        for z in [160,240,280]: rail(p,(-40,0,z),(80,0,z),2)
        for y in [-18,18]: rail(p,(20,y,0),(20,0,95),2)
    elif suffix in ['Floodlight','ExteriorLamp']:
        large=suffix=='Floodlight'; w=70 if large else 28
        p.box((w/2,0,10),(w,30,20),'DarkMetal',3)
        p.box((w/2,-18,12),(w-10,5,12),'Emissive_Warm',2)
        for x in range(7,int(w),9): rail(p,(x,-22,3),(x,-22,21),1.5)
        for z in [0,8,16,24]: p.box((w/2,17,z),(w-4,6,2),'BareMetal')
        for x in [5,w-5]: rail(p,(x,0,-15),(x,0,0),3)
    return p


def finalize(p):
    # Evaluate modifiers without thousands of context-changing operator calls.
    bpy.context.view_layer.update()
    # Small fixtures benefit from a finer rounded edge profile; hulls retain 3.
    if p.name.removeprefix(PREFIX) in {'Skid','Ramp','RoofRack','AntennaMast','Floodlight',
            'ExteriorLamp','Int_CeilingLight','Int_WindowFrame','Fabricator','Stool','WallTerminal','O2Tank'}:
        for part in p.objects:
            for mod in part.modifiers:
                if mod.type=='BEVEL': mod.segments=10 if p.name.endswith(('CeilingLight','Stool','AntennaMast')) else 7
        bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    vertices=[]; faces=[]; face_mats=[]; mats=[]
    for part in p.objects:
        evaluated=part.evaluated_get(depsgraph); me=evaluated.to_mesh()
        offset=len(vertices)
        vertices.extend([part.matrix_world@v.co for v in me.vertices])
        indices=[]
        for m in me.materials:
            # Evaluated material IDs belong to the depsgraph; persist original IDs.
            m=bpy.data.materials.get(m.name) if m is not None else MATS['DarkMetal']
            if m not in mats: mats.append(m)
            indices.append(mats.index(m))
        for poly in me.polygons:
            faces.append(tuple(offset+i for i in poly.vertices))
            face_mats.append(indices[poly.material_index])
        evaluated.to_mesh_clear()
    for part in p.objects: bpy.data.objects.remove(part,do_unlink=True)
    me=bpy.data.meshes.new(p.name); me.from_pydata(vertices,[],faces); me.update()
    for m in mats: me.materials.append(m)
    for poly,mi in zip(me.polygons,face_mats): poly.material_index=mi
    o=bpy.data.objects.new(p.name,me); p.collection.objects.link(o)
    bpy.context.view_layer.objects.active=o; o.select_set(True)
    # Recalculate all disconnected closed components. Mechanical overlaps are intentional.
    bm=bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    # Boolean apertures can leave non-planar bevel n-gons. Triangulate before
    # weighting normals so shading agrees with the triangles UE actually draws.
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.dissolve_degenerate(bm,dist=.0001,edges=list(bm.edges))
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    for edge in bm.edges:
        if edge.is_manifold and edge.calc_face_angle()>math.radians(60): edge.smooth=False
    nonmanifold=sum(not e.is_manifold for e in bm.edges)
    assert nonmanifold==0, (p.name,nonmanifold)
    bm.to_mesh(o.data); bm.free()
    # World cube projection: 1 UV unit per 200 cm on the dominant face plane.
    uv=o.data.uv_layers.new(name='UVMap')
    for poly in o.data.polygons:
        axis=max(range(3),key=lambda i:abs(poly.normal[i]))
        axes=[i for i in range(3) if i!=axis]
        for li in poly.loop_indices:
            v=o.data.vertices[o.data.loops[li].vertex_index].co
            uv.data[li].uv=(v[axes[0]]/200,v[axes[1]]/200)
        poly.use_smooth=True
    # Weighted normals keep panel faces flat and rounded bevels smooth.
    o.data.shade_smooth()
    mod=o.modifiers.new('Area weighted normals','WEIGHTED_NORMAL'); mod.keep_sharp=True; mod.weight=50
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # At concave loft/bevel junctions an area-weighted average can cross a
    # face's tangent plane. Keep those exceptional corners in its hemisphere.
    normals=[None]*len(o.data.loops)
    for poly in o.data.polygons:
        for li in poly.loop_indices:
            normal=o.data.corner_normals[li].vector.copy()
            normals[li]=normal if normal.dot(poly.normal)>.01 else poly.normal.copy()
    o.data.normals_split_custom_set(normals)
    o.data.calc_loop_triangles()
    coords=[list(v.co) for v in o.data.vertices]
    bounds=[[round(min(v[i] for v in coords),5) for i in range(3)],
            [round(max(v[i] for v in coords),5) for i in range(3)]]
    geometry_hash=hashlib.sha256(json.dumps({'vertices':[[round(c,6) for c in v] for v in coords],
        'faces':[list(poly.vertices) for poly in o.data.polygons]},separators=(',',':')).encode()).hexdigest()
    p.record={'vertices':len(coords),'triangles':len(o.data.loop_triangles),'bounds_cm':bounds,
              'geometry_sha256':geometry_hash,'nonmanifold_edges':nonmanifold,'length_cm':p.length,
              'materials':sorted({m.name for m in o.data.materials}),
              'sockets':[{'name':s['socket_export_name'],'position_cm':list(s.location),'yaw_degrees':round(math.degrees(s.rotation_euler.z),3)} for s in p.sockets],
              'collision_boxes_cm':p.boxes}
    # Geometry now metres, object transforms all identity and origin still at datum.
    for v in o.data.vertices: v.co*=.01
    p.mesh=o
    for s in p.sockets: s.location*=.01; s.empty_display_size=.3
    for i,box in enumerate(p.boxes):
        bpy.ops.mesh.primitive_cube_add(size=1,location=Vector(box['center'])*.01)
        c=bpy.context.object; c.scale=Vector(box['size'])*.01; c.rotation_euler.z=box['yaw']
        bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        for col in list(c.users_collection): col.objects.unlink(c)
        p.collection.objects.link(c)
        c.name='UCX_%s_%02d'%(p.name,i); c.display_type='WIRE'; c.hide_render=True
        p.collision_objects.append(c)
    if getattr(p,'ramp_hull',False):
        c=bpy.data.objects.new('UCX_'+p.name+'_00',o.data.copy())
        # Use an exact convex wedge, excluding tread/rail ornament.
        me=bpy.data.meshes.new('Ramp convex wedge'); r=math.tan(math.radians(7.5))*4
        me.from_pydata([(0,-.85,-.12),(0,.85,-.12),(4,-.85,r-.12),(4,.85,r-.12),
                       (0,-.85,0),(0,.85,0),(4,-.85,r),(4,.85,r)],[],
                      [(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
        c.data=me; p.collection.objects.link(c); c.hide_render=True; p.collision_objects.append(c)
    p.record['convex_hulls']=len(p.collision_objects)
    print('KIT_PIECE',p.name,p.record['triangles'],flush=True)


def capsule_clear(center, boxes):
    """Exact distance from vertical capsule segment (r34, hh90) to yawed OBB."""
    x,y,z=center
    for b in boxes:
        cx,cy,cz=b['center']; sx,sy,sz=b['size']; yaw=b.get('yaw',0)
        dx=(x-cx)*math.cos(yaw)+(y-cy)*math.sin(yaw)
        dy=-(x-cx)*math.sin(yaw)+(y-cy)*math.cos(yaw)
        distance=[max(abs(dx)-sx/2,0),max(abs(dy)-sy/2,0),
                  max((z-56)-(cz+sz/2),(cz-sz/2)-(z+56),0)]
        # Tangent floor contact is allowed; penetration is not.
        if sum(d*d for d in distance)<34**2-.001: return False
    return True


def validate_contracts():
    # Analytic rounded rectangle membership for all 8 sanctuary corners.
    def inside(y,z):
        dy=max(abs(y)-340,0); dz=max(abs(z-200)-170,0)
        return dy*dy+dz*dz <=30**2+.00001
    assert all(inside(y,z) for y in [-325,325] for z in [0,370])
    assert 5*200>=2*475
    boxes=[]
    for k in range(5):
        for b in PIECES[PREFIX+'HullSegment_A'].boxes:
            q=dict(b); q['center']=[b['center'][0]+200*k,b['center'][1],b['center'][2]]; boxes.append(q)
    # Dome is after the 1000 cm sanctuary-bearing run; front cap/airlock before it.
    for suffix,offset in [('EndCap_Dome',1000),('EndCap_Door',-40),('Airlock',-440)]:
        for b in PIECES[PREFIX+suffix].boxes:
            q=dict(b); q['center']=[b['center'][0]+offset,b['center'][1],b['center'][2]]; boxes.append(q)
    for suffix,position in FURNISHED_LAYOUT:
        for b in PIECES[PREFIX+suffix].boxes:
            q=dict(b); q['center']=[b['center'][i]+position[i] for i in range(3)]; boxes.append(q)
    samples=0
    for y in [-20,0,20]:
        for x in range(-480,967,4):
            assert capsule_clear((x,y,90),boxes),('Aisle blocked',x,y)
            samples+=1
    # Side-branch portal and collar, including approach and both portal planes.
    branch=list(PIECES[PREFIX+'HullSegment_SideDoor'].boxes)
    for b in PIECES[PREFIX+'Collar'].boxes:
        x,y,z=b['center']; q=dict(b); q['center']=[100-y,420+x,z]; q['yaw']=math.pi/2; branch.append(q)
    for x in [80,100,120]:
        for y in range(250,550,2):
            assert capsule_clear((x,y,90),branch),('Side portal blocked',x,y)
            samples+=1
    for suffix in ['EndCap_Door','Airlock','Collar']:
        assert capsule_clear((0,0,90),PIECES[PREFIX+suffix].boxes)
    wedge=PIECES[PREFIX+'Ramp'].collision_objects[0]
    low=wedge.data.vertices[4].co*100; high=wedge.data.vertices[6].co*100
    slope=(high.z-low.z)/(high.x-low.x)
    assert abs(math.degrees(math.atan(slope))-7.5)<.001
    assert high.x-low.x==400 and abs(wedge.data.vertices[5].co.y-low.y/100)*100>=68
    normal=Vector((-slope,0,1)).normalized()
    for x in range(0,401,4):
        sphere_center=Vector((x,0,slope*x+34/normal.z))
        assert abs(normal.dot(sphere_center-low)-34)<.001
        samples+=1
    return {'sanctuary_box_cm':{'center':[500,0,185],'half_extent':[475,325,185]},
            'sanctuary_contained':True,'door_clear_cm':[120,210],
            'capsule_radius_cm':34,'capsule_half_height_cm':90,'capsule_samples':samples,
            'capsule_clear':True,'furnished_aisle_clear':True,'ramp_degrees':7.5,'ramp_capsule_clear':True,
            'scope':'Analytic UCX capsule sweeps, not Unreal CharacterMovement playtest'}


def export_piece(p,out):
    bpy.ops.object.select_all(action='DESELECT')
    for o in [p.mesh]+p.collision_objects+p.sockets: o.select_set(True)
    bpy.context.view_layer.objects.active=p.mesh
    original_names = [s.name for s in p.sockets]
    # UE's legacy FBX reader flips Y for handedness, and removes the FBX axis
    # conversion again from socket rotations. Bake that conversion here so the
    # delivered mesh AND outward socket +X match the cm contract at import scale 1.
    # Verified using the engine's FBX SDK and its exact conversion formulas.
    reflected = Matrix.Diagonal((1,-1,1,1))
    originals=[]
    for obj in [p.mesh]+p.collision_objects:
        original=obj.data; baked=original.copy()
        normals={(poly.index,baked.loops[li].vertex_index):
                    reflected.to_3x3()@baked.corner_normals[li].vector
                 for poly in baked.polygons for li in poly.loop_indices}
        baked.transform(reflected); baked.flip_normals(); baked.update()
        baked.normals_split_custom_set([normals[(poly.index,baked.loops[li].vertex_index)]
                                       for poly in baked.polygons for li in poly.loop_indices])
        obj.data=baked; originals.append((obj,original,baked))
    socket_transforms=[(s.location.copy(),s.rotation_euler.copy()) for s in p.sockets]
    for s in p.sockets:
        s.name=s['socket_export_name']; s.location.y=-s.location.y
        s.rotation_euler.z=math.pi-s.rotation_euler.z
    bpy.ops.export_scene.fbx(filepath=str(out/(p.name+'.fbx')),use_selection=True,
        object_types={'MESH','EMPTY'},global_scale=1,apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Y',axis_up='Z',
        bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',
        add_leaf_bones=False,bake_anim=False,path_mode='AUTO',use_custom_props=True)
    for s,name,(location,rotation) in zip(p.sockets,original_names,socket_transforms):
        s.name=name; s.location=location; s.rotation_euler=rotation
    for obj,original,baked in originals:
        obj.data=original; bpy.data.meshes.remove(baked)


def instance(p,location=(0,0,0),yaw=0):
    o=bpy.data.objects.new('Preview_'+p.name,p.mesh.data)
    bpy.context.scene.collection.objects.link(o)
    o.location=Vector(location)*.01; o.rotation_euler.z=yaw
    return o


def preview_setup():
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=900; scene.render.resolution_y=700; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.world.color=(.16,.16,.16)
    sh=scene.display.shading
    sh.light='STUDIO'; sh.studiolight_rotate_z=.4; sh.color_type='MATERIAL'
    sh.show_shadows=True; sh.show_cavity=True; sh.cavity_type='BOTH'
    sh.curvature_ridge_factor=1.4; sh.curvature_valley_factor=1.2
    sh.background_type='WORLD'; sh.show_specular_highlight=True
    cam_data=bpy.data.cameras.new('PreviewCamera'); cam=bpy.data.objects.new('PreviewCamera',cam_data)
    scene.collection.objects.link(cam); scene.camera=cam; cam_data.type='ORTHO'
    return cam


def render_view(out,name,objects,cam,direction=(-1.2,1.5,1.0),scale=1.2,target=None):
    for p in PIECES.values(): p.mesh.hide_render=True
    for o in objects: o.hide_render=False
    points=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
    lo=Vector([min(p[i] for p in points) for i in range(3)])
    hi=Vector([max(p[i] for p in points) for i in range(3)])
    center=(lo+hi)/2 if target is None else Vector(target)
    cam.location=center+Vector(direction).normalized()*max((hi-lo).length,5)*2
    cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    # Fit actual camera-space projected bounds, allowing landscape assembly views.
    inv=cam.rotation_euler.to_matrix().transposed()
    projected=[inv@(p-center) for p in points]
    w=max(abs(p.x) for p in projected)*2; h=max(abs(p.y) for p in projected)*2
    cam.data.ortho_scale=max(w,h*900/700)*scale
    bpy.context.scene.render.filepath=str(out/(name+'.png'))
    lights=[]
    if name==PREFIX+'Fabricator':
        # Workbench intentionally uses opaque slot colors. EEVEE reveals the
        # actual glazed chamber, print bed and gantry in the hero-prop preview.
        try: bpy.context.scene.render.engine='BLENDER_EEVEE'
        except TypeError: bpy.context.scene.render.engine='BLENDER_EEVEE_NEXT'
        for offset,energy in [((3,-4,4),700),((-3,-2,2),400),((0,3,4),900)]:
            data=bpy.data.lights.new('Preview softbox','AREA'); data.energy=energy; data.shape='DISK'; data.size=3
            light=bpy.data.objects.new('Preview softbox',data); bpy.context.scene.collection.objects.link(light)
            light.location=center+Vector(offset)
            light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
            lights.append(light)
    bpy.ops.render.render(write_still=True)
    for light in lights: bpy.data.objects.remove(light,do_unlink=True)
    bpy.context.scene.render.engine='BLENDER_WORKBENCH'
    for o in objects: o.hide_render=True


def previews(out,selected):
    out.mkdir(parents=True,exist_ok=True); cam=preview_setup()
    for p in PIECES.values():
        if p.name in selected:
            direction=(-1.2,1.5,1) if 'HullSegment' in p.name else (1.2,-1.5,1)
            render_view(out,p.name,[p.mesh],cam,direction)
    assembled=[]
    def add(s,pos=(0,0,0),yaw=0):
        o=instance(PIECES[PREFIX+s],pos,yaw); assembled.append(o); return o
    add('EndCap_Door',(-40,0,0)); add('Airlock',(-440,0,0))
    for i,s in enumerate(['A','B','C','Damaged','SideDoor']): add('HullSegment_'+s,(200*i,0,0))
    add('EndCap_Dome',(1000,0,0))
    for x in [0,200,400,600,800]:
        add('RoofRack',(x,0,445)); add('SolarPanel',(x,0,515))
        for y in [-280,280]: add('Skid',(x,y,-32))
    add('AntennaMast',(760,-180,510)); add('Ramp',(-840,0,-math.tan(math.radians(7.5))*400))
    for y in [-110,110]: add('ExteriorLamp',(-450,y,220))
    add('Collar',(900,420,0),math.pi/2)
    bpy.context.view_layer.update()
    render_view(out,'ASSEMBLED_Exterior',assembled,cam,(-1.3,1.6,.95),1.08)
    # Interior cutaway uses the actual interior modules with the near wall and roof removed.
    for o in assembled: bpy.data.objects.remove(o,do_unlink=True)
    assembled=[]
    for x in [0,200,400,600,800]:
        add('Int_FloorPanel',(x,0,0)); add('Int_WallPanel_B',(x,0,0))
    for s,pos in FURNISHED_LAYOUT: add(s,pos)
    # Far end wall made of framed panels; camera sees the usable aisle and hero machine.
    for y in [-260,-65,130]:
        o=add('Int_WallPanel_A',(1365,y,0),math.pi/2)
    bpy.context.view_layer.update()
    render_view(out,'ASSEMBLED_InteriorCutaway',assembled,cam,(-1.1,-1.5,1.25),1.08)
    for o in assembled: bpy.data.objects.remove(o,do_unlink=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=ROOT/'Saved/AssetInbox/HabitatKit')
    parser.add_argument('--only',default='')
    parser.add_argument('--preview',action='store_true'); parser.add_argument('--manifest',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    args.out=args.out.resolve()
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=1
    random.seed(2042); material_setup()
    for s in ['A','B','C','Damaged','SideDoor']: hull('HullSegment_'+s)
    bulkhead(); dome(); airlock()
    for s in ['DoorLeaf','Collar','Skid','Ramp','RoofRack','SolarPanel','AntennaMast','Floodlight','ExteriorLamp']: accessory(s)
    for s in ['FloorPanel','WallPanel_A','WallPanel_B','WallPanel_C','CeilingPanel','CeilingLight','WindowFrame']: interior('Int_'+s)
    for s in ['Bunk','ShelfUnit','Workbench','Fabricator','Locker','Crate_S','Crate_L','Stool','WallTerminal','O2Tank','CableBundle']: furniture(s)
    for p in PIECES.values(): finalize(p)
    validation=validate_contracts()
    selected=set(args.only.split(',')) if args.only else set(PIECES)
    selected={n if n.startswith(PREFIX) else PREFIX+n for n in selected}
    assert not(selected-set(PIECES)), 'Unknown pieces: '+str(selected-set(PIECES))
    args.out.mkdir(parents=True,exist_ok=True)
    for n in sorted(selected): export_piece(PIECES[n],args.out)
    manifest={'schema':1,'seed':2042,'units':'cm','blender_version':bpy.app.version_string,
              'fbx':{'blender_unit_m':1,'unreal_unit_cm':1,'global_scale':1,'forward':'-Y','up':'Z',
                     'unreal_handedness_baked':True,'socket_yaw_bake':'180 - contract yaw'},
              'validation':validation,'pieces':{n:PIECES[n].record for n in sorted(selected)}}
    if args.manifest:
        (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    if args.preview: previews(args.out/'previews',selected)
    print('KIT_COMPLETE',len(selected),'pieces',json.dumps(validation),flush=True)


if __name__=='__main__': main()
