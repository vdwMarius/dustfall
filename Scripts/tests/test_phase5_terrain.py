"""Focused offline checks; no Unreal import, launch, build or asset writes.

Run: <UE Python> -m unittest discover -s Scripts/tests -p test_phase5_terrain.py
Native generator tests are Dustfall.Core.Terrain.Switchback (Lead runs after build).
"""
import copy
import importlib.util
import json
import math
import struct
import array
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('terrain_builder', ROOT/'Scripts/build_phase5_terrain.py')
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)
DATA = json.loads((ROOT/'Scripts/Data/terrain_features_v2.json').read_text())
LAYOUT = importlib.util.spec_from_file_location('terrain_layout', ROOT/'Scripts/phase2_layout.py')
LAYOUT_MODULE = importlib.util.module_from_spec(LAYOUT)
LAYOUT.loader.exec_module(LAYOUT_MODULE)
ROUTES = LAYOUT_MODULE.route_polylines((0, 40000))


def project(p, line):
    best, arc = None, 0
    for a, b in zip(line, line[1:]):
        run = math.dist(a, b)
        t = max(0, min(1, sum((p[k]-a[k])*(b[k]-a[k]) for k in range(2))/run**2))
        q = [a[k]+t*(b[k]-a[k]) for k in range(2)]
        item = (math.dist(p,q), arc+t*run, [(b[k]-a[k])/run for k in range(2)])
        if best is None or item[0] < best[0]: best = item
        arc += run
    return best


def tread_project(p, line):
    """Independent scalar reference for the native continuous-normal mapping."""
    def unit(v):
        length=math.hypot(*v)
        return [x/length for x in v]
    def dot(a,b): return sum(x*y for x,y in zip(a,b))
    segments=[unit([b[k]-a[k] for k in (0,1)]) for a,b in zip(line,line[1:])]
    tangents=[segments[0]]+[unit([a[k]+b[k] for k in (0,1)]) for a,b in zip(segments,segments[1:])]+[segments[-1]]
    best=None;arc=0
    for i,(a,b) in enumerate(zip(line,line[1:])):
        d=[b[k]-a[k] for k in (0,1)];r=[p[k]-a[k] for k in (0,1)];run=math.dist(a,b)
        ta=tangents[i];dt=[tangents[i+1][k]-ta[k] for k in (0,1)]
        c0=dot(r,ta);c1=dot(r,dt)-dot(d,ta);c2=-dot(d,dt)
        roots=[]
        if abs(c2)<1e-10:
            if abs(c1)>1e-10: roots=[-c0/c1]
        elif c1*c1-4*c2*c0>=0:
            q=-.5*(c1+math.copysign(math.sqrt(c1*c1-4*c2*c0),c1))
            roots=[q/c2,c0/q] if abs(q)>1e-10 else [-c1/(2*c2)]
        roots=[max(0,min(1,t)) for t in roots if -1e-8<=t<=1+1e-8]
        if i==0 and c0<0: roots.append(c0/run)
        beyond=dot([p[k]-b[k] for k in (0,1)],tangents[i+1])
        if i==len(line)-2 and beyond>0: roots.append(1+beyond/run)
        for t in roots:
            point=[a[k]+t*d[k] for k in (0,1)]
            tangent=unit([ta[k]+max(0,min(1,t))*dt[k] for k in (0,1)])
            candidate=(math.dist(p,point),arc+t*run,tangent)
            if best is None or candidate[0]<best[0]: best=candidate
        arc+=run
    return best if best is not None else project(p,line)


def isolated_tread_cross(line, samples, width, projector, profile=None):
    """Rasterise only the four supporting vertices of each tread probe.

    This intentionally omits terrain relief, carving order and the full generator;
    it isolates projection and 1m raster error in a constant-grade descent.
    """
    total=sum(math.dist(a,b) for a,b in zip(line,line[1:]))
    grade=(samples[-1][2]-samples[0][2])/total
    cache={}
    def height(p):
        ix=math.floor((p[0]+100800)/100);iy=math.floor((p[1]+100800)/100)
        u=(p[0]+100800)/100-ix;v=(p[1]+100800)/100-iy
        def vertex(x,y):
            if (x,y) not in cache:
                arc=projector([-100800+100*x,-100800+100*y],line)[1]
                z=profile(arc) if profile is not None else samples[0][2]+grade*arc
                cache[x,y]=round(z/.78125)*.78125
            return cache[x,y]
        return sum((u if dx else 1-u)*(v if dy else 1-v)*vertex(ix+dx,iy+dy) for dx in (0,1) for dy in (0,1))
    worst=(0,None)
    for point in samples:
        p=point[:2];_,arc,t=projector(p,line);normal=[-t[1],t[0]]
        count=math.ceil(width/100)
        previous=height([p[k]-normal[k]*width/2 for k in (0,1)])
        for j in range(1,count+1):
            z=height([p[k]+normal[k]*(-width/2+width*j/count) for k in (0,1)])
            slope=abs(z-previous)/(width/count);previous=z
            if slope>worst[0]: worst=(slope,p)
    return worst


