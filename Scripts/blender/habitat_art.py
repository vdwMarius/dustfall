"""Round-two industrial art builders and lit review scenes.

Centimetres throughout authoring. Structural UCX and socket contracts belong
to habitat_kit; this pass changes render geometry, never their mating planes.
"""
import math
import os
import random
import bpy
from mathutils import Vector

k = None


def profile(offset=0):
    return k.rounded_profile(420+offset,-40-offset,440+offset,170+offset,10)


def ring(p,x,half,bottom,top,radius,thickness=8,mat='PaintedMetal'):
    outer=k.rounded_profile(half,bottom,top,radius,10)
    inner=k.rounded_profile(half-thickness,bottom+thickness,top-thickness,max(1,radius-thickness),10)
    return k.superellipse_loft(p,x-4,x+4,outer,inner,mat)


FONT={
 'F':['111','100','110','100','100'], 'A':['010','101','111','101','101'],
 'B':['110','101','110','101','110'], 'R':['110','101','110','101','101'],
 'I':['111','010','010','010','111'], 'C':['111','100','100','100','111'],
 'T':['111','010','010','010','010'], 'O':['111','101','101','101','111'],
 '0':['111','101','101','101','111'], '1':['010','110','010','010','111'],
 '2':['110','001','010','100','111'], '3':['110','001','010','001','110'],
 '4':['101','101','111','001','001'], '5':['111','100','110','001','110'],
}


def label(p,text,origin,pixel=1.2,axis='Y'):
    """Raised bitmap lettering, each stroke a closed bevelled metal solid."""
    x,y,z=origin
    for n,char in enumerate(text):
        for row,line in enumerate(FONT[char]):
            for col,on in enumerate(line):
                if on!='1': continue
                a=(n*4+col)*pixel; b=(4-row)*pixel
                if axis=='Y': p.box((x+a,y,z+b),(pixel*.88,.9,pixel*.88),'BareMetal',.15)
                else: p.box((x,y+a,z+b),(.9,pixel*.88,pixel*.88),'BareMetal',.15)


def hatch(p,x,facing=-1):
    # The inner boundary remains exactly 120 x 210, including at floor level.
    # Rounded outer corners are outside that clear rectangular opening.
    for j,(half,top,rad,mat) in enumerate([(101,254,42,'PaintedMetal'),
             (91,240,34,'BareMetal'),(80,228,24,'DarkMetal')]):
        outer=k.rounded_profile(half,-18,top,rad,10)
        inner=k.rounded_profile(60,0,210,1,10)
        k.superellipse_loft(p,x+facing*j*8,x+facing*(j*8+7),outer,inner,mat)
    for sign in [-1,1]:
        for z in range(22,230,29):
            p.cylinder((x+facing*27,sign*87,z),2.5,3,'DarkMetal','X',6)
        for z in [60,170]:
            p.box((x+facing*23,sign*113,z),(27,26,28),'PaintedMetal',4)
            p.cylinder((x+facing*39,sign*113,z),6,6,'BareMetal','X')
        for z in range(15,212,24):
            p.box((x+facing*24,sign*72,z),(3,8,13),'Hazard',1)
        p.box((x+facing*13,sign*134,200),(21,28,40),'PaintedMetal',5)
        p.box((x+facing*25,sign*134,200),(5,16,24),'Emissive_Warm',3)
        for yy in [-7,7]: k.rail(p,(x+facing*29,sign*134+yy,186),(x+facing*29,sign*134+yy,214),1.4)
    p.box((x+facing*15,0,267),(28,119,22),'PaintedMetal',5)
    p.box((x+facing*30,0,263),(4,91,9),'Emissive_Warm',2)


