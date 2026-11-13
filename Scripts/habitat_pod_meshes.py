"""Project-owned industrial pod geometry; no runtime Python dependency.

Writes deterministic OBJ sources under Intermediate, imported by habitat builder.
Rounded pressure hulls are continuous superellipse sections, with real thickness,
panel gaps, inset windows and a deliberately torn outer rear panel. Coordinates cm.
"""
import math
import random
from pathlib import Path


class Mesh:
    def __init__(self): self.vertices=[]; self.faces=[]
    def quad(self, *points):
        start=len(self.vertices)+1
        self.vertices.extend(points); self.faces.append(tuple(range(start,start+4)))
    def write(self,path):
        lines=['# DUSTFALL project-owned curved industrial geometry','o '+path.stem]
        for x,y,z in self.vertices: lines.append('v %.6f %.6f %.6f'%(x,y,z))
        for face in self.faces:
            p,q,r=[self.vertices[i-1] for i in face[:3]]
            a=[q[i]-p[i] for i in range(3)]; b=[r[i]-p[i] for i in range(3)]
            normal=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
            dominant=max(range(3),key=lambda i:abs(normal[i]))
            axes=[i for i in range(3) if i!=dominant]
            # Physical metre-scale UVs keep normal detail continuous across
            # subdivided curves rather than repeating once per thin segment.
            for index in face:
                v=self.vertices[index-1]
                lines.append('vt %.6f %.6f'%(v[axes[0]]/100,v[axes[1]]/100))
        lines.append('s 1')
        for face in self.faces:
            lines.append('f '+' '.join('%d/%d'%(i,i) for i in face))
        path.write_text('\n'.join(lines)+'\n')


def section(angle, width=420, height=240, z=240, inset=0):
    c,s=math.cos(angle),math.sin(angle)
    return ((width-inset)*math.copysign(abs(c)**.5,c),
            z+(height-inset)*math.copysign(abs(s)**.5,s))


def panel(mesh,x0,x1,t0,t1,width=420,height=240,z=240,depth=8):
    steps=max(1,int(abs(t1-t0)*32))
    for i in range(steps):
        a=t0+(t1-t0)*i/steps; b=t0+(t1-t0)*(i+1)/steps
        ya,za=section(a,width,height,z); yb,zb=section(b,width,height,z)
        ia,ja=section(a,width,height,z,depth); ib,jb=section(b,width,height,z,depth)
        mesh.quad((x0,yb,zb),(x1,yb,zb),(x1,ya,za),(x0,ya,za))
        mesh.quad((x0,ia,ja),(x1,ia,ja),(x1,ib,jb),(x0,ib,jb))
        mesh.quad((x0,ia,ja),(x1,ia,ja),(x1,ya,za),(x0,ya,za))
        mesh.quad((x0,yb,zb),(x1,yb,zb),(x1,ib,jb),(x0,ib,jb))
        if i==0: mesh.quad((x0,ya,za),(x0,yb,zb),(x0,ib,jb),(x0,ia,ja))
        if i==steps-1: mesh.quad((x1,ia,ja),(x1,ib,jb),(x1,yb,zb),(x1,ya,za))


def cap(mesh,x,outer=(420,240,240),inner=None,segments=96):
    for i in range(segments):
        a=2*math.pi*i/segments; b=2*math.pi*(i+1)/segments
        ya,za=section(a,*outer); yb,zb=section(b,*outer)
        if inner:
            ia,ja=section(a,*inner); ib,jb=section(b,*inner)
        else: ia,ja=0,outer[2]; ib,jb=ia,ja
        mesh.quad((x,ya,za),(x,yb,zb),(x,ib,jb),(x,ia,ja))
        mesh.quad((x-10,ia,ja),(x-10,ib,jb),(x-10,yb,zb),(x-10,ya,za))