def real_data_diagnostics():
    """Sample input anchors/guards/bends only, never port the terrain generator.

    XY mapping and Z quantum come from the Lead's measured report. Absolute
    landscape Z was not recorded; baseline differences cancel that translation.
    """
    main = pathlib.Path('G:/ue/dustfall')
    report = json.loads((main/'Docs/Phase5_TerrainResults.json').read_text())['validation']
    resolved = json.loads((main/'Saved/Codex/terrain_features_v2_resolved.json').read_text())
    raw = (main/'Scripts/Data/Phase3LandscapeBaseline.bin').read_bytes()
    x1,y1,x2,y2 = struct.unpack('<4i',raw[:16])
    w,h = x2-x1+1,y2-y1+1
    heights = array.array('H'); heights.frombytes(raw[16:])
    if sys.byteorder != 'little': heights.byteswap()
    bounds = report['mask_world_bounds_cm']; quantum = report['height_quantisation_cm']
    def baseline(p):
        x = max(0,min(w-1,(p[0]-bounds[0])/(bounds[2]-bounds[0])*(w-1)))
        y = max(0,min(h-1,(p[1]-bounds[1])/(bounds[3]-bounds[1])*(h-1)))
        ix,iy = min(int(x),w-2),min(int(y),h-2)
        u,v = x-ix,y-iy
        return ((1-v)*((1-u)*heights[iy*w+ix]+u*heights[iy*w+ix+1])+
                v*((1-u)*heights[(iy+1)*w+ix]+u*heights[(iy+1)*w+ix+1])-32768)*quantum
    def core(p):
        return (any(math.dist(p,d[:2]) <= d[2] for d in resolved['resolved']['discs_cm']) or
                any(project(p,r['line_cm'])[0] <= resolved['protection']['route_inner_cm']
                    for r in resolved['resolved']['routes']))
    diagnostics = {}
    for f in report['features']:
        if 'polyline_cm' not in f: continue
        line = [p[:2] for p in f['polyline_cm']]
        worst = (0,None)
        for a,b in zip(line,line[1:]):
            if core(a) and core(b):
                grade = abs(baseline(a)-baseline(b))/math.dist(a,b)
                if grade > worst[0]: worst = (grade,a)
        cross = (0,None)
        source = next(s for s in resolved['features'] if s['id']==f['id'])
        for p in line:
            _,arc,t = project(p,source['line_cm'])
            normal = [-t[1],t[0]]; half=source['width_cm']/2
            sides = [[p[k]+sign*normal[k]*half for k in range(2)] for sign in (-1,1)]
            if all(core(q) for q in sides):
                slope=abs(baseline(sides[0])-baseline(sides[1]))/(2*half)
                if slope > cross[0]: cross=(slope,p)
        diagnostics[f['id']] = dict(guard_grade=worst,guard_cross=cross)
    return diagnostics, baseline, resolved, report


def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)


def anchor_relief(p, features):
    """Analytic input relief at anchors only; no heightfield/path generator."""
    def gaussian(a):
        x,y=p[0]-a[0],p[1]-a[1];c,t=math.cos(a[5]),math.sin(a[5])
        return math.exp(-2*(((x*c+y*t)/a[2])**2+((-x*t+y*c)/a[3])**2))
    def wall(t, knots):
        t=max(0,min(1,t))
        for a,b in zip(knots,knots[1:]):
            if t<=b[0]: return a[1]+(b[1]-a[1])*(t-a[0])/(b[0]-a[0])
        return knots[-1][1]
    total=0
    for f in features:
        k=f['type'];a=f.get('parameters',[])
        if f['stage']=='path': continue
        if k in ('gaussian_hill','spire_base'): value=a[4]*gaussian(a)
        elif k=='ridged_noise':
            if len(a)==7: value=a[0]*max(0,math.sin(p[0]*a[1]+math.sin(p[1]*a[2])))**a[3]*(a[4]+a[5]*abs(math.sin(p[1]*a[6])))
            else: value=a[0]*gaussian([a[1],a[2],a[3],a[4],1,a[5]])*abs(math.sin(p[0]*a[6]+p[1]*a[7]))
        elif k=='ravine':
            y=a[0]+a[1]*math.sin((p[0]-a[2])*a[3])
            value=-a[9]*math.exp(-((p[0]-a[4])/a[5])**a[6])*math.exp(-((p[1]-y)/(a[7] if p[1]>y else a[8]))**2*a[10])
        elif k=='crater':
            r=math.dist(p,a[:2]);value=a[2]*math.exp(-((r-a[3])/a[4])**2)-a[5]*math.exp(-(r/a[6])**2)
        elif k=='pit': value=-a[2]*(1-smooth(a[3],a[4],math.dist(p,a[:2])))+a[5]*gaussian([a[6],a[7],a[8],a[9],1,a[10]])
        else:
            distance,arc,tangent=project(p,f['line_cm']);run=sum(math.dist(a,b) for a,b in zip(f['line_cm'],f['line_cm'][1:]))
            # Recover the closest point for the signed wall distance.
            left=arc
            for start,end in zip(f['line_cm'],f['line_cm'][1:]):
                length=math.dist(start,end)
                if left<=length+1e-7:
                    q=[start[j]+min(1,left/length)*(end[j]-start[j]) for j in (0,1)];break
                left-=length
            signed=tangent[0]*(p[1]-q[1])-tangent[1]*(p[0]-q[0])
            blend=f['end_blend_cm']
            if k=='escarpment': blend+=(f['plateau_blend_cm']-blend)*smooth(0,f['face_width_cm'],signed*f['high_side'])
            end=smooth(0,blend,arc)*smooth(0,blend,run-arc)
            if k=='canyon':
                t=arc/run;rim=sum(f['rim_width_cm'][j]*([1-t,t][j]) for j in (0,1))/2;floor=sum(f['floor_width_cm'][j]*([1-t,t][j]) for j in (0,1))/2
                value=-f['depth_cm']*(1-wall((distance-floor)/(rim-floor),f['north_wall'] if signed>=0 else f['south_wall']))*end
            else:
                d=signed*f['high_side'];rise=1 if d>f['face_width_cm'] else wall((d+f['talus_width_cm'])/(f['talus_width_cm']+f['face_width_cm']),f['wall'])
                value=(f['drop_cm']*rise+f['vertical_offset_cm'])*end
        total+=value
    return total


