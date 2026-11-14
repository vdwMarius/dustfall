"""Terrain v2 authoring, under the Lead's sole editor lock, after a full build.

Defaults to VALIDATE_ONLY=True. Apply after reviewing a passing dry run with:
runpy.run_path(..., run_name='__main__', init_globals={'VALIDATE_ONLY': False}).
Never generates PCG. Validation runs before cell loading or actor authoring.
Outputs are asynchronous: wait for Docs/Phase5_TerrainResults.json status.
Schema validation/resolution is pure Python and may be reviewed without Unreal.
"""
import copy
import hashlib
import json
import math
import pathlib
import runpy
import time
import traceback

VALIDATE_ONLY = globals().get('VALIDATE_ONLY', True)


def rounded_line(line, radius=1200.0):
    """Quadratic corner fillets, <=12m displacement; preserve both endpoints."""
    out = [list(line[0])]
    for a, b, c in zip(line, line[1:], line[2:]):
        ab, bc = math.dist(a, b), math.dist(b, c)
        r = min(radius, ab * .2, bc * .2)
        start = [b[k] + (a[k]-b[k])*r/ab for k in range(2)]
        end = [b[k] + (c[k]-b[k])*r/bc for k in range(2)]
        for j in range(5):
            t = j/4
            out.append([(1-t)**2*start[k]+2*t*(1-t)*b[k]+t*t*end[k] for k in range(2)])
    return out + [list(line[-1])]


