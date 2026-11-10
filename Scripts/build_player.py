"""Build DUSTFALL's Phase 1 player from the UE 5.8 third-person template.

Run via UnrealEditor-Cmd with PythonScriptPlugin enabled. The template supplies
Enhanced Input movement/look/jump; F, V and Shift supplement those bindings.
This script only saves the character after all graph wiring compiles.
"""
import pathlib, traceback, unreal

log_path = pathlib.Path(unreal.Paths.project_saved_dir()) / 'Codex' / 'player_build.txt'
log_path.parent.mkdir(parents=True, exist_ok=True)
log_lines = []
def log(message):
    log_lines.append(str(message))
    log_path.write_text('\n'.join(log_lines), encoding='utf-8')
    unreal.log('[DUSTFALL player] ' + str(message))

def require(value, message):
    if not value: raise RuntimeError(message)
    return value

def subobjects(bp):
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    result = []
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(handle)
        obj = lib.get_associated_object(data)
        result.append((handle, obj, str(lib.get_variable_name(data))))
    return subsystem, result

def pin(node, name, direction):
    for p in node.list_all_pins():
        if str(p.get_pin_name()) == name and p.get_pin_direction() == direction: return p
    raise RuntimeError('Missing pin %s on %s: %s' % (name, node.get_node_title(), [str(p.get_pin_name()) for p in node.list_all_pins()]))

IN = unreal.EdGraphPinDirection.EGPD_INPUT
OUT = unreal.EdGraphPinDirection.EGPD_OUTPUT
def connect(a, ap, b, bp):
    require(pin(a, ap, OUT).try_create_connection(pin(b, bp, IN)), 'Failed connection %s.%s -> %s.%s' % (a, ap, b, bp))
def value(n, p, v):
    require(pin(n, p, IN).set_pin_value(str(v)), 'Failed default %s.%s' % (n, p))
def output_name(node):
    pins = [p for p in node.list_all_pins() if p.get_pin_direction() == OUT]
    require(pins, 'No output for ' + str(node))
    return str(pins[0].get_pin_name())

DEFAULTS = {'WalkSpeed': 500.0, 'SprintSpeed': 750.0, 'ThirdPersonArmLength': 400.0, 'FirstPersonEyeOffset': 64.0, 'FlashlightIntensity': 15000.0, 'FlashlightRange': 2500.0, 'FlashlightOuterCone': 35.0, 'FlashlightInnerCone': 20.0}

def player_data():
    """Create Blueprint data asset type and authoring instance for rebuilds."""
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    blueprint_factory = unreal.BlueprintFactory()
    blueprint_factory.set_editor_property("parent_class", unreal.PrimaryDataAsset)
    bp_path = "/Game/Data/BP_PlayerFoundationData"
    bp = unreal.EditorAssetLibrary.load_asset(bp_path) if unreal.EditorAssetLibrary.does_asset_exist(bp_path) else None
    if not bp:
        bp = tools.create_asset("BP_PlayerFoundationData", "/Game/Data", None, blueprint_factory)
    if not bp:
        raise RuntimeError("Could not create atmosphere data Blueprint")
    pin = unreal.BlueprintEditorLibrary.get_basic_type_by_name("real")
    existing = list(unreal.BlueprintEditorLibrary.list_member_variable_names(bp, False))
    for name in DEFAULTS:
        if name not in existing and not unreal.BlueprintEditorLibrary.add_member_variable(bp, name, pin):
            raise RuntimeError("Could not create atmosphere field " + name)
        unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp, name, True)
    if not unreal.BlueprintEditorLibrary.compile_blueprint(bp):
        raise RuntimeError("Could not compile atmosphere data Blueprint")
    factory = unreal.DataAssetFactory()
    factory.set_editor_property("data_asset_class", bp.generated_class())
    data_path = "/Game/Data/DA_PlayerFoundation_Phase1"
    data = unreal.EditorAssetLibrary.load_asset(data_path) if unreal.EditorAssetLibrary.does_asset_exist(data_path) else None
    new_data = not data
    if new_data:
        data = tools.create_asset("DA_PlayerFoundation_Phase1", "/Game/Data", None, factory)
    if not data:
        raise RuntimeError("Could not create atmosphere data asset")
    if new_data:
        for name, value in DEFAULTS.items():
            data.set_editor_property(name, value)
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(data)
    return {name: data.get_editor_property(name) for name in DEFAULTS}