def switchback(top,bottom,tangent,required,corridor,radius,spacing,step=100):
    """Small geometric reference for native hairpins, no terrain carving."""
    along=[x/math.hypot(*tangent) for x in tangent];across=[-along[1],along[0]]
    dot=lambda a,b:sum(x*y for x,y in zip(a,b))
    delta=[bottom[k]-top[k] for k in (0,1)]
    if dot(delta,across)<0: across=[-x for x in across]
    span,offset=dot(delta,across),dot(delta,along)
    for turns in range(1,int(span/max(2*radius,spacing))+1):
        r=span/(2*turns);capacity=(corridor-spacing)/2-r-abs(offset)/2
        leg=max(abs(offset)/(2*turns)+step,(required*1.002-turns*math.pi*r)/(2*turns))
        if not 0<leg<=capacity: continue
        line=[list(top)]
        for i in range(turns):
            sign=1 if i%2==0 else -1;centre=offset*(i+.5)/turns;count=max(32,math.ceil(math.pi*r/step))
            for j in range(count+1):
                angle=math.pi*j/count;x=2*r*i+r*(1-math.cos(angle));y=centre+sign*(leg+r*math.sin(angle))
                line.append([top[k]+across[k]*x+along[k]*y for k in (0,1)])
        line.append(list(bottom))
        if sum(math.dist(a,b) for a,b in zip(line,line[1:]))>=required:return line
    raise ValueError('No safe hairpin fits corridor')


def at_arc(line, arc):
    for a,b in zip(line,line[1:]):
        length=math.dist(a,b)
        if arc<=length: return [a[k]+max(0,min(1,arc/length))*(b[k]-a[k]) for k in (0,1)]
        arc-=length
    return line[-1][:]


def real_path_geometry():
    _,baseline,_,report=real_data_diagnostics()
    data=BUILDER.resolve_features(DATA,(0,40000),ROUTES)
    # The report records 1m XY spacing and .78125cm Z quantum. Test only
    # relative heights: the unrecorded absolute landscape Z cancels in drops.
    margin=math.sqrt(2)*100
    result={}
    for f in data['features']:
        if f['stage']!='path' or 'route_reference' in f:continue
        line=f['line_cm'];top,bottom=line[0],line[-1]
        drop=baseline(top)+anchor_relief(top,data['features'])-baseline(bottom)-anchor_relief(bottom,data['features'])
        run=sum(math.dist(a,b) for a,b in zip(line,line[1:]))
        support=f['width_cm']/2+f['shoulder_cm']+2*margin
        required=abs(drop)/(f['max_grade']*data['sampling']['grade_reserve'])*1.01+2*support+2*f['endpoint_blend_cm']
        generated=False
        if f['type']=='descent' and run<required:
            parent=next(p for p in data['features'] if p['id']==f['parent'])
            tangent=project([(top[k]+bottom[k])/2 for k in (0,1)],parent['line_cm'])[2]
            tangent=[x*f.get('traverse_direction',1) for x in tangent]
            line=switchback(top,bottom,tangent,required,f['corridor_width_cm'],f['minimum_turn_radius_cm'],
                            f['width_cm']+2*(f['shoulder_cm']+margin))
            run=sum(math.dist(a,b) for a,b in zip(line,line[1:]));generated=True
        count=math.ceil(run/data['sampling']['path_step_cm'])
        samples=[at_arc(line,run*j/count)+[-drop*j/count] for j in range(count+1)]
        result[f['id']]=dict(feature=f,line=line,run=run,drop=drop,generated=generated,samples=samples)
    return data,result,report