def generate(root):
    directory=Path(root)/'Intermediate/Codex/PodMeshes'; directory.mkdir(parents=True,exist_ok=True)
    meshes={name:Mesh() for name in ['HullPanels','PressureLiner','HullRibs','EndCaps','WindowGlass','AirlockBarrel','DoorFrame','DamagePetals','RustScars','LowerGrime','RepairPlates']}
    # Axial construction bays, 16 curved perimeter panels per bay. Two apertures
    # per flank are actually omitted from metal and filled by inset glass.
    for bay,(x0,x1) in enumerate([(-510,-345),(-345,-180),(-180,-15),(-15,150),(150,315),(315,510)]):
        for j in range(16):
            # Superellipse derivatives grow at the cardinal axes: a constant
            # angular gap there becomes a large world-space hole. Keep seams
            # near one centimetre throughout the rounded section.
            a=2*math.pi*j/16+(.00002 if j%4==0 else .002)
            b=2*math.pi*(j+1)/16-(.00002 if (j+1)%4==0 else .002)
            window=bay in [3,4] and j in [0,7,8,15]
            torn=bay==0 and j in [1,2,3]
            if not window and not torn: panel(meshes['HullPanels'],x0+1.5,x1-1.5,a,b)
            if window:
                if j in [0,8]: wa,wb=2*math.pi*j/16,a+.045
                else: wa,wb=b-.045,2*math.pi*(j+1)/16
                if wa>a: panel(meshes['HullPanels'],x0+1.5,x1-1.5,a,wa)
                if wb<b: panel(meshes['HullPanels'],x0+1.5,x1-1.5,wb,b)
                panel(meshes['WindowGlass'],x0+9,x1-9,wa,wb,414,234,240,5)
                # Metal bridge at each side closes the inset glazing aperture.
                panel(meshes['HullRibs'],x0+1,x0+9,wa,wb,422,242,240,10)
                panel(meshes['HullRibs'],x1-9,x1-1,wa,wb,422,242,240,10)
            if not window: panel(meshes['PressureLiner'],x0,x1,a,b,406,226,240,4)
    for x in [-515,-345,-180,-15,150,315,510]:
        panel(meshes['HullRibs'],x-4,x+4,0,2*math.pi,427,247,240,8)
    # Curved end shoulder/rear dome rather than a square flat wall.
    for step in range(12):
        t0=step*math.pi/24; t1=(step+1)*math.pi/24
        for j in range(96):
            a=j*math.pi/48; b=(j+1)*math.pi/48
            y0,z0=section(a); y1,z1=section(b)
            meshes['HullPanels'].quad((-510-125*math.sin(t0),y0*math.cos(t0),240+(z0-240)*math.cos(t0)),
                (-510-125*math.sin(t1),y0*math.cos(t1),240+(z0-240)*math.cos(t1)),
                (-510-125*math.sin(t1),y1*math.cos(t1),240+(z1-240)*math.cos(t1)),
                (-510-125*math.sin(t0),y1*math.cos(t0),240+(z1-240)*math.cos(t0)))
    cap(meshes['EndCaps'],510,inner=(170,174,215))
    cap(meshes['EndCaps'],-510)
    # Airlock enclosure is also curved, while its tested door and floor contract
    # stay at x500/1000, floor z50 and 180/220cm doorway widths.
    panel(meshes['AirlockBarrel'],515,1005,0,2*math.pi,222,195,220,12)
    cap(meshes['DoorFrame'],1015,outer=(238,210,220),inner=(126,151,194))
    cap(meshes['DoorFrame'],995,outer=(229,201,220),inner=(128,153,194))
    for index in range(7):
        a=.38+index*.09
        panel(meshes['DamagePetals'],-509+index*9,-354+index*6,a,a+.055,432+index*5,255+index*4,240,5)
    rng=random.Random(783)
    # Authored finish damage follows actual curved panel surfaces, never planar
    # decals floating away from the hull. Small irregular chipped clusters mix
    # with long runoff below structural seams and dark lower dust accumulation.
    for i in range(95):
        x=rng.uniform(-495,490); a=rng.choice([0,math.pi])+rng.uniform(-.85,.85)
        length=rng.uniform(7,38); height=rng.uniform(.007,.035)
        panel(meshes['RustScars'],x,min(508,x+length),a,a+height,421.5,241.5,240,1)
    for x in [-345,-180,-15,315]:
        for a in [.18,math.pi-.18]:
            panel(meshes['RustScars'],x+7,x+rng.uniform(14,24),a,a+.30,421.6,241.6,240,1)
    for bay in range(6):
        for a in [-.62,math.pi+.20]:
            panel(meshes['LowerGrime'],-508+bay*169,-343+bay*169,a,a+.32,421.1,241.1,240,1)
    for x,a in [(-260,.08),(-80,math.pi-.25),(345,.35)]:
        panel(meshes['RepairPlates'],x,x+105,a,a+.14,424,244,240,3)
    paths={}
    for name,mesh in meshes.items():
        path=directory/('SM_Pod_'+name+'.obj'); mesh.write(path); paths[name]=path
    return paths


if __name__=='__main__':
    generate(Path(__file__).resolve().parents[1])
