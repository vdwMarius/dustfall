"""Build replaceable Phase 2 exterior landmark blockouts in the open level.

Run in the editor after loading the foundation map and its landscape cells.
No map save is performed. The habitat blockout defines the local origin.
All locations and dimensions are centimetres; these are non-interactive scenery.
"""
import json
import math
import pathlib
import unreal

TAG = "DF_Phase2_Landmark"
FOLDER = "DUSTFALL/Phase2_Landmarks"


def build():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.EditorLevelLibrary.get_editor_world()
    current = list(actors.get_all_level_actors())
    bases = [a for a in current if a.get_actor_label() == "Hab_Base_Temporary"
             and "DF_Phase1_Habitat_Blockout" in [str(t) for t in a.tags]]
    if len(bases) != 1:
        raise RuntimeError("Expected exactly one Phase 1 habitat base in the loaded level")
    base = bases[0].get_actor_location()
    origin = (base.x, base.y, base.z - 10.0)
    landscapes = [a for a in current if isinstance(a, unreal.LandscapeProxy)]
    if not landscapes:
        raise RuntimeError("No loaded landscape; load the landmark landscape cells first")
    # Ignore every non-landscape actor, including prior landmark geometry and the
    # landing pad. A missed trace is an error, never a guessed elevation.
    ignored = [a for a in current if not isinstance(a, unreal.LandscapeProxy)]

    def ground(x, y):
        hit = unreal.SystemLibrary.line_trace_single(
            world, unreal.Vector(x, y, 100000), unreal.Vector(x, y, -100000),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignored,
            unreal.DrawDebugTrace.NONE, True)
        parts = unreal.get_default_object(unreal.GameplayStatics.static_class()).call_method(
            "BreakHitResult", (hit,))
        if not parts[0]:
            raise RuntimeError("Landscape trace missed at ({:.0f}, {:.0f}); load its cell".format(x, y))
        return parts[5].z

    # Probe the footprint as well as its center before touching old actors.
    sites = {"Wreck": (15000, 10000, 1100, 1100),
             "Ruin": (35000, -25000, 900, 900),
             "Cruiser": (-55000, 5000, 10500, 6500)}
    elevations = {}
    report = {}
    for name, (dx, dy, rx, ry) in list(sites.items()):
        offsets = [(0, 0)] if name != "Cruiser" else sorted(
            ((x, y) for x in range(-20000, 20001, 5000)
             for y in range(-20000, 20001, 5000)),
            key=lambda p: (p[0] * p[0] + p[1] * p[1], p[0], p[1]))
        selected = None
        for sx, sy in offsets:
            cx, cy = dx + sx, dy + sy
            if name == "Cruiser" and math.hypot(cx, cy) < 40000:
                continue
            x, y = origin[0] + cx, origin[1] + cy
            try:
                heights = [ground(x + ox, y + oy) for ox, oy in
                           ((0, 0), (rx, 0), (-rx, 0), (0, ry), (0, -ry),
                            (rx, ry), (rx, -ry), (-rx, ry), (-rx, -ry))]
            except RuntimeError:
                if name != "Cruiser":
                    raise
                continue
            spread = max(heights) - min(heights)
            if spread <= 700:
                selected = (cx, cy, heights[0], min(heights), max(heights))
                break
        if selected is None:
            raise RuntimeError(name + " has no loaded footprint within the 7 m height limit; load cells or adjust terrain")
        cx, cy, center_z, min_z, max_z = selected
        sites[name] = (cx, cy, rx, ry)
        elevations[name] = center_z
        report[name] = {"relative_x_cm": cx, "relative_y_cm": cy,
                        "center_ground_z_cm": center_z, "min_ground_z_cm": min_z,
                        "max_ground_z_cm": max_z, "height_range_cm": max_z - min_z}

    cube = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
    cylinder = unreal.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
    metal = unreal.load_asset("/Game/Habitat/Blockout/M_Hab_Blockout_DustyMetal")
    dark = unreal.load_asset("/Game/Habitat/Blockout/M_Hab_Blockout_Dark")
    rusty = unreal.load_asset("/Game/World/Megascans/Phase2/RustyMetal/M_RustyMetal") or metal
    concrete = unreal.load_asset("/Game/World/Megascans/Phase2/StainedConcrete/M_StainedConcrete") or metal
    if not cube or not cylinder or not metal or not dark:
        raise RuntimeError("Required engine cube or Phase 1 dusty metal materials are missing")
    for actor in current:
        if TAG in [str(t) for t in actor.tags]:
            actors.destroy_actor(actor)

    def box(site, label, offset, size, mat=None, yaw=0, collision=True, pitch=0, mesh=None):
        dx, dy, _, _ = sites[site]
        if site == "Cruiser":
            offset = (offset[0] * 2.7, offset[1] * 2.7, offset[2] * 1.5)
            size = (size[0] * 2.7, size[1] * 2.7, size[2] * 1.5)
        if mat is None:
            mat = concrete if site == "Ruin" else rusty
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(
            origin[0] + dx + offset[0], origin[1] + dy + offset[1],
            elevations[site] + offset[2]))
        if not actor:
            raise RuntimeError("Could not spawn " + label)
        actor.set_actor_label("P2_" + site + "_" + label)
        actor.tags = [unreal.Name(TAG)]
        actor.set_folder_path(FOLDER + "/" + site)
        component = actor.static_mesh_component
        component.set_static_mesh(mesh or cube)
        component.set_material(0, mat)
        component.set_collision_profile_name("BlockAll" if collision else "NoCollision")
        actor.set_actor_scale3d(unreal.Vector(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0))
        actor.set_actor_rotation(unreal.Rotator(pitch=pitch, yaw=yaw, roll=0), False)

    # Crashed transport: fractured hull with exposed transverse ribs, a tail,
    # and scattered plates. No claimed enterable or loot-bearing interior.
    box("Wreck", "Hull", (0, 0, 250), (1500, 550, 500), yaw=18)
    box("Wreck", "BrokenBow", (760, 250, 135), (520, 420, 260), dark, 18)
    box("Wreck", "TailFin", (-550, -180, 620), (200, 90, 800), dark, 18)
    box("Wreck", "PortWing", (-120, -420, 100), (650, 440, 110), metal, 18)
    for i, x in enumerate((-350, 0, 350)):
        box("Wreck", "Rib%02d" % i, (x, 0, 530), (65, 620, 100), dark, 18, False)
    box("Wreck", "DebrisA", (1000, -430, 55), (300, 180, 100), dark, -15)
    box("Wreck", "DebrisB", (-950, 500, 45), (240, 120, 80), metal, 42)

    # Ruined habitat: collapsed exterior walls suggest the Phase 1 pod's scale.
    box("Ruin", "Footing", (0, 0, 30), (850, 600, 60), dark)
    box("Ruin", "BackWall", (-380, 0, 150), (90, 570, 300))
    box("Ruin", "SideWall", (0, -260, 115), (700, 90, 230))
    box("Ruin", "WallFragment", (120, 260, 90), (450, 85, 180))
    box("Ruin", "CollapsedRoof", (-80, -30, 105), (450, 260, 70), dark, 24)
    box("Ruin", "Antenna", (-330, -220, 400), (35, 35, 650), dark)
    box("Ruin", "Panel", (420, 360, 35), (220, 160, 55), dark, -28)

    # Distant massive cruiser: closed masses, broken spine, bridge and engines.
    box("Cruiser", "MainHull", (0, 0, 1000), (5400, 1400, 1800), yaw=-22)
    box("Cruiser", "ForwardHull", (2600, -1050, 720), (1800, 1050, 1300), dark, -22)
    box("Cruiser", "Bridge", (-500, 200, 2300), (1500, 850, 900), metal, -22)
    box("Cruiser", "DorsalSpine", (300, -120, 1900), (4300, 220, 260), dark, -22)
    box("Cruiser", "BrokenFin", (-1400, 550, 2450), (700, 140, 1500), dark, -22)
    for i, y in enumerate((-500, 0, 500)):
        box("Cruiser", "Engine%02d" % i, (-2600 + y * 0.4, y + 1000, 500),
            (360, 360, 800), dark, -22, pitch=90, mesh=cylinder)
    box("Cruiser", "FallenPlate", (1500, 1700, 100), (1400, 450, 160), rusty, 12, pitch=8)
    for i, y in enumerate((-350, 0, 350)):
        box("Cruiser", "HullStrip%02d" % i, (0, y, 1950), (4100, 70, 100), dark, -22, False)
    for i, x in enumerate((-1200, -600, 0, 600, 1200)):
        box("Cruiser", "HullRib%02d" % i, (x, 0, 2000), (70, 1400, 110), rusty, -22, False)
    report_path = pathlib.Path(unreal.Paths.project_dir()) / "Saved/Codex/landmark_build_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("Phase 2 landmarks built; report: " + str(report_path))


if __name__ == "__main__":
    build()