def pinned_profile(points, pins, limit, transition, sink_depth=0):
    """Reference integrated grade envelope, sampled like the native profile."""
    arcs=[0]
    for a,b in zip(points,points[1:]):arcs.append(arcs[-1]+math.dist(a,b))
    z=[0]*len(points)
    for first,last in zip(sorted(pins),sorted(pins)[1:]):
        run=arcs[last]-arcs[first];top=pins[first];drop=pins[last]-top
        if abs(drop)>limit*run+1e-7:raise ValueError('Incompatible pins')
        ramp=min(transition,run/2,max(0,run-abs(drop)/limit)*.9) if last>first+1 else 0
        def area(x):
            if ramp<1e-8:return x
            edge=lambda t:ramp*(t**3-.5*t**4)
            if x<ramp:return edge(x/ramp)
            if x>run-ramp:return run-ramp-edge((run-x)/ramp)
            return x-ramp/2
        sink=min(max(0,sink_depth),max(0,limit-abs(drop)/(run-ramp))*ramp/1.5)
        for j in range(first,last+1):
            arc=arcs[j]-arcs[first]
            cut=sink*smooth(0,ramp,arc)*smooth(0,ramp,run-arc) if ramp>1e-8 else 0
            z[j]=top+drop*area(arc)/(run-ramp)-cut
    def sample(arc):
        # Native samples have uniform design arc spacing. Chord length only
        # enters the grade envelope above, as in LimitPinnedGrade.
        u=arc/arcs[-1]*(len(z)-1);j=max(0,min(len(z)-2,math.floor(u)))
        return z[j]+(z[j+1]-z[j])*(u-j)
    return z,sample


def real_raster_replica(bound_extensions=True):
    """Sparse native carving replica using real baseline and unchanged report geometry.

    Recreates raster-sampled anchors and generated hairpins; reuses exact reported
    guard/junction intervals. Only evaluates vertices supporting traversal probes.
    """
    from functools import lru_cache
    _, baseline, data, report = real_data_diagnostics()
    features = sorted(data['features'], key=lambda f: f['id'])
    sampling, protection = data['sampling'], data['protection']
    step = sampling['path_step_cm']
    sx, sy, sz = report['landscape_scale']
    ox, oy, oz = report['landscape_location_cm']
    quantum = sz/128
    margin = math.hypot(sx, sy)

    def guard(p):
        return min([1]+[smooth(d[2], d[2]+protection['disc_blend_cm'], math.dist(p,d[:2]))
                        for d in data['resolved']['discs_cm']]+
                       [smooth(protection['route_inner_cm'],protection['route_outer_cm'],project(p,r['line_cm'])[0])
                        for r in data['resolved']['routes']])

    @lru_cache(None)
    def relief_vertex(x,y):
        p=(ox+x*sx,oy+y*sy)
        return baseline(p)+oz+anchor_relief(p,features)*guard(p)

    def interpolate(p, vertex):
        x,y=(p[0]-ox)/sx,(p[1]-oy)/sy
        ix,iy=math.floor(x),math.floor(y);u,v=x-ix,y-iy
        return sum((u if dx else 1-u)*(v if dy else 1-v)*vertex(ix+dx,iy+dy)
                   for dx in (0,1) for dy in (0,1))

    relief = lambda p: interpolate(p, relief_vertex)
    paths=[]
    for measured in report['features']:
        if 'polyline_cm' not in measured: continue
        f=copy.deepcopy(next(f for f in features if f['id']==measured['id']))
        line=f['line_cm'];run=sum(math.dist(a,b) for a,b in zip(line,line[1:]))
        drop=relief(tuple(line[0]))-relief(tuple(line[-1]))
        support=f['width_cm']/2+f['shoulder_cm']+2*margin
        required=abs(drop)/(f['max_grade']*sampling['grade_reserve'])*1.01+2*support+2*f['endpoint_blend_cm']
        if f['type']=='descent' and run<required:
            parent=next(p for p in features if p['id']==f['parent'])
            tangent=project([(line[0][k]+line[-1][k])/2 for k in (0,1)],parent['line_cm'])[2]
            tangent=[v*f.get('traverse_direction',1) for v in tangent]
            line=switchback(line[0],line[-1],tangent,required,f['corridor_width_cm'],f['minimum_turn_radius_cm'],
                            f['width_cm']+2*(f['shoulder_cm']+margin),step)
            run=sum(math.dist(a,b) for a,b in zip(line,line[1:]))
        count=max(1,math.ceil(run/step));points=[at_arc(line,run*j/count) for j in range(count+1)]
        pins={j:relief(tuple(p)) for j,p in enumerate(points) if j in (0,count) or guard(p)==0}
        for crossing in measured['guard_core_crossings']:
            low,high=crossing['arc_range_cm']
            for j,p in enumerate(points):
                if low-step<=run*j/count<=high+step: pins[j]=baseline(p)+oz
        f.update(line=line,run=run,drop=drop,points=points,pins=pins)
        padding=f['width_cm']/2+f['shoulder_cm']+margin
        f['bounds']=[min(p[k] for p in line)-padding for k in (0,1)]+[max(p[k] for p in line)+padding for k in (0,1)]
        paths.append(f)
    paths.sort(key=lambda f:f['id'])
    for junction in report['path_overlaps']:
        if junction['resolution']!='common_level_profile_pins_and_simultaneous_weighted_blend':continue
        height=relief(tuple(junction['xy_cm']))
        for name,field in zip(junction['features'],('first_arc_range_cm','second_arc_range_cm')):
            f=next(f for f in paths if f['id']==name);low,high=junction[field]
            pad=f['width_cm']/2+f['shoulder_cm']+2*margin
            for j,p in enumerate(f['points']):
                if low-pad<=f['run']*j/(len(f['points'])-1)<=high+pad and guard(p)==1:f['pins'][j]=height
    for f in paths:
        if 'route_reference' in f:
            f['target']=[relief(tuple(p)) for p in f['points']]
        else:
            limit=f['max_grade']*sampling['grade_reserve']
            if f['type']!='descent':limit=min(f['hard_max_grade']*sampling['grade_reserve'],max(limit,abs(f['drop'])/f['run']*1.001))
            f['target'],_=pinned_profile(f['points'],f['pins'],limit,f['endpoint_blend_cm'],f['sink_cm'])

    @lru_cache(None)
    def output_vertex(x,y):
        p=(ox+x*sx,oy+y*sy);z=relief_vertex(x,y)
        tread=[];shoulder=[]
        for f in paths:
            if 'route_reference' in f:continue
            b=f['bounds']
            if not (b[0]<=p[0]<=b[2] and b[1]<=p[1]<=b[3]):continue
            distance,arc,_=tread_project(p,f['line'])
            half=f['width_cm']/2
            if distance>half+f['shoulder_cm']+margin:continue
            if bound_extensions and not -(half+f['shoulder_cm']+margin)<=arc<=f['run']+half+f['shoulder_cm']+margin:continue
            u=arc/f['run']*(len(f['target'])-1);j=max(0,min(len(f['target'])-2,math.floor(u)))
            target=f['target'][j]+(f['target'][j+1]-f['target'][j])*(u-j)
            weight=(1-smooth(half+margin,half+margin+f['shoulder_cm'],distance))*guard(p)
            (tread if distance<=half+margin else shoulder).append((weight,target))
        contributions=tread if sum(w for w,_ in tread)>0 else shoulder
        weight=sum(w for w,_ in contributions)
        if weight>0:z+=(sum(w*t for w,t in contributions)/weight-z)*max(w for w,_ in contributions)
        return math.floor((z-oz)/quantum+32768+.5)*quantum-32768*quantum+oz

    height=lambda p:interpolate(p,output_vertex)
    result={}
    for f in paths:
        grade=cross=error=0;previous=None
        for j,p in enumerate(f['points']):
            z=height(p);error=max(error,abs(z-f['target'][j]))
            if previous is not None:grade=max(grade,abs(z-previous)/math.dist(p,f['points'][j-1]))
            previous=z
            t=tread_project(p,f['line'])[2];normal=[-t[1],t[0]];width=f['width_cm'];across=math.ceil(width/step)
            prev=height([p[k]-normal[k]*width/2 for k in (0,1)])
            for a in range(1,across+1):
                next_z=height([p[k]+normal[k]*(-width/2+width*a/across) for k in (0,1)])
                cross=max(cross,abs(next_z-prev)/(width/across));prev=next_z
        ceiling=f['max_grade'] if f['type']=='descent' else f['hard_max_grade']
        valid=('route_reference' in f or (grade<=ceiling and cross<=f['max_cross_slope'] and
               error<=quantum+sampling['profile_tolerance_cm'] and
               (f['type']!='descent' or height(f['points'][0])>height(f['points'][-1]))))
        result[f['id']]=dict(grade=grade,cross_slope=cross,profile_error_cm=error,valid=valid)
    return result