try:
    settings = player_data()
    path = '/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter'
    bp = require(unreal.load_asset(path), 'Template character missing')
    subsystem, objects = subobjects(bp)
    for _, obj, var in objects: log('Component %s: %s' % (var, obj))
    camera = next((x for x in objects if isinstance(x[1], unreal.CameraComponent)), None)
    boom = next((x for x in objects if isinstance(x[1], unreal.SpringArmComponent)), None)
    movement = next((x for x in objects if isinstance(x[1], unreal.CharacterMovementComponent)), None)
    mesh = next((x for x in objects if isinstance(x[1], unreal.SkeletalMeshComponent)), None)
    require(camera and boom and movement and mesh, 'Template components incomplete')
    existing = next((x for x in objects if x[2] == 'Flashlight'), None)
    if not existing:
        h, reason = subsystem.add_new_subobject(unreal.AddNewSubobjectParams(camera[0], unreal.SpotLightComponent, bp))
        if not reason.is_empty(): raise RuntimeError('Adding flashlight: ' + str(reason))
        require(subsystem.rename_subobject(h, unreal.Text('Flashlight')), 'Could not name flashlight')
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        subsystem, objects = subobjects(bp)
        existing = next((x for x in objects if x[2] == 'Flashlight'), None)
    require(existing, 'Flashlight subobject unavailable')
    light = existing[1]
    light.set_editor_property('intensity', settings['FlashlightIntensity'])
    light.set_editor_property('attenuation_radius', settings['FlashlightRange'])
    light.set_editor_property('outer_cone_angle', settings['FlashlightOuterCone'])
    light.set_editor_property('inner_cone_angle', settings['FlashlightInnerCone'])
    light.set_editor_property('visible', False)
    movement[1].set_editor_property('max_walk_speed', settings['WalkSpeed'])
    boom[1].set_editor_property('target_arm_length', settings['ThirdPersonArmLength'])
    log('Flashlight configured')
    # Refresh handles after compilation, as component templates may have changed.
    subsystem, objects = subobjects(bp)
    names = { 'light': next(x[2] for x in objects if x[2] == 'Flashlight'),
              'boom': next(x[2] for x in objects if isinstance(x[1], unreal.SpringArmComponent)),
              'move': next(x[2] for x in objects if isinstance(x[1], unreal.CharacterMovementComponent)),
              'mesh': next(x[2] for x in objects if isinstance(x[1], unreal.SkeletalMeshComponent)),
              'camera': next(x[2] for x in objects if isinstance(x[1], unreal.CameraComponent)) }
    log('Graph variable names: ' + str(names))
    graph = unreal.BlueprintEditorLibrary.find_event_graph(bp)
    ed = unreal.BlueprintGraphEditor.get_graph_editor(graph)
    # Reserved builder positions allow safe, repeatable reconstruction.
    generated_positions = {(1000,1000),(1450,1000),(1200,1100),(1000,1400),
      (1450,1400),(1450,1570),(1200,1720),(1000,2050),(1250,2050),
      (1550,1980),(1550,2180),(1300,2360),(1900,1980),(1900,2180),
      (1700,2380),(2250,1980),(2250,2180),(2050,2380),
      (700,1000),(700,1400),(700,1570),(700,2050)}
    old = [n for n in ed.list_all_nodes() if (n.get_node_pos().x, n.get_node_pos().y) in generated_positions]
    if old:
        log('Removing %d previously generated nodes' % len(old))
        ed.remove_nodes(old)
    def create(typ, x, y):
        node = require(ed.create_node_from_name(typ, unreal.Vector2D(x,y), []), 'Cannot create node ' + typ)
        log('Created ' + typ)
        return node
    def get(name, x, y):
        n = require(ed.add_get_member_variable_node(unreal.Name(name)), 'Cannot get component variable ' + name)
        n.set_node_pos(unreal.IntPoint(x,y))
        return n
    # Add keyboard events; existing Enhanced Input template events remain intact.
    key_f = create('Input|KeyboardEvents|F', 1000, 1000)
    toggle = create('Rendering|ToggleVisibility', 1450, 1000)
    light_get = get(names['light'], 1200, 1100)
    connect(key_f,'Pressed',toggle,'execute'); connect(light_get,output_name(light_get),toggle,'self')
    key_s = create('Input|KeyboardEvents|LeftShift',1000,1400)
    fast = create('Class|CharacterMovementComponent|SetMaxWalkSpeed',1450,1400)
    slow = create('Class|CharacterMovementComponent|SetMaxWalkSpeed',1450,1570)
    move_get = get(names['move'],1200,1720)
    connect(key_s,'Pressed',fast,'execute'); connect(key_s,'Released',slow,'execute')
    connect(move_get,output_name(move_get),fast,'self'); connect(move_get,output_name(move_get),slow,'self')
    value(fast,'MaxWalkSpeed',settings['SprintSpeed']); value(slow,'MaxWalkSpeed',settings['WalkSpeed'])
    key_v = create('Input|KeyboardEvents|V',1000,2050)
    flip = require(ed.add_macro_node('/Engine/EditorBlueprintResources/StandardMacros.StandardMacros.FlipFlop'), 'Cannot create FlipFlop macro')
    flip.set_node_pos(unreal.IntPoint(1250,2050))
    log('FlipFlop pins: ' + ', '.join(str(p.get_pin_name()) for p in flip.list_all_pins()))
    first = create('Class|SpringArmComponent|SetTargetArmLength',1550,1980)
    third = create('Class|SpringArmComponent|SetTargetArmLength',1550,2180)
    boom_get = get(names['boom'],1300,2360)
    connect(key_v,'Pressed',flip,'None'); connect(flip,'A',first,'execute'); connect(flip,'B',third,'execute')
    connect(boom_get,output_name(boom_get),first,'self'); connect(boom_get,output_name(boom_get),third,'self')
    value(first,'TargetArmLength','0.0'); value(third,'TargetArmLength',settings['ThirdPersonArmLength'])
    # Hide the body for the owning player in first person to avoid camera clipping.
    hide = require(ed.add_call_function_node('/Script/Engine.PrimitiveComponent:SetOwnerNoSee'), 'Missing SetOwnerNoSee')
    show = require(ed.add_call_function_node('/Script/Engine.PrimitiveComponent:SetOwnerNoSee'), 'Missing SetOwnerNoSee')
    hide.set_node_pos(unreal.IntPoint(1900,1980)); show.set_node_pos(unreal.IntPoint(1900,2180))
    mesh_get = get(names['mesh'],1700,2380)
    connect(first,'then',hide,'execute'); connect(third,'then',show,'execute')
    connect(mesh_get,output_name(mesh_get),hide,'self'); connect(mesh_get,output_name(mesh_get),show,'self')
    value(hide,'bNewOwnerNoSee','true'); value(show,'bNewOwnerNoSee','false')
    eye = require(ed.add_call_function_node('/Script/Engine.SceneComponent:K2_SetRelativeLocation'), 'Missing SetRelativeLocation')
    reset = require(ed.add_call_function_node('/Script/Engine.SceneComponent:K2_SetRelativeLocation'), 'Missing SetRelativeLocation')
    eye.set_node_pos(unreal.IntPoint(2250,1980)); reset.set_node_pos(unreal.IntPoint(2250,2180))
    camera_get = get(names['camera'],2050,2380)
    connect(hide,'then',eye,'execute'); connect(show,'then',reset,'execute')
    connect(camera_get,output_name(camera_get),eye,'self'); connect(camera_get,output_name(camera_get),reset,'self')
    value(eye,'NewLocation','(X=0.0,Y=0.0,Z=%s)' % settings['FirstPersonEyeOffset']); value(reset,'NewLocation','(X=0.0,Y=0.0,Z=0.0)')
    # Named events are callable by automation and future UI/controller bindings.
    for name, x, y, target, target_pin in [
        ('DF_ToggleFlashlight',700,1000,toggle,'execute'),
        ('DF_StartSprint',700,1400,fast,'execute'),
        ('DF_StopSprint',700,1570,slow,'execute'),
        ('DF_ToggleView',700,2050,flip,'None')]:
        event = require(ed.add_custom_event_node(name), 'Cannot create event ' + name)
        event.set_node_pos(unreal.IntPoint(x,y))
        exec_pin = next((p for p in event.list_all_pins() if p.get_pin_direction() == OUT and str(p.get_pin_type_display_string()) == 'Exec'), None)
        require(exec_pin, 'No exec output on ' + name)
        require(exec_pin.try_create_connection(pin(target,target_pin,IN)), 'Cannot connect event ' + name)
    ok = unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    errors = list(ed.list_nodes_with_errors())
    log('Compile result %s; node errors %s' % (ok, errors))
    require(ok and not errors, 'Character Blueprint failed to compile')
    require(unreal.EditorAssetLibrary.save_loaded_asset(bp, False), 'Could not save player Blueprint')
    log('Player saved successfully')
    # Project-owned extension points keep DUSTFALL logic separate from template paths.
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    def child_blueprint(path, name, folder, parent):
        asset = unreal.EditorAssetLibrary.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
        if not asset:
            factory = unreal.BlueprintFactory()
            factory.set_editor_property('parent_class', parent)
            asset = require(tools.create_asset(name, folder, None, factory), 'Cannot create ' + path)
        require(unreal.BlueprintEditorLibrary.compile_blueprint(asset), 'Cannot compile ' + path)
        return asset
    character = child_blueprint('/Game/Player/BP_DustfallCharacter', 'BP_DustfallCharacter', '/Game/Player', bp.generated_class())
    template_mode = require(unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonGameMode'), 'Missing template GameMode')
    mode = child_blueprint('/Game/Core/BP_DustfallGameMode', 'BP_DustfallGameMode', '/Game/Core', template_mode.generated_class())
    unreal.get_default_object(mode.generated_class()).set_editor_property('default_pawn_class', character.generated_class())
    require(unreal.EditorAssetLibrary.save_loaded_asset(character, False), 'Cannot save Dustfall character')
    require(unreal.EditorAssetLibrary.save_loaded_asset(mode, False), 'Cannot save Dustfall GameMode')
    log('Project-owned character and GameMode saved')
except Exception:
    log(traceback.format_exc())
    raise
