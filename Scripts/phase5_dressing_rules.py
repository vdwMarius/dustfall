"""Pure editor-authoring geometry. No Unreal dependency or runtime Python.

Masks: uint8 row 0=minY, column 0=minX, extrema inclusive (native v2).
Corridors use analytic segments, not the lower-resolution texture mask.
"""
import math
import random


def project(x, y, line):
    best = None
    arc = 0.
    total = sum(math.dist(a[:2], b[:2]) for a, b in zip(line, line[1:]))
    for a, b in zip(line, line[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if not length:
            continue
        t = max(0., min(1., ((x-a[0])*dx+(y-a[1])*dy)/length**2))
        px, py = a[0]+t*dx, a[1]+t*dy
        d = math.hypot(x-px, y-py)
        row = (d, (dx*(y-py)-dy*(x-px))/length, (dx/length, dy/length), (arc+t*length)/total)
        if best is None or d < best[0]:
            best = row
        arc += length
    if best is None:
        raise ValueError('Degenerate polyline')
    return best


class Inputs:
    def __init__(self, rules, features, paths, bounds, size, path_mask, cliff_mask):
        self.rules, self.features, self.paths = rules, features, paths
        self.bounds, self.size = bounds, size
        if len(path_mask) != size*size or len(cliff_mask) != size*size:
            raise ValueError('Native terrain masks must be size squared uint8')
        self.path_mask, self.cliff_mask = path_mask, cliff_mask
        self.discs = features['resolved']['discs_cm']
        self.corridors = [(p['polyline_cm'], p['width_cm']/2) for p in paths]
        self.corridors += [(r['line_cm'], features['protection']['route_inner_cm']) for r in features['resolved']['routes']]
        # Native paths have samples every metre. Index exact segments so audits
        # of 50k instances do not scan every path sample for every footprint.
        self.segment_grid = {}; self.grid_size = rules['cell_size_cm']/10
        for line,half in self.corridors:
            for start,end in zip(line,line[1:]):
                record=(start,end,half)
                for ix in range(math.floor((min(start[0],end[0])-half)/self.grid_size),math.floor((max(start[0],end[0])+half)/self.grid_size)+1):
                    for iy in range(math.floor((min(start[1],end[1])-half)/self.grid_size),math.floor((max(start[1],end[1])+half)/self.grid_size)+1):
                        self.segment_grid.setdefault((ix,iy),[]).append(record)
        self.walls = [f for f in features['features'] if f['type'] in ('canyon', 'escarpment')]

    def mask(self, data, x, y):
        a,b,c,d = self.bounds
        if not a <= x <= c or not b <= y <= d:
            return 0
        ix = round((x-a)/(c-a)*(self.size-1)); iy = round((y-b)/(d-b)*(self.size-1))
        return data[iy*self.size+ix]

    def clear(self, x, y, radius):
        a,b,c,d = self.bounds
        if not a+radius <= x <= c-radius or not b+radius <= y <= d-radius:
            return False
        if any(math.hypot(x-cx, y-cy) < r+radius for cx,cy,r in self.discs):
            return False
        seen=set()
        for ix in range(math.floor((x-radius)/self.grid_size),math.floor((x+radius)/self.grid_size)+1):
            for iy in range(math.floor((y-radius)/self.grid_size),math.floor((y+radius)/self.grid_size)+1):
                for start,end,half in self.segment_grid.get((ix,iy),[]):
                    key=(id(start),id(end),half)
                    if key in seen:continue
                    seen.add(key)
                    if project(x,y,[start,end])[0]<half+radius:return False
        return True

    def cluster(self, x, y):
        n = self.rules['noise']; angle = math.radians(n['wind_yaw_degrees'])
        u=(x*math.cos(angle)+y*math.sin(angle))/n['along_scale_cm']
        v=(-x*math.sin(angle)+y*math.cos(angle))/n['across_scale_cm']
        phase=self.rules['seed']*.017
        return (math.sin(u+phase)+math.sin(v+math.sin(u*.71))+2)/4

    def wall(self, x, y):
        """Distance to top of talus, tangent and normalized foot-to-rim position."""
        best = None
        for f in self.walls:
            d,s,t,alpha = project(x,y,f['line_cm'])
            if f['type']=='canyon':
                floor=(f['floor_width_cm'][0]*(1-alpha)+f['floor_width_cm'][1]*alpha)/2
                rim=(f['rim_width_cm'][0]*(1-alpha)+f['rim_width_cm'][1]*alpha)/2
                cross=(d-floor)/(rim-floor)
                knots=f['north_wall'] if s>=0 else f['south_wall']
                distance=abs(cross-knots[1][0])*(rim-floor)
            else:
                span=f['talus_width_cm']+f['face_width_cm']
                cross=(s*f['high_side']+f['talus_width_cm'])/span
                distance=abs(cross-f['wall'][1][0])*span
            row=(distance,t,cross)
            if best is None or distance<best[0]: best=row
        return best


def candidates(inputs):
    """Stable seeded candidate order; acceptance uses actual landscape normals."""
    r=inputs.rules; rng=random.Random(r['seed']); a,b,c,d=inputs.bounds
    for kind in ('flats','slopes','talus','cliffs'):
        rule=r[kind]; step=rule['step_cm']
        for iy in range(math.ceil((d-b)/step)):
            for ix in range(math.ceil((c-a)/step)):
                x=a+(ix+rng.random())*step; y=b+(iy+rng.random())*step
                mask=inputs.mask(inputs.cliff_mask,x,y)
                if kind=='talus' and mask!=85: continue
                if kind=='cliffs' and mask!=255: continue
                if kind in ('flats','slopes') and mask in (85,255): continue
                if kind=='flats' and inputs.cluster(x,y)<r['noise']['bare_threshold']: continue
                if rng.random()>rule['keep_probability']: continue
                yield kind,x,y,rng.getrandbits(31),None
    # Trace rim positions derived from the exact rounded feature controls.
    for f in inputs.walls:
        total=sum(math.dist(a,b) for a,b in zip(f['line_cm'],f['line_cm'][1:])); arc=0.
        for p,q in zip(f['line_cm'],f['line_cm'][1:]):
            length=math.dist(p,q); nx,ny=-(q[1]-p[1])/length,(q[0]-p[0])/length
            for j in range(max(1,math.ceil(length/r['rims']['step_cm']))):
                t=j/max(1,math.ceil(length/r['rims']['step_cm'])); alpha=(arc+t*length)/total
                offsets=[s*((f['rim_width_cm'][0]*(1-alpha)+f['rim_width_cm'][1]*alpha)/2+r['rims']['rim_offset_cm']) for s in (-1,1)] if f['type']=='canyon' else [f['high_side']*(f['face_width_cm']+r['rims']['rim_offset_cm'])]
                for offset in offsets:
                    yield 'rims',p[0]+t*(q[0]-p[0])+nx*offset,p[1]+t*(q[1]-p[1])+ny*offset,rng.getrandbits(31),None
            arc+=length
    for path in inputs.paths:
        arc=0.; next_stone=0.; next_stake=0.
        for p,q in zip(path['polyline_cm'],path['polyline_cm'][1:]):
            length=math.dist(p[:2],q[:2])
            if not length: continue
            nx,ny=-(q[1]-p[1])/length,(q[0]-p[0])/length
            for kind,next_arc in [('edges',next_stone),('stakes',next_stake)]:
                while next_arc<arc+length:
                    t=(next_arc-arc)/length
                    center_x=p[0]+t*(q[0]-p[0]);center_y=p[1]+t*(q[1]-p[1])
                    edge_half=path['width_cm']/2
                    for route in inputs.features['resolved']['routes']:
                        distance=project(center_x,center_y,route['line_cm'])[0]
                        half=inputs.features['protection']['route_inner_cm']
                        if distance<half:edge_half=max(edge_half,half+distance)
                    for side in (-1,1) if kind=='edges' else (1,):
                        offset=edge_half+(rng.uniform(*r['edges']['offset_cm']) if kind=='edges' else r['stakes']['offset_cm'])
                        yield kind,p[0]+t*(q[0]-p[0])+nx*offset*side,p[1]+t*(q[1]-p[1])+ny*offset*side,rng.getrandbits(31),None
                    next_arc+=r[kind]['spacing_cm']
                if kind=='edges': next_stone=next_arc
                else: next_stake=next_arc
            arc+=length


def footprint(bounds, scale, pitch=0, roll=0):
    """Yaw invariant conservative XY radius and rotated lowest Z about pivot."""
    origin, extent=bounds
    p,r=math.radians(pitch),math.radians(roll)
    radius=0.; low=float('inf')
    for sx in (-1,1):
        for sy in (-1,1):
            for sz in (-1,1):
                x=(origin[0]+sx*extent[0])*scale[0]
                y=(origin[1]+sy*extent[1])*scale[1]
                z=(origin[2]+sz*extent[2])*scale[2]
                # Unreal pitch/roll signs do not affect the conservative maximum.
                yy=y*math.cos(r)-z*math.sin(r); zz=y*math.sin(r)+z*math.cos(r)
                xx=x*math.cos(p)+zz*math.sin(p); zz=-x*math.sin(p)+zz*math.cos(p)
                radius=max(radius,math.hypot(xx,yy)); low=min(low,zz)
    # Enclose both signs: UE rotator convention differs from right-handed Euler.
    ex=(abs(origin[0])+extent[0])*abs(scale[0]); ey=(abs(origin[1])+extent[1])*abs(scale[1]); ez=(abs(origin[2])+extent[2])*abs(scale[2])
    radius=max(radius,math.hypot(ex+ez*abs(math.sin(p))+ey*abs(math.sin(p)*math.sin(r)),ey+ez*abs(math.sin(r))))
    return radius,low