class RealRasterReplicaTests(unittest.TestCase):
    def test_real_report_reproduction_and_all_eleven_traversals(self):
        fixture=pathlib.Path('G:/ue/dustfall/Docs/Phase5_TerrainResults.json')
        if not fixture.exists():
            self.skipTest('Lead real-data fixtures unavailable')
        _,_,resolved,report=real_data_diagnostics()
        routes={r['id']:r['line_cm'] for r in resolved['resolved']['routes']}
        current=BUILDER.resolve_features(DATA,tuple(routes['Home_Cruiser'][-1]),routes)
        self.assertEqual(json.loads(json.dumps(current['features'])),resolved['features'])
        before=real_raster_replica(False)
        after=real_raster_replica(True)
        self.assertEqual(len(after),11)
        # The Lead's report can be from either side of the round-4 fix.
        # These legacy replicas use layer 0; they cannot validate merged terrain.
        reference=after if all(f.get('valid',True) for f in report['features']) else before
        for f in report['features']:
            if f['id'] not in before:continue
            if report.get('validation_surface'):continue
            metrics=reference[f['id']]
            for replica,native in [('grade','maximum_grade'),('cross_slope','maximum_cross_slope'),
                                   ('profile_error_cm','maximum_profile_error_cm')]:
                # Allow sub-micron differences in native versus Python arc accumulation.
                self.assertAlmostEqual(metrics[replica],f[native],delta=1e-4,msg=f['id']+': '+replica)
            self.assertEqual(metrics['valid'],f['valid'])
        for key,metrics in after.items():
            self.assertTrue(metrics['valid'],key+': '+str(metrics))
            if key!='scar_trail':self.assertEqual(before[key],metrics,key)
        print('\nRound4 real baseline replica (grade / cross / error cm):',flush=True)
        for key,m in after.items():
            print(f"{key}: {m['grade']:.9f} / {m['cross_slope']:.9f} / {m['profile_error_cm']:.9f} valid={m['valid']}",flush=True)

class RealInputGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not pathlib.Path('G:/ue/dustfall/Docs/Phase5_TerrainResults.json').exists():
            raise unittest.SkipTest('Lead real-data fixtures unavailable')
        cls.data,cls.geometry,cls.report=real_path_geometry()

    def test_escape_anchors_reach_deep_centreline_with_positive_drop(self):
        canyon=next(f for f in self.data['features'] if f['id']=='the_scar')
        run=sum(math.dist(a,b) for a,b in zip(canyon['line_cm'],canyon['line_cm'][1:]))
        for key in ('scar_west_escape','scar_east_escape'):
            g=self.geometry[key];top,bottom=g['line'][0],g['line'][-1]
            distance,arc,_=project(bottom,canyon['line_cm'])
            self.assertLess(distance,1)
            depth=canyon['depth_cm']*smooth(0,canyon['end_blend_cm'],arc)*smooth(0,canyon['end_blend_cm'],run-arc)
            self.assertGreater(depth,4400)
            self.assertGreater(g['drop'],2000)
            self.assertGreater(project(top,canyon['line_cm'])[0],max(canyon['rim_width_cm'])/2)

    def test_new_trails_clear_guard_cores_and_fade(self):
        protection=self.data['protection'];margin=math.sqrt(2)*100
        for key in ('scar_trail','shelf_trail'):
            g=self.geometry[key];width=g['feature']['width_cm']/2+margin
            for p in g['samples']:
                _,_,t=tread_project(p[:2],g['line']);normal=[-t[1],t[0]]
                for sign in (-1,0,1):
                    q=[p[k]+sign*width*normal[k] for k in (0,1)]
                    for disc in self.data['resolved']['discs_cm']:
                        self.assertGreater(math.dist(q,disc[:2]),disc[2]+protection['disc_blend_cm'])
                    for route in self.data['resolved']['routes']:
                        self.assertGreater(project(q,route['line_cm'])[0],protection['route_outer_cm'])

    def test_generated_bends_fit_tread_and_footprint_stays_on_landscape(self):
        bounds=self.report['mask_world_bounds_cm'];margin=math.sqrt(2)*100
        for key,g in self.geometry.items():
            f=g['feature']
            if f['type']!='descent':continue
            self.assertLess(abs(g['drop'])/g['run'],f['max_grade']*self.data['sampling']['grade_reserve'])
            footprint=f['width_cm']/2+f['shoulder_cm']+margin
            for p in g['line']:
                self.assertTrue(bounds[0]+footprint<p[0]<bounds[2]-footprint,key)
                self.assertTrue(bounds[1]+footprint<p[1]<bounds[3]-footprint,key)
            if not g['generated']:continue
            for a,b,c in zip(g['line'],g['line'][1:],g['line'][2:]):
                u=[b[k]-a[k] for k in (0,1)];v=[c[k]-b[k] for k in (0,1)];cross=abs(u[0]*v[1]-u[1]*v[0])
                if cross>1e-6:
                    radius=math.dist(a,b)*math.dist(b,c)*math.dist(a,c)/(2*cross)
                    self.assertGreaterEqual(radius+1e-5,f['minimum_turn_radius_cm'])
                    self.assertGreater(radius,footprint)

    def test_shared_junctions_and_smoothed_profiles_remain_traversable(self):
        _,baseline,_,_=real_data_diagnostics()
        profiles={}
        for key,g in self.geometry.items():
            top=g['line'][0]
            height=baseline(top)+anchor_relief(top,self.data['features'])
            profiles[key]={0:height,len(g['samples'])-1:height-g['drop']}
        # Real data has exactly two shared endpoints. Use geometric distances to
        # find their full tread overlap; do not test a second terrain generator.
        for left_key,right_key in [('scar_switchback','scar_trail'),('shelf_notch','shelf_trail')]:
            left,right=self.geometry[left_key],self.geometry[right_key]
            radius=(left['feature']['width_cm']+right['feature']['width_cm'])/2+2*math.sqrt(20000)
            hits=[(j,project(p[:2],right['line'])) for j,p in enumerate(left['samples']) if project(p[:2],right['line'])[0]<=radius]
            self.assertTrue(hits)
            j,q=min(hits,key=lambda h:h[1][0]);centre=left['samples'][j][:2]
            height=baseline(centre)+anchor_relief(centre,self.data['features'])
            for key,start,end in [(left_key,left['run']*hits[0][0]/(len(left['samples'])-1),left['run']*hits[-1][0]/(len(left['samples'])-1)),
                                  (right_key,min(h[1][1] for h in hits),max(h[1][1] for h in hits))]:
                g=self.geometry[key];padding=g['feature']['width_cm']/2+g['feature']['shoulder_cm']+2*math.sqrt(20000)
                for j in range(len(g['samples'])):
                    arc=g['run']*j/(len(g['samples'])-1)
                    if start-padding<=arc<=end+padding:profiles[key][j]=height
        for key,g in self.geometry.items():
            f=g['feature'];points=[p[:2] for p in g['samples']]
            z,profile=pinned_profile(points,profiles[key],f['max_grade']*self.data['sampling']['grade_reserve'],f['endpoint_blend_cm'],f['sink_cm'])
            maximum,xy=isolated_tread_cross(g['line'],g['samples'],f['width_cm'],tread_project,profile)
            self.assertLessEqual(maximum,f['max_cross_slope'],(key,maximum,xy))
            for a,b,za,zb in zip(points,points[1:],z,z[1:]):self.assertLessEqual(abs(za-zb)/math.dist(a,b),f['max_grade'])

    def test_new_normal_mapping_levels_real_descent_treads_after_raster(self):
        for key,g in self.geometry.items():
            if g['feature']['type']!='descent':continue
            maximum,xy=isolated_tread_cross(g['line'],g['samples'],g['feature']['width_cm'],tread_project)
            self.assertLessEqual(maximum,g['feature']['max_cross_slope'],(key,maximum,xy))