def resolve_features(data, cruiser, routes):
    data = copy.deepcopy(data)
    if data.get('schema_version') != 2 or data.get('units') != 'cm':
        raise ValueError('Expected terrain schema v2 in centimetres')
    def finite(value):
        if isinstance(value, (float, int)) and not math.isfinite(value):
            raise ValueError('Non-finite feature value')
        if isinstance(value, dict):
            for v in value.values(): finite(v)
        if isinstance(value, list):
            for v in value: finite(v)
    finite(data)
    p, s = data['protection'], data['sampling']
    for name in ('disc_blend_cm', 'route_inner_cm', 'route_outer_cm', 'cruiser_radius_cm'):
        if p[name] <= 0: raise ValueError('Invalid protection '+name)
    if p['route_outer_cm'] <= p['route_inner_cm']: raise ValueError('Invalid route shoulders')
    for disc in p['discs_cm']:
        if len(disc) != 3 or disc[2] <= 0: raise ValueError('Invalid protection disc')
    if not 0 < s['grade_reserve'] <= 1: raise ValueError('Invalid grade reserve')
    if not 0 <= s['profile_tolerance_cm'] <= 15: raise ValueError('Invalid profile tolerance')
    if s['mask_size'] != 2048 or not 0 < s['path_step_cm'] <= 100:
        raise ValueError('Masks must be 2048; output traversal sampling <=1m')
    if not 0 < s['probe_step_cm'] <= 1000:
        raise ValueError('Invalid sampling settings')
    if not 0 < s['talus_min_degrees'] < s['talus_max_degrees'] < s['cliff_degrees'] < 90:
        raise ValueError('Invalid slope thresholds')
    counts = {'gaussian_hill': (6,), 'ridged_noise': (7, 8), 'ravine': (11,), 'crater': (7,), 'pit': (11,), 'spire_base': (6,)}
    ids = set()
    for f in data['features']:
        ident, kind, stage = f['id'], f['type'], f['stage']
        if ident in ids: raise ValueError('Duplicate feature '+ident)
        ids.add(ident)
        if kind in counts:
            a = f['parameters']
            if len(a) not in counts[kind]: raise ValueError('Wrong parameter count '+ident)
            divisors = {'gaussian_hill': (2,3), 'spire_base': (2,3), 'ravine': (5,7,8), 'crater': (4,6), 'pit': (4,8,9)}
            if kind == 'ridged_noise' and len(a) == 8: divisors[kind] = (3,4)
            if any(a[i] <= 0 for i in divisors.get(kind, ())): raise ValueError('Invalid radius '+ident)
            if kind == 'pit' and a[4] <= a[3]: raise ValueError('Invalid pit transition')
            if kind == 'ravine' and int(a[6]) % 2: raise ValueError('Ravine along power must be even')
            if stage not in ('legacy','new'): raise ValueError('Invalid relief stage '+ident)
        elif kind not in ('canyon', 'escarpment', 'path', 'descent'):
            raise ValueError('Unsupported feature '+kind)
        if 'route_reference' in f: f['line_cm'] = routes[f['route_reference']]
        if kind == 'descent' and 'line_cm' not in f:
            # Anchor-only descents use the native generator when the direct run is short.
            # Without a bottom anchor, derive the foot from the parent wall and side.
            top = f['top_anchor_cm']
            bottom = f.get('bottom_anchor_cm')
            if bottom is None:
                parent = next(p for p in data['features'] if p['id'] == f['parent'])
                best = None
                for a, b in zip(parent['line_cm'], parent['line_cm'][1:]):
                    length = math.dist(a,b)
                    tangent = [(b[k]-a[k])/length for k in range(2)]
                    t = max(0,min(length,sum((top[k]-a[k])*tangent[k] for k in range(2))))
                    q = [a[k]+t*tangent[k] for k in range(2)]
                    candidate = (math.dist(top,q), q, [-tangent[1],tangent[0]])
                    if best is None or candidate[0] < best[0]: best = candidate
                _, q, normal = best
                if parent['type'] == 'canyon':
                    side = f['side']
                    if side not in (-1,1): raise ValueError('Descent side must be -1 or +1: '+ident)
                    # Centre of that half of the canyon floor, clear of the talus.
                    offset = side*min(parent['floor_width_cm'])/4
                elif parent['type'] == 'escarpment':
                    offset = -parent['high_side']*parent['talus_width_cm']
                else: raise ValueError('Anchor descent requires canyon/escarpment parent: '+ident)
                bottom = [q[k]+normal[k]*offset for k in range(2)]
            f['line_cm'] = [top, bottom]
        if kind in ('canyon','escarpment','path','descent'):
            line = f['line_cm']
            if len(line) < 2 or any(len(v) != 2 for v in line) or any(math.dist(a,b) < 1 for a,b in zip(line,line[1:])):
                raise ValueError('Invalid polyline '+ident)
            # Preserve existing route geometry exactly: route guarantees have priority.
            if 'route_reference' not in f: f['line_cm'] = rounded_line(line)
        for key in ('wall','north_wall','south_wall'):
            if key not in f: continue
            knots = f[key]
            if knots[0] != [0,0] or knots[-1] != [1,1] or any(len(k) != 2 for k in knots):
                raise ValueError('Wall must span (0,0)..(1,1): '+ident)
            if any(not 0 <= k[1] <= 1 for k in knots) or any(a[0] >= b[0] or a[1] > b[1] for a,b in zip(knots,knots[1:])):
                raise ValueError('Wall knots must be monotone '+ident)
        if kind in ('canyon','escarpment'):
            if stage != 'new' or f['end_blend_cm'] <= 0: raise ValueError('Invalid cliff '+ident)
        if kind == 'canyon':
            if f['depth_cm'] <= 0 or any(not 0 < floor < rim for floor,rim in zip(f['floor_width_cm'],f['rim_width_cm'])):
                raise ValueError('Invalid canyon widths '+ident)
            if len(f['rim_width_cm']) != 2 or len(f['floor_width_cm']) != 2: raise ValueError('Width pairs required')
        if kind == 'escarpment':
            if f['vertical_offset_cm'] not in (0,-f['drop_cm']): raise ValueError('Invalid cliff vertical offset')
            if f['high_side'] not in (-1,1) or any(f[k] <= 0 for k in ('drop_cm','face_width_cm','talus_width_cm','plateau_blend_cm')):
                raise ValueError('Invalid escarpment '+ident)
        if kind in ('path','descent'):
            if stage != 'path' or any(f[k] <= 0 for k in ('width_cm','shoulder_cm','endpoint_blend_cm','max_grade','max_cross_slope')):
                raise ValueError('Invalid path '+ident)
            f.setdefault('minimum_tread_width_cm', f['width_cm'])
            if not 68 <= f['minimum_tread_width_cm'] <= f['width_cm']:
                raise ValueError('Tread must fit a radius 34cm capsule: '+ident)
            if kind == 'descent':
                if any(f[k] <= 0 for k in ('corridor_width_cm','minimum_turn_radius_cm')):
                    raise ValueError('Invalid generator corridor '+ident)
                if f['minimum_turn_radius_cm'] < f['width_cm']/2 + f['shoulder_cm']:
                    raise ValueError('Turn radius cannot support outer tread/shoulder '+ident)
            else:
                f.setdefault('hard_max_grade', .20)
                if not 0 < f['hard_max_grade'] < 1:
                    raise ValueError('Invalid hard grade ceiling '+ident)
            if not 0 <= f['sink_cm'] <= 25 or f['max_grade'] >= 1: raise ValueError('Invalid path tuning '+ident)
    if any(f['type'] == 'descent' and f['parent'] not in ids for f in data['features']): raise ValueError('Unknown descent parent')
    data['resolved'] = dict(validated=True, discs_cm=p['discs_cm']+[[*cruiser,p['cruiser_radius_cm']]],
                            routes=[dict(id=k,line_cm=v) for k,v in routes.items()],
                            pcg_cell_size_cm=25000, pcg_origin_cm=0)
    return data


