"""Author the first accessible crashed transport section, after Phase 3 acceptance.

Replaces only P2_Wreck_* tagged landmark blockouts and own Phase4 wreck actors.
Open ripped flank, grounded deck/ramp, cargo and recorder bay; no sealed loot box.
No Python runtime requirement. Uses the same worn pod materials and licensed scans.
"""
import json
import math
import pathlib
import runpy
import unreal

ROOT=pathlib.Path(unreal.Paths.project_dir()).resolve()
TAG='DF_Phase4_Wreck'


def build():
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    current=list(actors.get_all_level_actors())
    origin=runpy.run_path(str(ROOT/'Scripts/habitat_layout.py'))['habitat_origin'](current)
    report=json.loads((ROOT/'Saved/Codex/landmark_build_report.json').read_text())['Wreck']
    anchor=(origin[0]+report['relative_x_cm'],origin[1]+report['relative_y_cm'],report['center_ground_z_cm'])
    cube=unreal.load_asset('/Engine/BasicShapes/Cube.Cube')
    metal=unreal.load_asset('/Game/Habitat/Materials/M_P3_Hab_PaleMetal')
    dark=unreal.load_asset('/Game/Habitat/Materials/M_P3_Hab_Charcoal')
    amber=unreal.load_asset('/Game/Habitat/Materials/M_P3_Hab_Amber')
    if not all([cube,metal,dark,amber]): raise RuntimeError('Build rounded Phase3 habitat materials first')
    for a in current:
        if TAG in [str(t) for t in a.tags] or (a.get_actor_label().startswith('P2_Wreck_') and 'DF_Phase2_Landmark' in [str(t) for t in a.tags]):
            actors.destroy_actor(a)
    def world(p): return unreal.Vector(*(anchor[i]+p[i] for i in range(3)))
    def xyz(p):
        v=world(p); return [v.x,v.y,v.z]
    def box(label,p,size,mat=metal,pitch=0,roll=0,yaw=0,collision=True):
        a=actors.spawn_actor_from_class(unreal.StaticMeshActor,world(p)); a.set_actor_label('P4_Wreck_'+label)
        a.tags=[unreal.Name(TAG)]; a.set_folder_path('DUSTFALL/Phase4_Wreck')
        c=a.static_mesh_component; c.set_static_mesh(cube); c.set_material(0,mat)
        c.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
        a.set_actor_scale3d(unreal.Vector(*(s/100 for s in size)))
        a.set_actor_rotation(unreal.Rotator(pitch=pitch,roll=roll,yaw=yaw),False)
        return a
    # Open cargo deck and recorder alcove are reachable via a gentle 8-degree
    # ramp. Central aisle width 260cm and headroom >350cm are intentional.
    box('AccessibleDeck',(0,0,65),(2600,1500,70),dark)
    box('BoardingRamp',(-1635,-350,40),(760,450,20),dark,pitch=7.5)
    box('BackWall',(-1280,295,420),(40,870,640),dark)
    box('ForwardBulkhead',(1280,0,380),(40,1500,560),metal)
    box('FarPressureWall',(0,735,570),(2600,30,940),dark)
    # A sloped, plated dorsal hull preserves the broad shattered-wedge language
    # of the reference. Near flank is genuinely open to expose the deck.
    for bay,x in enumerate([-1150,-750,-350,50,450,850,1250]):
        height=1150-(x+1150)*.24
        box('DorsalPlate_'+str(bay),(x,0,height),(390,1570,32),metal,pitch=-13.5,roll=7,collision=False)
        box('FarHullPlate_'+str(bay),(x,797,height*.48),(395,24,height*.85),metal,roll=-13,collision=False)
        if bay in [0,2,5]:
            box('TornNearPlate_'+str(bay),(x,-810,height*.69),(310,32,height*.46),metal,roll=25+bay*4,pitch=-12,collision=False)
        box('DeckFrame_'+str(bay),(x,0,94),(18,1450,12),metal,collision=False)
        box('RoofRib_'+str(bay),(x,0,height-35),(35,1470,45),dark,pitch=-13.5,roll=7,collision=False)
    box('BrokenRearFin',(-1500,370,1420),(900,150,1700),metal,pitch=-24,roll=12,collision=False)
    for index in range(8):
        box('FinPlate_'+str(index),(-1510+index*65,278,1100+index*90),(210,24,190),dark,pitch=-24,collision=False)
    # Cargo racks occupy sides, preserving a continuous centre aisle.
    for x in [-700,-100,500]:
        box('CargoLocker_'+str(x),(x,520,230),(300,300,260),dark)
        box('LockerFace_'+str(x),(x,362,235),(270,12,210),metal,collision=False)
        for z in [170,260]: box('LockerHandle_%s_%s'%(x,z),(x,350,z),(55,12,8),dark,collision=False)
    box('RecorderConsole',(910,-420,185),(380,250,170),dark)
    box('RecorderSurface',(910,-420,275),(400,270,12),metal)
    box('RecorderStatus',(900,-565,225),(100,8,25),amber,collision=False)
    box('ServicePartition',(590,-480,380),(25,520,560),dark)
    # Readable hazard boundaries on broken hull edges, rather than invisible pits.
    for x in [-1050,-450,150,750,1150]:
        box('EdgeStanchion_'+str(x),(x,-730,180),(12,12,160),metal)
        box('AmberEdge_'+str(x),(x,-735,264),(80,12,8),amber,collision=False)
    for x,z in [(-1650,85),(400,75),(1600,120)]:
        box('FallenHull_'+str(x),(x,1120,z),(650,430,25),metal,pitch=7,roll=15,yaw=x*.01)
    for index,p in enumerate([(-850,400,620),(900,-400,500)]):
        a=actors.spawn_actor_from_class(unreal.PointLight,world(p)); a.set_actor_label('P4_Wreck_Practical_'+str(index)); a.tags=[unreal.Name(TAG)]
        a.set_folder_path('DUSTFALL/Phase4_Wreck'); c=a.point_light_component
        c.set_mobility(unreal.ComponentMobility.MOVABLE); c.set_editor_property('intensity_units',unreal.LightUnits.LUMENS)
        c.set_intensity(420); c.set_attenuation_radius(1000); c.set_light_color(unreal.LinearColor(1,.5,.18,1))
        c.set_editor_property('cast_shadows',False); c.set_editor_property('volumetric_scattering_intensity',0.)
    # Stable world coordinates consumed by Phase4 discovery authoring/tests.
    result={'anchor_cm':anchor,'entry_cm':xyz((-1900,-350,155)),
            'deck_waypoints_cm':[xyz(p) for p in [(-1100,-350,198),(-500,0,198),(300,0,198),(900,-100,198)]],
            'salvage_cm':[xyz(p) for p in [(-650,320,290),(500,320,290)]],
            'lore_cm':xyz((900,-565,300)),'scope':'Accessible transport cargo deck and recorder alcove; full cruiser stories remain later.'}
    (ROOT/'Saved/Codex/phase4_wreck_build.json').write_text(json.dumps(result,indent=2))
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True,True)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_all_dirty_levels()
    return result


if __name__=='__main__': build()