class SchemaTests(unittest.TestCase):
    def test_anchor_moves_stay_within_sixty_metres(self):
        features={f['id']:f for f in DATA['features']}
        old={'scar_trail':[[-2500,2500]],'shelf_trail':[[13000,8500]],
             'scar_west_escape':[[-85000,-18000],[-85000,-31300]],
             'scar_east_escape':[[29000,-65000],[29000,-73800]]}
        for key,anchors in old.items():
            new=[features[key]['line_cm'][0]] if len(anchors)==1 else [features[key]['line_cm'][0],features[key]['line_cm'][-1]]
            for a,b in zip(anchors,new):self.assertLessEqual(math.dist(a,b),6000,key)

    def test_lead_grade_edits_preserved(self):
        features = {f['id']: f for f in DATA['features']}
        self.assertEqual([features[k]['max_grade'] for k in ('wreck_ruin','scar_trail','shelf_trail')], [.11,.18,.18])

    def test_resolve_is_deterministic_and_preserves_routes(self):
        original = copy.deepcopy(DATA)
        a = BUILDER.resolve_features(DATA, (0,40000), ROUTES)
        b = BUILDER.resolve_features(DATA, (0,40000), ROUTES)
        self.assertEqual(a,b)
        self.assertEqual(DATA,original)
        for f in a['features']:
            if 'route_reference' in f:
                self.assertEqual(f['line_cm'], ROUTES[f['route_reference']])
            if f['type'] == 'descent':
                self.assertGreater(f['corridor_width_cm'],0)
                self.assertGreaterEqual(f['minimum_turn_radius_cm'],f['width_cm']/2+f['shoulder_cm'])

    def test_anchor_only_and_wall_side_descents(self):
        for parent, top, side in [('the_shelf',[53000,50500],1),('the_scar',[-35000,-27000],1)]:
            data = copy.deepcopy(DATA)
            f = next(f for f in data['features'] if f['id']=='shelf_notch')
            del f['line_cm']
            f.update(top_anchor_cm=top, parent=parent, side=side)
            a = BUILDER.resolve_features(data,(0,40000),ROUTES)
            line = next(f['line_cm'] for f in a['features'] if f['id']=='shelf_notch')
            self.assertEqual(line[0],top)
            self.assertNotEqual(line[0],line[-1])

    def test_feature_order_does_not_change_resolved_geometry(self):
        original=BUILDER.resolve_features(DATA,(0,40000),ROUTES)
        reordered=copy.deepcopy(DATA);reordered['features'].reverse()
        resolved=BUILDER.resolve_features(reordered,(0,40000),ROUTES)
        self.assertEqual({f['id']:f for f in original['features']},{f['id']:f for f in resolved['features']})
        # Derived anchors must resolve against the same rounded parent even when
        # that parent appears after its child in the input array.
        anchor=copy.deepcopy(DATA)
        f=next(f for f in anchor['features'] if f['id']=='shelf_notch')
        del f['line_cm'];f.update(top_anchor_cm=[53000,50500],side=1)
        a=BUILDER.resolve_features(anchor,(0,40000),ROUTES)
        anchor['features'].reverse();b=BUILDER.resolve_features(anchor,(0,40000),ROUTES)
        self.assertEqual({f['id']:f for f in a['features']},{f['id']:f for f in b['features']})

    def test_capsule_and_turn_clearance_rejected(self):
        for key, value in [('minimum_tread_width_cm',67),('minimum_turn_radius_cm',100)]:
            data=copy.deepcopy(DATA)
            next(f for f in data['features'] if f['type']=='descent')[key]=value
            with self.assertRaises(ValueError): BUILDER.resolve_features(data,(0,40000),ROUTES)