def hull(suffix):
    p=k.Piece(suffix,200); side=suffix.endswith('SideDoor')
    damaged=suffix.endswith('Damaged'); window=suffix.endswith('_B')
    inner=k.rounded_profile(370,-12,400,45,10)
    # Larger bottom fillets fit within the rounded exterior while retaining
    # every corner of the unchanged sanctuary box.
    assert all(max(abs(y)-250,0)**2+max(130-z,z-270,0)**2<=170**2+.001 for y,z in inner)
    shell=k.superellipse_loft(p,0,200,profile(),inner,'DarkMetal')
    # Windows are 110 wide x 80 high, stacked so both fit a 200 cm module.
    apertures=[((100,415,z),(110,150,80)) for z in [154,254]] if window else []
    if side: apertures=[((100,415,104.5),(120,180,211))]
    for center,size in apertures: k.cut_box(shell,center,size)
    if damaged: k.cut_box(shell,(102,444,280),(132,112,232))
    rng=random.Random(2042+sum(map(ord,suffix)))
    pr=profile(3)
    cuts=[3,67,134,197] if suffix.endswith('_C') else [3,100,197]
    skin=[]
    for i,(a,b) in enumerate(zip(pr,pr[1:]+pr[:1])):
        av,bv=Vector(a),Vector(b); d=bv-av
        if d.length<.01: continue
        # Separate closed plates, with genuine seams across the curved shoulders.
        aa=av+d.normalized()*.55; bb=bv-d.normalized()*.55
        mid=(aa+bb)/2; normal=Vector((mid.x,mid.y-200)).normalized()
        for n,(x0,x1) in enumerate(zip(cuts,cuts[1:])):
            offset=rng.uniform(.1,.3)
            pts=[aa,bb,bb+normal*(2+offset),aa+normal*(2+offset)]
            vs=[(x,y,z) for x in [x0+.6,x1-.6] for y,z in pts]
            if (i+n+sum(map(ord,suffix)))%37==0:
                # A buckled corner in a handful of plates, still closed solids.
                vs=[(x,y-normal.x*1.8,z-normal.y*1.8) if j in [1,2] else (x,y,z)
                    for j,(x,y,z) in enumerate(vs)]
            mat='BareMetal' if (i+n+sum(map(ord,suffix)))%59==0 else 'PaintedMetal'
            obj=p.raw(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,.65)
            skin.append(obj)
            for center,size in apertures:
                if max(a[0],b[0])>340: k.cut_box(obj,center,size)
            if damaged and max(a[0],b[0])>380:
                k.cut_box(obj,(102,444,280),(132,112,232))
    for x in [2,198]: ring(p,x,427,-47,447,177,5,'BareMetal')
    for sign in [-1,1]:
        if not (sign==1 and (window or side or damaged)):
            for x,z in [(48,175),(149,237)]:
                k.panel(p,(x,sign*427,z),80,64,normal=sign)
            # Recessed grips, routed utilities and clamps.
            for x in [35,165]:
                p.box((x,sign*433,284),(36,7,15),'DarkMetal',4)
                k.rail(p,(x-13,sign*439,284),(x+13,sign*439,284),2)
        for z in [132,268]:
            if not(sign==1 and (window or side)): k.rail(p,(8,sign*434,z),(192,sign*434,z),2.1,'DarkMetal')
        for x in [18,180]:
            p.box((x,sign*437,132),(7,11,12),'BareMetal')
        p.box((36,sign*432,100),(49,4,19),'DarkMetal',2)
        label(p,'0'+str(['A','B','C','Damaged','SideDoor'].index(suffix.removeprefix('HullSegment_'))+1),
              (22,sign*436,94),1.8)
    if window:
        for z in [154,254]:
            for yy in [379,425,438]:
                for dz in [-46,46]: p.box((100,yy,z+dz),(130,12,12),'PaintedMetal',4)
                for dx in [-61,61]: p.box((100+dx,yy,z),(12,12,85),'PaintedMetal',4)
            p.box((100,408,z),(108,2,78),'Glass',1)
            p.box((100,397,z),(108,2,78),'Emissive_Warm',1)
            p.box((100,440,z-49),(139,30,9),'BareMetal',2)
            k.bolt_ring(p,(100,447,z),130,98)
    if suffix.endswith('_C'):
        for x in [48,150]: k.vent(p,(x,441,205),78,94)
        # Strapped tanks on the opposite flank; ladder on the visible side.
        for x in [53,145]:
            p.cylinder((x,-450,210),23,126,'PaintedMetal','Z',24)
            for z in [160,253]: p.cylinder((x,-450,z),25,7,'DarkMetal','Z',24)
        for x in [38,156]: k.rail(p,(x,465,-5),(x,465,354),3.5)
        for z in range(12,350,31): k.rail(p,(38,467,z),(156,467,z),2.8)
        for x in [38,156]:
            for z in [35,260]: k.rail(p,(x,420,z),(x,465,z),3)
    if damaged:
        # Torn outer skin has an actual aperture; dark inner pressure liner remains.
        for x in [53,106,159]:
            k.rail(p,(x,399,160),(x,399,389),4,'BareMetal')
        for z in [190,352]: k.rail(p,(37,400,z),(170,400,z),3,'BareMetal')
        for i in range(13):
            x=30+i*11; z=390+rng.uniform(-20,14) if i%2 else 168+rng.uniform(-18,18)
            bend=rng.uniform(22,57); dz=-52 if i%2 else 57
            vs=[(x-7,425,z),(x+9,426,z+4),(x+13,426+bend,z+dz),(x-4,443+bend,z+dz*.7)]
            vs += [(a,b+2.2,c) for a,b,c in vs]
            p.raw(vs,[(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'BareMetal',1)
        k.panel(p,(56,443,128),86,42,mat='BareMetal')
        k.panel(p,(176,441,231),34,105,mat='PaintedMetal')
        for x in [62,114,144]: k.rail(p,(x,407,175),(x+15,414,335),1.6,'Rubber')
    if side:
        k.framed_opening(p,420,side=True); p.socket('Door',0,(100,420,0),math.pi/2)
    k.shell_collision(p,side=side)
    p.socket('Hull',0,(0,0,0),math.pi); p.socket('Hull',1,(200,0,0))
    return p


def dome():
    p=k.Piece('EndCap_Dome',120); pr=profile(); n=len(pr)
    # Quarter ellipsoid: tangential at the mating rim, smoothly closes at tip.
    vertices=[]; steps=18
    for j in range(steps):
        t=j/steps*math.pi/2; s=math.cos(t)
        vertices += [(120*math.sin(t),y*s,200+(z-200)*s) for y,z in pr]
    vertices.append((120,0,200)); tip=len(vertices)-1
    faces=[tuple(range(n-1,-1,-1))]
    for j in range(steps-1):
        for i in range(n): faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    for i in range(n): faces.append(((steps-1)*n+i,(steps-1)*n+(i+1)%n,tip))
    p.raw(vertices,faces,'PaintedMetal',0)
    ring(p,3,425,-45,445,175,5,'BareMetal')
    for y in [-145,145]:
        k.panel(p,(109,y,200),75,90,'X')
    p.collision((60,0,200),(120,740,400)); p.socket('Hull',0,(0,0,0),math.pi)
    return p


def blanket(p):
    # Closed rumpled textile volume. No intersecting stripe blocks or open cloth.
    nx,ny=22,14; vertices=[]
    for layer in [0,1]:
        for i in range(nx):
            for j in range(ny):
                x=63+i*7.1; y=-3+j*9.1
                z=101+2.6*math.sin(i*.83+j*.61)+1.3*math.sin(j*1.7-i*.3)
                z-=10*(abs(y-57)/61)**6
                vertices.append((x,y,z-layer*5))
    n=nx*ny; faces=[]
    for i in range(nx-1):
        for j in range(ny-1):
            a=i*ny+j; faces += [(a,a+ny,a+ny+1,a+1),(n+a+1,n+a+ny+1,n+a+ny,n+a)]
    edge=list(range(ny))+[i*ny+ny-1 for i in range(1,nx)]+[(nx-1)*ny+j for j in range(ny-2,-1,-1)]+[i*ny for i in range(nx-2,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]): faces.append((a,b,n+b,n+a))
    p.raw(vertices,faces,'Fabric',0)


def furniture(suffix):
    p=base_furniture(suffix)
    if suffix=='Bunk':
        # Remove the old slatted blanket/pillow and replace with thick bedding.
        for obj in list(p.objects):
            if obj.location.z>89:
                p.objects.remove(obj); bpy.data.objects.remove(obj,do_unlink=True)
        p.box((32,57,99),(49,88,21),'Fabric',9)
        blanket(p)
        for x in [49,125,202]:
            k.panel(p,(x,-1,29),68,44,mat='PaintedMetal')
            k.rail(p,(x-16,-11,33),(x+16,-11,33),2.5)
        for x in [17,211]:
            p.box((x,119,69),(15,22,40),'BareMetal',2)
            k.rail(p,(x,125,87),(x,125,125),3)
    elif suffix=='ShelfUnit':
        rng=random.Random(118)
        for level in [75,145,220]:
            for i in range(5):
                x=14+i*29; h=rng.uniform(18,36)
                if i%3==0:
                    p.box((x,30,level+6+h/2),(23,35,h),'PaintedMetal',3)
                    p.box((x,10,level+12),(15,3,7),'Hazard')
                else:
                    p.cylinder((x,31,level+8+h/2),10,h,'BareMetal',vertices=16)
                    p.cylinder((x,31,level+10+h),7,4,'DarkMetal')
                    k.rail(p,(x-8,31,level+h+14),(x+8,31,level+h+14),1.5)
        # Helmet with visor and rim, and a simple wrench/tool silhouette.
        p.cylinder((40,30,35),21,30,'PaintedMetal',vertices=24)
        p.box((40,9,39),(30,4,15),'Glass',6)
        k.rail(p,(88,20,20),(130,20,20),3)
        for yy in [14,26]: k.rail(p,(126,20,20),(142,yy,20),3)
    elif suffix=='Workbench':
        for z in [24,48]:
            k.panel(p,(193,-3,z),72,21,mat='PaintedMetal')
            k.rail(p,(178,-12,z),(208,-12,z),2)
        p.cylinder((23,45,104),12,6,'DarkMetal')
        k.rail(p,(23,45,108),(23,45,143),2.5)
        k.rail(p,(23,45,143),(50,33,153),2.5)
        p.box((50,33,151),(35,22,10),'DarkMetal',4)
        p.box((50,33,145),(28,15,3),'Emissive_Warm')
        for x in [95,133,163]:
            p.box((x,47,103),(27,32,7),'PaintedMetal',2)
        # Chair behind the working position.
        p.box((108,-66,51),(55,53,11),'Fabric',5)
        p.box((108,-89,82),(56,10,57),'DarkMetal',5)
        for x in [88,128]:
            for y in [-83,-46]: k.rail(p,(x,y,1),(x,y,48),2.5)
        p.collision((108,-66,47),(56,56,94))
    elif suffix=='Fabricator':
        for x in [16,109]:
            for y in [15,80]: p.box((x,y,-2),(24,24,10),'Rubber',3)
        # Second handle, recessed print nozzle, leadscrew and visible specimen.
        k.rail(p,(34,69,135),(90,69,135),3)
        for x in [34,90]: k.rail(p,(x,69,125),(x,69,135),3)
        k.rail(p,(40,60,44),(40,60,99),2.5)
        p.box((65,58,86),(34,18,14),'BareMetal',2)
        p.cylinder((65,53,76),4,12,'DarkMetal')
        p.box((62,40,48),(25,27,11),'PaintedMetal',3)
        p.box((54,-4,111),(95,5,13),'DarkMetal',2)
        label(p,'FABRICATOR',(9,-7.5,107),2.1)
        p.box((113,-9,97),(9,3,8),'Emissive_Cool',1)
    elif suffix=='WallTerminal':
        for x in [12,34,56]:
            p.box((x,-13,53),(13,1,2),'Emissive_Cool',.3)
        for z in [42,47,58,65]: p.box((23,-13,z),(28,1,1),'Emissive_Cool',.3)
    elif suffix=='Stool':
        p.box((25,48,79),(49,9,43),'DarkMetal',5)
        for x in [8,42]: k.rail(p,(x,45,45),(x,48,91),2)
    return p


def interior(suffix):
    if suffix=='Int_AlcoveFrame':
        p=k.Piece(suffix,60)
        # Opening 180 x 220 with 60 cm deep sill; collision keeps it open.
        for x in [8,52]:
            ring(p,x,112,-20,244,25,12,'PaintedMetal')
        for y in [-100,100]:
            p.box((30,y,110),(60,20,220),'DarkMetal',3)
            p.collision((30,y,110),(60,20,220))
        p.box((30,0,-10),(75,224,20),'BareMetal',3)
        p.box((30,0,233),(60,224,26),'PaintedMetal',3)
        p.collision((30,0,-10),(75,224,20)); p.collision((30,0,233),(60,224,26))
        p.socket('Door',0,(0,0,0),math.pi); p.socket('Door',1,(60,0,0))
        return p
    p=base_interior(suffix)
    if suffix.startswith('Int_WallPanel'):
        # Pull the upper wall lining around the shoulder instead of leaving
        # v1's rectangular panel corners protruding through the curved hull.
        bpy.context.view_layer.update()
        from mathutils import Matrix
        for obj in p.objects:
            transform=obj.matrix_world.copy()
            for vertex in obj.data.vertices:
                co=transform@vertex.co
                co.y-=max(co.z-275,0)**2*.003
                vertex.co=co
            obj.matrix_world=Matrix.Identity(4)
        # Shoulder rib and utilities integrated in every wall segment.
        pts=[(360,275),(358,320),(346,355),(320,382),(275,391),(180,391),(0,391)]
        for x in [8,192]:
            for a,b in zip(pts,pts[1:]): k.rail(p,(x,*a),(x,*b),4,'BareMetal')
        for y,z in [(300,375),(311,368),(321,359)]: k.rail(p,(0,y,z),(200,y,z),2,'Rubber')
        for x in [25,100,175]: p.box((x,309,369),(8,40,9),'BareMetal')
        p.box((110,348,295),(110,25,43),'DarkMetal',3)
        for z in range(281,312,6): p.box((110,333,z),(95,5,2),'BareMetal')
        p.box((46,337,185),(61,12,91),'DarkMetal',2)
        for x in [23,35,47,59,71]:
            k.rail(p,(x,328,150),(x+5,328,210),1.5,'Rubber')
        p.box((11,321,187),(25,4,91),'PaintedMetal',2,rot=(0,0,-.65))
        p.box((149,336,235),(46,23,55),'PaintedMetal',3)
        for z in [220,244]: k.rail(p,(151,325,z),(151,311,z),2.5)
        p.box((110,336,342),(132,16,13),'DarkMetal',3)
        p.box((110,325,342),(119,5,6),'Emissive_Cool',2)
    elif suffix=='Int_CeilingPanel':
        # Curved transverse ribs with cable trays following the shoulder profile.
        pts=k.rounded_profile(360,2,391,65,10)
        top=[v for v in pts if v[1]>=270]
        for x in [8,192]:
            for a,b in zip(top,top[1:]): k.rail(p,(x,*a),(x,*b),4,'BareMetal')
        for y in [-180,180]:
            for yy in [y-16,y+16]: k.rail(p,(0,yy,376),(200,yy,376),2,'DarkMetal')
            for x in range(10,200,22): k.rail(p,(x,y-16,376),(x,y+16,376),1.3)
    elif suffix=='Int_WindowFrame':
        # Replace v1's small frame with matching 110 x 80 clear aperture.
        for obj in list(p.objects): bpy.data.objects.remove(obj,do_unlink=True)
        p.objects=[]
        for z in [-6,86]: p.box((55,0,z),(134,22,12),'PaintedMetal',4)
        for x in [-6,116]: p.box((x,0,40),(12,22,80),'PaintedMetal',3)
        p.box((55,-13,-11),(144,42,10),'BareMetal',2)
        k.bolt_ring(p,(55,-14,40),132,100)
    return p


def accessory(suffix):
    p=base_accessory(suffix)
    if suffix=='DoorLeaf':
        # Paint the door itself, including its heavy rounded face.
        for obj in p.objects:
            if obj.data.materials and obj.data.materials[0]==k.MATS['DarkMetal'] and obj.location.z==105:
                obj.data.materials[0]=k.MATS['PaintedMetal']
        k.vent(p,(-5,0,85),65,65,'X')
        p.box((-7,0,158),(4,66,31),'Emissive_Warm',6)
        for yy in [-39,39]: p.box((-10,yy,158),(5,9,44),'BareMetal',2)
        for z in [136,180]: p.box((-10,0,z),(5,86,8),'BareMetal',2)
        k.rail(p,(-16,-44,70),(-16,-44,119),3)
    elif suffix=='Skid':
        # Lower render geometry and its matching attachment hull together.
        for obj in p.objects:
            obj.location.z*=.48
            for v in obj.data.vertices: v.co.z*=.48
        for b in p.boxes: b['center'][2]*=.48; b['size'][2]*=.48
        rng=random.Random(69)
        for i in range(13):
            p.box((rng.uniform(-8,170),rng.choice([-1,1])*rng.uniform(52,83),-38),
                  (rng.uniform(17,39),rng.uniform(15,32),rng.uniform(9,22)),'DarkMetal',3,
                  (rng.uniform(-.15,.15),rng.uniform(-.2,.2),rng.uniform(-.8,.8)))
    elif suffix=='SolarPanel':
        # Tilt geometry about local X on triangular support frames.
        angle=math.radians(23)
        from mathutils import Matrix
        rot=Matrix.Rotation(angle,4,'X')
        p.box((100,0,20),(192,173,3),'DarkMetal',1)
        bpy.context.view_layer.update()
        for obj in p.objects:
            obj.matrix_world=rot@obj.matrix_world
            obj.location.z+=36
        for x in [16,184]:
            k.rail(p,(x,-77,0),(x,-77,20),3)
            k.rail(p,(x,77,0),(x,77,82),3)
            k.rail(p,(x,-77,0),(x,77,82),2.5)
        k.rail(p,(12,85,5),(194,85,5),1.7,'Rubber')
    return p


def airlock():
    p=base_airlock()
    for obj in p.objects:
        if obj.data.materials and obj.data.materials[0]==k.MATS['DarkMetal']:
            obj.data.materials[0]=k.MATS['PaintedMetal']
    hatch(p,0,-1); hatch(p,400,1)
    for x in [8,130,265,392]: ring(p,x,185,-45,305,55,5,'BareMetal')
    for x in [80,180,280]:
        for sign in [-1,1]:
            p.box((x,sign*186,81),(76,7,32),'BareMetal',3)
    return p


def bulkhead(*args,**kwargs):
    # Use the same large-radius silhouette as adjoining hull, with unchanged UCX.
    original=k.rounded_profile
    def rounded(half,bottom,top,radius,steps=8):
        if half==420 and bottom==-40: radius=170
        return original(half,bottom,top,radius,steps)
    k.rounded_profile=rounded
    try: p=base_bulkhead(*args,**kwargs)
    finally: k.rounded_profile=original
    return p


def setup_preview():
    scene=bpy.context.scene; scene.render.engine='CYCLES'
    scene.cycles.samples=24; scene.cycles.use_denoising=True
    cache=k.ROOT/'Saved/AssetInbox/HabitatKit/OptixCache'
    cache.mkdir(parents=True,exist_ok=True)
    os.environ['OPTIX_CACHE_PATH']=str(cache)
    prefs=bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type='OPTIX'; prefs.get_devices()
        if any(d.type=='OPTIX' for d in prefs.devices):
            for device in prefs.devices: device.use=device.type=='OPTIX'
            scene.cycles.device='GPU'
    except (TypeError,RuntimeError):
        scene.cycles.device='CPU'
    scene.render.resolution_x=1600; scene.render.resolution_y=1200
    scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.24,.27,.32,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.32
    scene.view_settings.view_transform='AgX'
    # Glazed panes are transmissive, with separate warm pane behind each window.
    glass=k.MATS['Glass'].node_tree.nodes.get('Principled BSDF')
    glass.inputs['Transmission Weight'].default_value=.88
    glass.inputs['Base Color'].default_value=(.3,.48,.51,1)
    glass.inputs['Roughness'].default_value=.16
    glass.inputs['Alpha'].default_value=1
    # A thin review glazing mix preserves legibility of untextured mechanisms.
    # The slot remains M_Hab_Glass; Unreal assigns its own production shader.
    tree=k.MATS['Glass'].node_tree
    transparent=tree.nodes.new('ShaderNodeBsdfTransparent')
    transparent.inputs[0].default_value=(.75,.87,.93,1)
    mix=tree.nodes.new('ShaderNodeMixShader'); mix.inputs[0].default_value=.18
    tree.links.new(transparent.outputs[0],mix.inputs[1])
    tree.links.new(glass.outputs[0],mix.inputs[2])
    tree.links.new(mix.outputs[0],tree.nodes.get('Material Output').inputs['Surface'])
    tree=bpy.data.node_groups.new('Review glow','CompositorNodeTree')
    scene.compositing_node_group=tree
    nodes=tree.nodes
    source=nodes.new('CompositorNodeRLayers'); glow=nodes.new('CompositorNodeGlare')
    glow.inputs['Type'].default_value='Fog Glow'
    glow.inputs['Quality'].default_value='Medium'
    glow.inputs['Threshold'].default_value=1.8
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    output=nodes.new('NodeGroupOutput')
    tree.links.new(source.outputs['Image'],glow.inputs['Image'])
    tree.links.new(glow.outputs['Image'],output.inputs['Image'])
    data=bpy.data.cameras.new('Review camera'); cam=bpy.data.objects.new('Review camera',data)
    scene.collection.objects.link(cam); scene.camera=cam
    return cam


def render(out,name,objects,cam,direction=(-1.3,1.5,.7),eye=None,target=None):
    scene=bpy.context.scene
    for p in k.PIECES.values(): p.mesh.hide_render=True
    for obj in objects: obj.hide_render=False
    bpy.context.view_layer.update()
    points=[obj.matrix_world@Vector(c) for obj in objects for c in obj.bound_box]
    lo=Vector([min(v[i] for v in points) for i in range(3)])
    hi=Vector([max(v[i] for v in points) for i in range(3)])
    center=(lo+hi)/2
    if eye:
        cam.data.type='PERSP'; cam.data.lens=19
        cam.location=eye; aim=Vector(target)
        cam.rotation_euler=(aim-cam.location).to_track_quat('-Z','Y').to_euler()
    else:
        cam.data.type='ORTHO'; cam.location=center+Vector(direction).normalized()*max((hi-lo).length,4)*2
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        inv=cam.rotation_euler.to_matrix().transposed(); projected=[inv@(v-center) for v in points]
        cam.data.ortho_scale=max(max(abs(v.x) for v in projected)*2,
            max(abs(v.y) for v in projected)*2*1600/1200)*1.13
    # Soil meets the ramp toe; the rubble skirts/pads settle into it.
    ground_z=-.65 if name in {'ASSEMBLED_Exterior','ASSEMBLED_RearDamage'} else min(lo.z-.02,-.01)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(center.x,center.y,ground_z))
    ground=bpy.context.object
    if 'Review soil' not in bpy.data.materials:
        m=bpy.data.materials.new('Review soil'); m.diffuse_color=(.12,.095,.065,1); m.use_nodes=True
        bs=m.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value=(.12,.095,.065,1)
        bs.inputs['Roughness'].default_value=.95
    ground.data.materials.append(bpy.data.materials['Review soil'])
    lights=[]
    extent=max((hi-lo).length,3)
    for vec,power,size,color in [((-1.1,1.4,.65),48, .65,(1,.73,.47)),
                                   ((.1,-.8,1.3),14,.9,(.65,.79,1)),
                                   ((1.2,.4,1.1),28,.65,(1,.91,.76))]:
        data=bpy.data.lights.new('Review softbox','AREA'); data.energy=power*extent**2
        data.shape='DISK'; data.size=extent*size; data.color=color
        obj=bpy.data.objects.new('Review softbox',data); scene.collection.objects.link(obj)
        obj.location=center+Vector(vec)*extent
        obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler(); lights.append(obj)
    if eye:
        for pos,color,power in [((2,0,3.1),(1,.56,.24),95),((5,1.8,3.1),(.36,.65,1),80),((8,0,3.1),(1,.63,.3),110)]:
            data=bpy.data.lights.new('Practical bounce','POINT'); data.energy=power; data.color=color; data.shadow_soft_size=.5
            obj=bpy.data.objects.new('Practical bounce',data); scene.collection.objects.link(obj); obj.location=pos; lights.append(obj)
    if name==k.PREFIX+'Fabricator' or eye:
        data=bpy.data.lights.new('Chamber inspection light','POINT')
        data.energy=6; data.color=(.48,.76,1); data.shadow_soft_size=.06
        obj=bpy.data.objects.new('Chamber inspection light',data); scene.collection.objects.link(obj)
        obj.location=(5.83,2.95,1.84) if eye else (.63,.4,.85)
        lights.append(obj)
    scene.render.filepath=str(out/(name+'.png')); bpy.ops.render.render(write_still=True)
    for obj in lights+[ground]: bpy.data.objects.remove(obj,do_unlink=True)
    for obj in objects: obj.hide_render=True


def previews(out,selected):
    out.mkdir(parents=True,exist_ok=True); cam=setup_preview()
    for p in k.PIECES.values():
        if p.name in selected and not getattr(k,'ASSEMBLED_ONLY',False):
            direction=(-1.2,1.5,.8) if 'HullSegment' in p.name or p.name.endswith(('Airlock','DoorLeaf','AlcoveFrame')) else (1.2,-1.5,.8)
            render(out,p.name,[p.mesh],cam,direction)
    if getattr(k,'SKIP_ASSEMBLED',False): return
    assembled=[]
    def add(s,pos=(0,0,0),yaw=0):
        obj=k.instance(k.PIECES[k.PREFIX+s],pos,yaw); assembled.append(obj); return obj
    add('EndCap_Door',(-40,0,0)); add('Airlock',(-440,0,0))
    # Closed hero hatch only dresses the review; the separate sliding leaf is unchanged.
    add('DoorLeaf',(-469,0,0))
    for i,s in enumerate(['A','B','C','Damaged','A']): add('HullSegment_'+s,(200*i,0,0))
    add('EndCap_Dome',(1000,0,0))
    for x in [0,200,400,600,800]:
        add('RoofRack',(x,0,425)); add('SolarPanel',(x+200,0,485),math.pi)
        for y in [-280,280]: add('Skid',(x,y,-32))
    for x,y,factor in [(760,-180,1),(100,-180,.62),(940,120,.45)]:
        obj=add('AntennaMast',(x,y,490)); obj.scale.z=factor
    add('Ramp',(-840,0,-math.tan(math.radians(7.5))*400))
    for x in [15,380,790,985]:
        for y in [-358,358]: add('ExteriorLamp',(x,y,363),math.pi if y>0 else 0)
    render(out,'ASSEMBLED_Exterior',assembled,cam,(-1.4,1.65,.75))
    render(out,'ASSEMBLED_RearDamage',assembled,cam,(1.35,1.55,.65))
    for obj in assembled: bpy.data.objects.remove(obj,do_unlink=True)
    assembled=[]
    for x in [0,200,400,600,800]:
        add('Int_FloorPanel',(x,0,0)); add('Int_WallPanel_B',(x,0,0))
        add('Int_WallPanel_C',(x+200,0,0),math.pi)
        add('Int_CeilingPanel',(x,0,0)); add('Int_CeilingLight',(x+50,0,374))
    for s,pos in k.FURNISHED_LAYOUT: add(s,pos)
    # Frame a future planted alcove at the far end; its empty opening is visible.
    add('Int_AlcoveFrame',(960,0,0))
    for y in [-365,90]:
        obj=add('Int_WallPanel_A',(1365,y,0),math.pi/2); obj.scale.x=1.375
    obj=add('Int_WallPanel_A',(1365,-90,220),math.pi/2)
    obj.scale.x=.9; obj.scale.z=.425
    add('EndCap_Dome',(1060,0,0))
    render(out,'ASSEMBLED_InteriorCutaway',assembled,cam,eye=(-3.1,-.45,1.65),target=(5,.2,1.68))
    for obj in assembled: bpy.data.objects.remove(obj,do_unlink=True)


def install(module):
    global k,base_furniture,base_interior,base_accessory,base_airlock,base_bulkhead
    k=module
    base_furniture=k.furniture; base_interior=k.interior; base_accessory=k.accessory
    base_airlock=k.airlock; base_bulkhead=k.bulkhead
    for name in ['hull','dome','bulkhead','airlock','interior','furniture','accessory','previews']:
        setattr(k,name,globals()[name])