def main():
    import unreal
    root = pathlib.Path(unreal.Paths.project_dir())
    report_file = root/'Docs/Phase5_TerrainResults.json'
    native_file = root/'Saved/Codex/phase5_terrain_native.json'
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report = dict(status='starting', pcg_rebuild_required=True, heavy_validation_deferred_to_user=True)
    def write(): report_file.write_text(json.dumps(report,indent=2),encoding='utf-8')
    write()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    saving = unreal.EditorLoadingAndSavingUtils
    def dirty(): return list(saving.get_dirty_map_packages()) + list(saving.get_dirty_content_packages())
    before = {p.get_path_name() for p in dirty()}
    try:
        if unreal.EditorLevelLibrary.get_game_world(): raise RuntimeError('Stop PIE before authoring')
        if any('L_Dustfall_Foundation' in p for p in before):
            raise RuntimeError('Foundation has pre-existing unsaved changes; preserve/save those before terrain authoring')
        current = list(actors.get_all_level_actors())
        landscape = next(a for a in current if isinstance(a,unreal.Landscape))
        if '/Game/World/Maps/L_Dustfall_Foundation' not in landscape.get_path_name(): raise RuntimeError('Wrong map')
        landmarks = json.loads((root/'Saved/Codex/landmark_build_report.json').read_text())
        cruiser = (landmarks['Cruiser']['relative_x_cm'],landmarks['Cruiser']['relative_y_cm'])
        routes = runpy.run_path(str(root/'Scripts/phase2_layout.py'))['route_polylines'](cruiser)
        source = root/'Scripts/Data/terrain_features_v2.json'
        data = resolve_features(json.loads(source.read_text()),cruiser,routes)
        resolved = root/'Saved/Codex/terrain_features_v2_resolved.json'
        resolved.parent.mkdir(parents=True,exist_ok=True)
        resolved.write_text(json.dumps(data,indent=2),encoding='utf-8')
        report.update(feature_source=str(source.relative_to(root)), feature_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      resolved_features=str(resolved.relative_to(root)),design_changes=data['documentation']['design_changes'],
                      fall_cache_risks=data['documentation']['fall_cache_risks'])
        baseline=root/'Scripts/Data/Phase3LandscapeBaseline.bin'
        validation_file=root/'Saved/Codex/phase5_terrain_validation.json'
        status=unreal.DustfallTerrainLibrary.validate_terrain_features(
            landscape,str(baseline),str(resolved),str(validation_file))
        validation=json.loads(validation_file.read_text())
        report.update(validation=validation, native_result=status, validate_only=VALIDATE_ONLY)
        after_validation={p.get_path_name() for p in dirty()}
        report['validation_editor_stayed_clean'] = after_validation == before
        if after_validation != before:
            raise RuntimeError('Validation changed dirty package set; stopping before authoring')
        if not status.startswith('OK'):
            report.update(status='validation_failed', native=validation)
            write()
            unreal.log_error(status)
            return
        if VALIDATE_ONLY:
            report.update(status='validation_passed', native=validation)
            write()
            return
        # First potentially dirty operation, only after full native validation.
        runpy.run_path(str(root/'Scripts/load_phase3_authoring_cells.py'))
        current = list(actors.get_all_level_actors())
        landscape = next(a for a in current if isinstance(a,unreal.Landscape))
        world = unreal.EditorLevelLibrary.get_editor_world()
        ignore = [a for a in current if not isinstance(a,unreal.LandscapeProxy)]
        breaker = unreal.get_default_object(unreal.GameplayStatics.static_class())
        def trace(x,y):
            hit = unreal.SystemLibrary.line_trace_single(world,unreal.Vector(x,y,100000),unreal.Vector(x,y,-100000),
                        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,unreal.DrawDebugTrace.NONE,True)
            parts = breaker.call_method('BreakHitResult',(hit,))
            if not parts[0]: raise RuntimeError('Landscape collision missing at '+str((x,y)))
            return parts[5].z
        # Reuse Phase3's tag, footprint seating and stake offsets. Do not call
        # dress_geology(): it destroys/rebuilds all formations and creates assets.
        phase3 = runpy.run_path(str(root/'Scripts/build_phase3_terrain.py'))
        geology = []
        for a in current:
            if phase3['TAG'] not in [str(t) for t in a.tags]: continue
            loc=a.get_actor_location()
            geology.append((a,loc,trace(loc.x,loc.y)))
        status=unreal.DustfallTerrainLibrary.author_terrain_from_features(landscape,str(baseline),str(resolved),str(native_file))
        report['native_result']=status
        if not status.startswith('OK'):
            if native_file.exists(): report['native']=json.loads(native_file.read_text())
            raise RuntimeError(status)
        report.update(status='waiting_for_collision',baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest())
        state=dict(start=time.monotonic(),handle=None,last_poll=0)
        def finish_tick(delta):
            try:
                if time.monotonic()-state['start'] < 3 or time.monotonic()-state['last_poll'] < .5: return
                state['last_poll']=time.monotonic()
                if time.monotonic()-state['start'] > 90: raise RuntimeError('Landscape collision update timed out')
                native=json.loads(native_file.read_text())
                paths=json.loads((root/'Saved/Codex/TerrainMasks/polylines.json').read_text())['paths']
                # Poll actual collision against output heights before reseating/saving.
                errors=[abs(trace(*p[:2])-p[2]) for line in paths for p in line['polyline_cm'][::10]]
                if errors and max(errors) > 15:
                    report['collision_pending_max_error_cm']=max(errors);write();return
                moved=[]
                for a,loc,old_ground in geology:
                    ground=trace(loc.x,loc.y)
                    if abs(ground-old_ground)<.5: continue
                    if a.get_actor_label().startswith('P3_JaggedOutcrop_'):
                        mesh=a.static_mesh_component.static_mesh; bounds=mesh.get_bounds(); scale=a.get_actor_scale3d()
                        width=max(bounds.box_extent.x*2*scale.x,bounds.box_extent.y*2*scale.y)
                        zs=[trace(loc.x+dx*width*.3,loc.y+dy*width*.3) for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1))]
                        z=min(zs)-70-(bounds.origin.z-bounds.box_extent.z)*scale.z
                    else: z=ground+(loc.z-old_ground)
                    a.modify()
                    for component in a.get_components_by_class(unreal.SceneComponent): component.modify()
                    a.set_actor_location(unreal.Vector(loc.x,loc.y,z),False,True)
                    moved.append(a.get_actor_label())
                probes=[]
                def probe(name,x,y,expected=None):
                    z=trace(x,y);row=dict(id=name,xy_cm=[x,y],collision_z_cm=z)
                    if expected is not None: row['heightfield_error_cm']=abs(z-expected)
                    probes.append(row);return z
                for line in paths:
                    pts=line['polyline_cm'];maximum=0;previous=None
                    # Native polylines are <=1m. Probe every 10m and final endpoint.
                    for i in sorted(set(range(0,len(pts),10))|{len(pts)-1}):
                        p=pts[i];z=probe(line['id'],*p[:2],p[2])
                        if previous: maximum=max(maximum,abs(z-previous[2])/math.dist(p[:2],previous[:2]))
                        previous=[*p[:2],z]
                    line['collision_maximum_grade_10m']=maximum
                for key,line in routes.items():
                    for a,b in zip(line,line[1:]):
                        count=max(1,math.ceil(math.dist(a,b)/1000))
                        for i in range(count+1): probe('route_'+key,*[a[k]+(b[k]-a[k])*i/count for k in range(2)])
                for f in data['features']:
                    if f['type'] not in ('canyon','escarpment'): continue
                    # Every 10m along the feature: floor/rim or top/foot, not only one hero view.
                    line=f['line_cm']
                    for a,b in zip(line,line[1:]):
                        length=math.dist(a,b);normal=[-(b[1]-a[1])/length,(b[0]-a[0])/length]
                        for j in range(max(1,math.ceil(length/1000))+1):
                            t=j/max(1,math.ceil(length/1000));p=[a[k]+(b[k]-a[k])*t for k in range(2)]
                            offsets=[0,-max(f['rim_width_cm'])/2,max(f['rim_width_cm'])/2] if f['type']=='canyon' else [f['high_side']*f['face_width_cm'],-f['high_side']*f['talus_width_cm']]
                            for offset in offsets:
                                x,y=[p[k]+normal[k]*offset for k in range(2)]
                                # End caps can meet map boundary: report, do not invent collision beyond it.
                                lo_x,lo_y,hi_x,hi_y=native['mask_world_bounds_cm']
                                if lo_x<=x<=hi_x and lo_y<=y<=hi_y: probe(f['id'],x,y)
                cells={a.get_actor_label():a for a in current if a.get_actor_label().startswith('P3_PCGCell_')}
                changed=['P3_PCGCell_%d_%d'%tuple(v) for v in native['changed_pcg_grid_cells']]
                report.update(status='complete',native=native,reseated_actors=moved,collision_probes=probes,
                              paths=paths,changed_pcg_cells=changed,missing_pcg_cells=[k for k in changed if k not in cells],
                              acceptance='Authoring/collision sampling only; Lead must inspect captures and playtest descents/fall cache')
                packages=[p for p in dirty() if p.get_path_name() not in before and 'L_Dustfall_Foundation' in p.get_path_name()]
                if not saving.save_packages(packages,True): raise RuntimeError('Failed saving terrain/map/external actor or component packages')
                native['status']='applied_collision_verified'
                report['saved_packages']=[p.get_path_name() for p in packages]
                unreal.unregister_slate_post_tick_callback(state['handle']);unreal._dustfall_phase5_terrain_handle=None
                write()
            except Exception:
                report.update(status='failed',error=traceback.format_exc());write()
                unreal.unregister_slate_post_tick_callback(state['handle']);unreal._dustfall_phase5_terrain_handle=None
                unreal.log_error(report['error'])
        state['handle']=unreal.register_slate_post_tick_callback(finish_tick)
        unreal._dustfall_phase5_terrain_handle=state['handle'];write()
    except Exception:
        report.update(status='failed',error=traceback.format_exc());write();raise


if __name__ == '__main__':
    main()