class DryRunOrderingTests(unittest.TestCase):
    def exercise(self, passes, validate_only, merged=True):
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder)
            (root/'Scripts/Data').mkdir(parents=True)
            (root/'Saved/Codex').mkdir(parents=True)
            (root/'Scripts/Data/terrain_features_v2.json').write_text(json.dumps(DATA))
            (root/'Saved/Codex/landmark_build_report.json').write_text(json.dumps({'Cruiser':{'relative_x_cm':0,'relative_y_cm':40000}}))
            events=[]
            class Landscape:
                def get_path_name(self): return '/Game/World/Maps/L_Dustfall_Foundation.Landscape'
            def validate(actor, baseline, features, report):
                events.append('validate')
                payload=dict(status='validation_passed' if passes else 'failed',
                             validation_surface='final merged heightfield; inverse additive composition written to layer 0' if merged else None,
                             features=[dict(id='wreck_ruin',required_grade=.11),dict(id='shelf_notch',generated=True)],
                             problems=[] if passes else [dict(id='a',message='one'),dict(id='b',message='two')],
                             paths=[dict(id='shelf_notch',polyline_cm=[[0,0,6000],[10000,0,0]])],clipped_vertices=0)
                pathlib.Path(report).write_text(json.dumps(payload))
                return 'OK: validated' if passes else 'ERROR: all failures'
            fake=types.SimpleNamespace(
                Paths=types.SimpleNamespace(project_dir=lambda:str(root)),
                EditorActorSubsystem=object(), Landscape=Landscape,
                get_editor_subsystem=lambda _:types.SimpleNamespace(get_all_level_actors=lambda:[Landscape()]),
                EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_map_packages=lambda:[],get_dirty_content_packages=lambda:[]),
                EditorLevelLibrary=types.SimpleNamespace(get_game_world=lambda:None),
                DustfallTerrainLibrary=types.SimpleNamespace(validate_terrain_features=validate),
                log_error=lambda _:None)
            def run_path(path):
                if pathlib.Path(path).name=='phase2_layout.py':
                    return dict(route_polylines=lambda cruiser:ROUTES)
                events.append('mutation:'+pathlib.Path(path).name)
                raise AssertionError('Cell loading or authoring must not precede successful validation/apply mode')
            with patch.dict(sys.modules,unreal=fake), patch.object(BUILDER,'VALIDATE_ONLY',validate_only), patch.object(BUILDER.runpy,'run_path',side_effect=run_path):
                BUILDER.main()
            result=json.loads((root/'Docs/Phase5_TerrainResults.json').read_text())
            self.assertEqual(events,['validate'])
            self.assertTrue(result['validation_editor_stayed_clean'])
            self.assertEqual(len(result['native']['features']),2)
            return result

    def test_failed_apply_attempt_leaves_editor_clean_and_reports_all_errors(self):
        result=self.exercise(False,False)
        self.assertEqual(result['status'],'validation_failed')
        self.assertEqual(len(result['validation']['problems']),2)

    def test_failed_dry_run_reports_all_errors(self):
        self.assertEqual(self.exercise(False,True)['status'],'validation_failed')

    def test_passing_validate_only_never_loads_or_authors(self):
        self.assertEqual(self.exercise(True,True)['status'],'validation_passed')

    def test_old_native_build_cannot_apply_even_when_legacy_validation_passes(self):
        with self.assertRaisesRegex(RuntimeError,'needs Lead rebuild'):
            self.exercise(True,False,merged=False)


class CollisionAcceptanceTests(unittest.TestCase):
    def test_timeout_evidence_keeps_missing_hits_and_worst_proxy(self):
        def trace(x,y):
            if x == 2: raise RuntimeError('missing landscape')
            return 0,'proxy_'+str(x)
        rows=BUILDER.collision_diagnostics([('route',1,0,-1240.625),('missing',2,0,0)],trace)
        self.assertIsNone(rows[0]['actual_z_cm'])
        self.assertEqual(rows[1]['proxy'],'proxy_1')
        self.assertEqual(rows[1]['xy_cm'],[1,0])
        self.assertEqual(rows[1]['expected_z_cm'],-1240.625)
        self.assertFalse(BUILDER.collision_ready(rows,15))

    def test_protection_is_stricter_than_path_tolerance(self):
        rows=BUILDER.collision_diagnostics([('home',0,0,0)],lambda x,y:(1,'proxy'))
        self.assertTrue(BUILDER.collision_ready(rows,15))
        self.assertFalse(BUILDER.collision_ready(rows,100/128))

    def test_final_surface_samples_vertices_edges_and_both_triangles(self):
        with tempfile.TemporaryDirectory() as folder:
            path=pathlib.Path(folder)/'surface.bin'
            path.write_bytes(struct.pack('<4i4H',0,0,1,1,32768,32896,33024,33280))
            sample=BUILDER.load_final_surface(dict(final_surface_file=str(path),
                landscape_location_cm=[-100,-100,100],landscape_scale=[100,100,100]))
            self.assertEqual(sample(-100,-100),100)
            self.assertEqual(sample(0,0),500)
            self.assertEqual(sample(-25,-75),250)
            self.assertEqual(sample(-75,-25),300)
            with self.assertRaises(ValueError): sample(1,0)


if __name__ == '__main__':
    unittest.main()
