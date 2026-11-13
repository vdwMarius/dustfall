"""Author Phase 3 survival, clone recovery and save/load in runtime Blueprints.

Run main() in the sole authoring editor, after the habitat builder. Python has
no runtime role. One persistent recovery cache accumulates unrecovered payload
on repeated deaths, so a later death cannot erase earlier carried salvage.
"""
import array
import json
import math
import pathlib
import runpy
import wave
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
BEL = unreal.BlueprintEditorLibrary
LIB = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
IN = unreal.EdGraphPinDirection.EGPD_INPUT
OUT = unreal.EdGraphPinDirection.EGPD_OUTPUT
DIRECTOR = '/Game/Systems/BP_SurvivalDirector'
SAVE = '/Game/Systems/BP_DustfallSaveGame'
DATA = '/Game/Data/BP_SurvivalData'
TUNING = '/Game/Data/DA_Survival_Phase3'
CRATE = '/Game/Systems/BP_DeathCrate'
DEFAULTS = dict(MaxOxygen=100., MaxPower=100., MaxIntegrity=100., MaxStamina=100.,
                OxygenDrainPerSecond=.12, OxygenRefillPerSecond=8.,
                PowerDrainPerSecond=.04, PowerRefillPerSecond=5.,
                StaminaDrainPerSecond=18., StaminaRefillPerSecond=12.,
                StormIntegrityDrainPerSecond=.015, WalkSpeed=500., SprintSpeed=750.,
                ExhaustedSpeed=300., SaveIntervalSeconds=30., RecoveryDistance=250.,
                OxygenWarningThreshold=20., OxygenWarningCooldown=8.,
                StaminaRecoveryThreshold=25., SprintVelocityThreshold=550.)
STATE = ['Oxygen', 'Power', 'Integrity', 'Stamina', 'CloneGeneration',
         'CarriedScrap', 'CrateScrap', 'CrateActive', 'CrateLocation', 'SavedLocation']


def need(x, message):
    if not x:
        raise RuntimeError(message)
    return x


def bp(path, parent):
    asset = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if not asset:
        folder, name = path.rsplit('/', 1)
        factory = unreal.BlueprintFactory()
        factory.set_editor_property('parent_class', parent)
        asset = TOOLS.create_asset(name, folder, None, factory)
    return need(asset, 'Cannot create ' + path)


def member(asset, name, typ):
    if name not in [str(n) for n in BEL.list_member_variable_names(asset, False)]:
        need(BEL.add_member_variable(asset, name, typ), 'Cannot add ' + name)
    BEL.set_blueprint_variable_instance_editable(asset, name, True)


def pin(n, name, direction):
    for p in n.list_all_pins():
        if str(p.get_pin_name()) == name and p.get_pin_direction() == direction:
            return p
    raise RuntimeError('Missing pin %s: %s (%s)' % (name, n.get_node_title(),
                       [str(p.get_pin_name()) for p in n.list_all_pins()]))


def wire(a, ap, b, bpname):
    need(pin(a, ap, OUT).try_create_connection(pin(b, bpname, IN)), 'Wire %s -> %s' % (ap, bpname))


def val(n, name, value):
    need(pin(n, name, IN).set_pin_value(str(value)), 'Default ' + name)


def output(n):
    return str(next(p for p in n.list_all_pins() if p.get_pin_direction() == OUT
                    and str(p.get_pin_type_display_string()) != 'Exec').get_pin_name())


class Graph:
    def __init__(self, ed):
        self.ed, self.index = ed, 0

    def place(self, node):
        need(node, 'Cannot create graph node')
        node.set_node_pos(unreal.IntPoint((self.index % 8) * 260, (self.index // 8) * 220))
        self.index += 1
        return node

    def call(self, name):
        return self.place(self.ed.add_call_function_node('/Script/Engine.' + name))

    def core(self, name):
        return self.place(self.ed.add_call_function_node('/Script/dustfall.DustfallSurvivalLibrary:' + name))

    def own(self, name):
        return self.place(self.ed.add_call_function_node(DIRECTOR + '.BP_SurvivalDirector_C:' + name))

    def get(self, name, owner=''):
        return self.place(self.ed.add_get_member_variable_node(unreal.Name(name), owner))

    def set(self, name, owner=''):
        return self.place(self.ed.add_set_member_variable_node(unreal.Name(name), owner))

    def math(self, name, a=None, b=None):
        node = self.call('KismetMathLibrary:' + name)
        for p, arg in [('A', a), ('B', b)]:
            if arg is not None:
                if isinstance(arg, tuple):
                    wire(arg[0], arg[1], node, p)
                else:
                    val(node, p, arg)
        return node

    def branch(self, source, source_pin, condition):
        n = self.place(self.ed.add_branch_node())
        wire(source, source_pin, n, 'execute')
        wire(condition, output(condition), n, 'Condition')
        return n

    def data(self, name):
        ref = self.get('Tuning')
        field = self.get(name, DATA + '.BP_SurvivalData_C')
        wire(ref, output(ref), field, 'self')
        return field

    def pawn(self):
        return self.call('GameplayStatics:GetPlayerCharacter')

    def slot(self, node):
        slot = self.get('SaveSlotName')
        wire(slot, output(slot), node, 'SlotName')

    def location(self):
        pawn = self.pawn()
        loc = self.call('Actor:K2_GetActorLocation')
        wire(pawn, 'ReturnValue', loc, 'self')
        return loc

    def setter(self, last, name, source=None, value=None, last_pin='then'):
        n = self.set(name)
        wire(last, last_pin, n, 'execute')
        if source:
            wire(source[0], source[1], n, name)
        else:
            val(n, name, value)
        return n

    def cast_save(self, value_node, value_pin):
        context = [pin(value_node, value_pin, OUT)]
        available = [str(n) for n in self.ed.list_available_nodes(context)]
        matches = [n for n in available if 'Cast' in n and 'BP_DustfallSaveGame' in n]
        if not matches:
            (ROOT / 'Saved/Codex/phase3_survival_cast_nodes.txt').write_text('\n'.join(n for n in available if 'Cast' in n or 'SaveGame' in n))
        need(matches, 'SaveGame cast node unavailable (see phase3_survival_cast_nodes.txt)')
        cast = self.place(self.ed.create_node_from_name(matches[0], unreal.Vector2D(), context))
        wire(value_node, value_pin, cast, 'Object')
        return cast


def clear_functions(asset, names):
    for graph in list(BEL.list_graph_names(asset)):
        if any(str(graph) == n or str(graph).startswith(n + '_') for n in names):
            BEL.remove_function_graph(asset, str(graph))
    need(BEL.compile_blueprint(asset), 'Cannot clear function names')


def function(asset, name):
    g = Graph(unreal.BlueprintGraphEditor.create_and_edit_function_graph(asset, name))
    entry = g.ed.find_graph_entry_pin().get_owning_node()
    return g, entry


def compile_save(asset):
    need(BEL.compile_blueprint(asset), 'Compile ' + asset.get_name())
    LIB.save_loaded_asset(asset, False)


def warning_sound():
    path = '/Game/Audio/Suit/S_OxygenWarning_Phase3'
    existing = LIB.load_asset(path) if LIB.does_asset_exist(path) else None
    if existing:
        return existing
    source = ROOT / 'Saved/Codex/OxygenWarning_Phase3.wav'
    source.parent.mkdir(parents=True, exist_ok=True)
    rate = 22050
    values = []
    for i in range(int(rate * .65)):
        t = i / rate
        local = t if t < .22 else t - .35
        amplitude = max(0., min(1., local / .012, (.22 - local) / .025)) if 0 <= local < .22 else 0.
        values.append(int(12000 * amplitude * math.sin(math.tau * (740 if t < .3 else 560) * t)))
    with wave.open(str(source), 'wb') as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(rate)
        handle.writeframes(array.array('h', values).tobytes())
    task = unreal.AssetImportTask()
    task.filename = str(source); task.destination_path = '/Game/Audio/Suit'
    task.destination_name = 'S_OxygenWarning_Phase3'; task.automated = True
    task.replace_existing = True; task.save = True
    TOOLS.import_asset_tasks([task])
    sound = need(LIB.load_asset(path), 'Warning sound import')
    sound.set_editor_property('looping', False); LIB.save_loaded_asset(sound)
    return sound


def main():
    real = BEL.get_basic_type_by_name('real')
    integer = BEL.get_basic_type_by_name('int')
    boolean = BEL.get_basic_type_by_name('bool')
    vector = BEL.get_struct_type(unreal.load_object(None, '/Script/CoreUObject.Vector'))
    types = {n: real for n in ['Oxygen', 'Power', 'Integrity', 'Stamina']}
    types.update({n: integer for n in ['CloneGeneration', 'CarriedScrap', 'CrateScrap']})
    types.update(CrateActive=boolean, CrateLocation=vector, SavedLocation=vector)
    data_bp = bp(DATA, unreal.PrimaryDataAsset)
    previous_fields = [str(n) for n in BEL.list_member_variable_names(data_bp, False)]
    for name in DEFAULTS:
        member(data_bp, name, real)
    compile_save(data_bp)
    tuning = LIB.load_asset(TUNING) if LIB.does_asset_exist(TUNING) else None
    if not tuning:
        f = unreal.DataAssetFactory()
        f.set_editor_property('data_asset_class', data_bp.generated_class())
        tuning = TOOLS.create_asset('DA_Survival_Phase3', '/Game/Data', None, f)
        for n, v in DEFAULTS.items():
            tuning.set_editor_property(n, v)
    else:
        for n, v in DEFAULTS.items():
            if n not in previous_fields:
                tuning.set_editor_property(n, v)
    LIB.save_loaded_asset(tuning)
    warning = warning_sound()
    save_bp = bp(SAVE, unreal.SaveGame)
    for n, t in types.items():
        member(save_bp, n, t)
    member(save_bp, 'SaveVersion', integer)
    compile_save(save_bp)

    crate_bp = bp(CRATE, unreal.Actor)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_blueprint(crate_bp)
    mesh = next((lib.get_associated_object(lib.get_data(h)) for h in handles
                 if isinstance(lib.get_associated_object(lib.get_data(h)), unreal.StaticMeshComponent)), None)
    if not mesh:
        h, reason = sub.add_new_subobject(unreal.AddNewSubobjectParams(handles[0], unreal.StaticMeshComponent, crate_bp))
        need(reason.is_empty(), 'Crate mesh: ' + str(reason))
        sub.rename_subobject(h, unreal.Text('RecoveryCache'))
        BEL.compile_blueprint(crate_bp)
        handles = sub.k2_gather_subobject_data_for_blueprint(crate_bp)
        mesh = next(lib.get_associated_object(lib.get_data(h)) for h in handles
                    if isinstance(lib.get_associated_object(lib.get_data(h)), unreal.StaticMeshComponent))
    mesh.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube'))
    mesh.set_relative_scale3d(unreal.Vector(.8, .55, .4))
    mesh.set_collision_profile_name('NoCollision')
    material_path = '/Game/Systems/M_RecoveryCache'
    material = LIB.load_asset(material_path) if LIB.does_asset_exist(material_path) else TOOLS.create_asset('M_RecoveryCache', '/Game/Systems', unreal.Material, unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary
    mel.delete_all_material_expressions(material)
    color = mel.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, 0, 0)
    color.set_editor_property('constant', unreal.LinearColor(.28, .11, .015, 1))
    mel.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    emissive = mel.create_material_expression(material, unreal.MaterialExpressionConstant3Vector, 0, 200)
    emissive.set_editor_property('constant', unreal.LinearColor(.6, .22, .025, 1))
    mel.connect_material_property(emissive, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    rough = mel.create_material_expression(material, unreal.MaterialExpressionConstant, 0, 400)
    rough.set_editor_property('r', .75)
    mel.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(material); LIB.save_loaded_asset(material)
    mesh.set_material(0, material)
    handles = sub.k2_gather_subobject_data_for_blueprint(crate_bp)
    objects = [(h, lib.get_associated_object(lib.get_data(h)), str(lib.get_variable_name(lib.get_data(h)))) for h in handles]
    for name, component_type in [('CacheBeacon', unreal.PointLightComponent), ('RecoveryLabel', unreal.TextRenderComponent)]:
        obj = next((o for _, o, n in objects if n == name), None)
        if not obj:
            h, reason = sub.add_new_subobject(unreal.AddNewSubobjectParams(handles[0], component_type, crate_bp))
            need(reason.is_empty(), 'Recovery marker ' + str(reason)); sub.rename_subobject(h, unreal.Text(name))
            BEL.compile_blueprint(crate_bp)
            handles = sub.k2_gather_subobject_data_for_blueprint(crate_bp)
            objects = [(h, lib.get_associated_object(lib.get_data(h)), str(lib.get_variable_name(lib.get_data(h)))) for h in handles]
            obj = next(o for _, o, n in objects if n == name)
        if name == 'CacheBeacon':
            obj.set_editor_property('intensity', 90.)
            obj.set_editor_property('attenuation_radius', 350.)
            obj.set_editor_property('light_color', unreal.Color(255, 170, 50, 255))
            obj.set_editor_property('cast_shadows', False)
            obj.set_relative_location(unreal.Vector(0, 0, 70), False, False)
        else:
            obj.set_text(unreal.Text('E  RECOVER'))
            obj.set_world_size(24.)
            obj.set_relative_location(unreal.Vector(0, -65, 100), False, False)
            obj.set_relative_rotation(unreal.Rotator(yaw=0), False, False)
    compile_save(crate_bp)

    director = bp(DIRECTOR, unreal.Actor)
    environment_bp = need(LIB.load_asset('/Game/World/Blueprints/BP_DustfallEnvironmentDirector'), 'Missing environment director')
    for n, t in types.items():
        member(director, n, t)
    for n, t in dict(InHabitat=boolean, DeathInProgress=boolean, SprintExhausted=boolean, SprintRequested=boolean,
                     HabitatCenter=vector, HabitatHalfExtent=vector, CloneSpawn=vector,
                     SaveElapsed=real, LastSaveSucceeded=boolean,
                     WarningElapsed=real, OxygenWarningCount=integer, StaminaBeforeTick=real,
                     SaveSlotName=BEL.get_basic_type_by_name('string'),
                     Tuning=BEL.get_object_reference_type(data_bp.generated_class()),
                     EnvironmentDirector=BEL.get_object_reference_type(environment_bp.generated_class()),
                     RecoveryActor=BEL.get_object_reference_type(unreal.Actor)).items():
        member(director, n, t)
    compile_save(director)
    names = ['RefreshRecoveryCache', 'SaveProgress', 'LoadProgress', 'RecoverCrate', 'RespawnClone', 'GetSuitState']
    old_events = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(director))
    keep_events = [old_events.find_event_node('ReceiveTick'), old_events.find_event_node('ReceiveBeginPlay')]
    old_events.remove_nodes([n for n in old_events.list_all_nodes() if n not in keep_events])
    clear_functions(director, names)

    # First define all functions so calls between their graphs resolve canonically.
    for name in names:
        unreal.BlueprintGraphEditor.create_and_edit_function_graph(director, name)
    need(BEL.compile_blueprint(director), 'Function declarations')

    g = Graph(unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_graph(director, 'RefreshRecoveryCache')))
    entry = g.ed.find_graph_entry_pin().get_owning_node()
    actor = g.get('RecoveryActor')
    active = g.get('CrateActive')
    inverse = g.call('KismetMathLibrary:Not_PreBool')
    wire(active, output(active), inverse, 'A')
    hide = g.call('Actor:SetActorHiddenInGame')
    wire(entry, 'then', hide, 'execute'); wire(actor, output(actor), hide, 'self'); wire(inverse, 'ReturnValue', hide, 'bNewHidden')
    move = g.call('Actor:K2_SetActorLocation')
    wire(hide, 'then', move, 'execute'); wire(actor, output(actor), move, 'self')
    loc = g.get('CrateLocation'); wire(loc, output(loc), move, 'NewLocation'); val(move, 'bTeleport', 'true')
    need(BEL.compile_blueprint(director), 'Refresh graph')

    g = Graph(unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_graph(director, 'SaveProgress')))
    entry = g.ed.find_graph_entry_pin().get_owning_node()
    last = g.setter(entry, 'SavedLocation', (g.location(), 'ReturnValue'))
    create = g.call('GameplayStatics:CreateSaveGameObject')
    val(create, 'SaveGameClass', save_bp.generated_class().get_path_name())
    wire(last, 'then', create, 'execute')
    cast = g.cast_save(create, 'ReturnValue'); wire(create, 'then', cast, 'execute')
    cast_out = next(str(p.get_pin_name()) for p in cast.list_all_pins() if str(p.get_pin_name()).startswith('As'))
    last = cast
    for name in STATE:
        setter = g.set(name, save_bp.generated_class().get_path_name())
        wire(last, 'then', setter, 'execute'); wire(cast, cast_out, setter, 'self')
        src = g.get(name); wire(src, output(src), setter, name); last = setter
    setter = g.set('SaveVersion', save_bp.generated_class().get_path_name())
    wire(last, 'then', setter, 'execute'); wire(cast, cast_out, setter, 'self'); val(setter, 'SaveVersion', 1)
    save = g.call('GameplayStatics:SaveGameToSlot')
    wire(setter, 'then', save, 'execute'); wire(cast, cast_out, save, 'SaveGameObject'); g.slot(save)
    g.setter(save, 'LastSaveSucceeded', (save, 'ReturnValue'))
    need(BEL.compile_blueprint(director), 'Save graph')

    g = Graph(unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_graph(director, 'LoadProgress')))
    entry = g.ed.find_graph_entry_pin().get_owning_node()
    exists = g.call('GameplayStatics:DoesSaveGameExist'); g.slot(exists)
    wire(entry, 'then', exists, 'execute')
    branch = g.branch(exists, 'then', exists)
    load = g.call('GameplayStatics:LoadGameFromSlot'); g.slot(load); wire(branch, 'then', load, 'execute')
    cast = g.cast_save(load, 'ReturnValue'); wire(load, 'then', cast, 'execute')
    cast_out = next(str(p.get_pin_name()) for p in cast.list_all_pins() if str(p.get_pin_name()).startswith('As'))
    version = g.get('SaveVersion', save_bp.generated_class().get_path_name()); wire(cast, cast_out, version, 'self')
    supported = g.math('EqualEqual_IntInt', (version, output(version)), 1)
    last = g.branch(cast, 'then', supported)
    for name in STATE:
        field = g.get(name, save_bp.generated_class().get_path_name()); wire(cast, cast_out, field, 'self')
        last = g.setter(last, name, (field, output(field)))
    pawn = g.pawn(); move = g.call('Actor:K2_SetActorLocation'); wire(last, 'then', move, 'execute'); wire(pawn, 'ReturnValue', move, 'self')
    loc = g.get('SavedLocation'); wire(loc, output(loc), move, 'NewLocation'); val(move, 'bTeleport', 'true')
    refresh = g.own('RefreshRecoveryCache'); wire(move, 'then', refresh, 'execute')
    need(BEL.compile_blueprint(director), 'Load graph')

    g = Graph(unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_graph(director, 'RecoverCrate')))
    entry = g.ed.find_graph_entry_pin().get_owning_node()
    active = g.get('CrateActive'); branch = g.branch(entry, 'then', active)
    loc = g.location(); crate_loc = g.get('CrateLocation')
    distance = g.call('KismetMathLibrary:Vector_Distance'); wire(loc, 'ReturnValue', distance, 'V1'); wire(crate_loc, output(crate_loc), distance, 'V2')
    allowed = g.math('LessEqual_DoubleDouble', (distance, 'ReturnValue'), (g.data('RecoveryDistance'), 'RecoveryDistance'))
    near = g.branch(branch, 'then', allowed)
    total = g.math('Add_IntInt', (g.get('CarriedScrap'), 'CarriedScrap'), (g.get('CrateScrap'), 'CrateScrap'))
    last = g.setter(near, 'CarriedScrap', (total, 'ReturnValue'))
    last = g.setter(last, 'CrateScrap', value=0)
    last = g.setter(last, 'CrateActive', value='false')
    refresh = g.own('RefreshRecoveryCache'); wire(last, 'then', refresh, 'execute')
    save = g.own('SaveProgress'); wire(refresh, 'then', save, 'execute')
    need(BEL.compile_blueprint(director), 'Recovery graph')

    g = Graph(unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_graph(director, 'RespawnClone')))
    entry = g.ed.find_graph_entry_pin().get_owning_node()
    busy = g.get('DeathInProgress'); inverse = g.call('KismetMathLibrary:Not_PreBool'); wire(busy, output(busy), inverse, 'A')
    branch = g.branch(entry, 'then', inverse)
    last = g.setter(branch, 'DeathInProgress', value='true')
    loc = g.location(); raised = g.call('KismetMathLibrary:Add_VectorVector'); wire(loc, 'ReturnValue', raised, 'A'); val(raised, 'B', '(X=0,Y=0,Z=-65)')
    last = g.setter(last, 'CrateLocation', (raised, 'ReturnValue'))
    total = g.math('Add_IntInt', (g.get('CrateScrap'), 'CrateScrap'), (g.get('CarriedScrap'), 'CarriedScrap'))
    last = g.setter(last, 'CrateScrap', (total, 'ReturnValue'))
    last = g.setter(last, 'CarriedScrap', value=0)
    last = g.setter(last, 'CrateActive', value='true')
    count = g.math('Add_IntInt', (g.get('CloneGeneration'), 'CloneGeneration'), 1)
    last = g.setter(last, 'CloneGeneration', (count, 'ReturnValue'))
    for name in ['Oxygen', 'Power', 'Integrity', 'Stamina']:
        d = g.data('Max' + name); last = g.setter(last, name, (d, output(d)))
    last = g.setter(last, 'SprintExhausted', value='false')
    pawn = g.pawn(); move = g.call('Actor:K2_SetActorLocation'); wire(last, 'then', move, 'execute'); wire(pawn, 'ReturnValue', move, 'self')
    spawn = g.get('CloneSpawn'); wire(spawn, output(spawn), move, 'NewLocation'); val(move, 'bTeleport', 'true')
    last = g.setter(move, 'DeathInProgress', value='false')
    refresh = g.own('RefreshRecoveryCache'); wire(last, 'then', refresh, 'execute')
    save = g.own('SaveProgress'); wire(refresh, 'then', save, 'execute')
    need(BEL.compile_blueprint(director), 'Clone graph')

    query = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_graph(director, 'GetSuitState'))
    ret = None
    for name in ['Oxygen', 'Power', 'Integrity', 'Stamina', 'CloneGeneration']:
        ret = query.add_graph_output_parameter(unreal.Name(name), types[name])
    query.find_graph_entry_pin().try_create_connection(pin(ret, 'execute', IN))
    for name in ['Oxygen', 'Power', 'Integrity', 'Stamina', 'CloneGeneration']:
        src = query.add_get_member_variable_node(unreal.Name(name)); wire(src, output(src), ret, name)
    need(BEL.compile_blueprint(director), 'Query graph')

    ed = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(director))
    tick, begin = ed.find_event_node('ReceiveTick'), ed.find_event_node('ReceiveBeginPlay')
    ed.remove_nodes([n for n in ed.list_all_nodes() if n not in [tick, begin]])
    g = Graph(ed)
    # Enable director keyboard input while allowing the airlock to receive E too.
    pc = g.call('GameplayStatics:GetPlayerController')
    enable = g.call('Actor:EnableInput'); wire(begin, 'then', enable, 'execute'); wire(pc, 'ReturnValue', enable, 'PlayerController')
    load = g.own('LoadProgress'); wire(enable, 'then', load, 'execute')
    refresh = g.own('RefreshRecoveryCache'); wire(load, 'then', refresh, 'execute')
    for key, method in [('E', 'RecoverCrate'), ('F5', 'SaveProgress'), ('F9', 'LoadProgress')]:
        keynode = g.place(ed.create_node_from_name('Input|KeyboardEvents|' + key, unreal.Vector2D(), []))
        try:
            keynode.set_editor_property('consume_input', False)
        except Exception:
            pass
        call = g.own(method); wire(keynode, 'Pressed', call, 'execute')
    center, extent = g.get('HabitatCenter'), g.get('HabitatHalfExtent')
    inside = g.core('IsWithinHabitat'); loc = g.location()
    wire(loc, 'ReturnValue', inside, 'Point'); wire(center, output(center), inside, 'Origin'); wire(extent, output(extent), inside, 'HalfExtent')
    last = g.setter(tick, 'InHabitat', (inside, 'ReturnValue'))
    # Rate integration is clamped, using seconds rather than frame-dependent values.
    def integrate(lastnode, field, rate):
        clamp = g.core('IntegrateResource')
        wire(g.get(field), field, clamp, 'Current')
        wire(rate, output(rate), clamp, 'RatePerSecond')
        wire(tick, 'DeltaSeconds', clamp, 'DeltaSeconds')
        maximum = g.data('Max' + field); wire(maximum, output(maximum), clamp, 'Maximum')
        return g.setter(lastnode, field, (clamp, 'ReturnValue'))
    for field in ['Oxygen', 'Power']:
        drain = g.data(field + 'DrainPerSecond'); negative = g.math('Multiply_DoubleDouble', (drain, output(drain)), -1)
        refill = g.data(field + 'RefillPerSecond'); select = g.call('KismetMathLibrary:SelectFloat')
        wire(inside, 'ReturnValue', select, 'bPickA'); wire(refill, output(refill), select, 'A'); wire(negative, 'ReturnValue', select, 'B')
        last = integrate(last, field, select)
    environment = g.get('EnvironmentDirector')
    storm = g.get('StormIntensity', environment_bp.generated_class().get_path_name())
    wire(environment, output(environment), storm, 'self')
    wear = g.math('Multiply_DoubleDouble', (storm, output(storm)), (g.data('StormIntegrityDrainPerSecond'), 'StormIntegrityDrainPerSecond'))
    negative = g.math('Multiply_DoubleDouble', (wear, 'ReturnValue'), -1)
    sheltered = g.call('KismetMathLibrary:SelectFloat'); wire(inside, 'ReturnValue', sheltered, 'bPickA')
    val(sheltered, 'A', 0); wire(negative, 'ReturnValue', sheltered, 'B')
    last = integrate(last, 'Integrity', sheltered)
    pawn = g.pawn(); velocity = g.call('Actor:GetVelocity'); wire(pawn, 'ReturnValue', velocity, 'self')
    speed = g.call('KismetMathLibrary:VSizeXY'); wire(velocity, 'ReturnValue', speed, 'A')
    sprint = g.math('Greater_DoubleDouble', (speed, 'ReturnValue'), (g.data('SprintVelocityThreshold'), 'SprintVelocityThreshold'))
    drain = g.data('StaminaDrainPerSecond'); negative = g.math('Multiply_DoubleDouble', (drain, output(drain)), -1)
    refill = g.data('StaminaRefillPerSecond'); rate = g.call('KismetMathLibrary:SelectFloat')
    wire(sprint, 'ReturnValue', rate, 'bPickA'); wire(negative, 'ReturnValue', rate, 'A'); wire(refill, output(refill), rate, 'B')
    # Capture before integration: a fully depleted resting player must enter the
    # recovery latch even if this frame has already regenerated a small amount.
    last = g.setter(last, 'StaminaBeforeTick', (g.get('Stamina'), 'Stamina'))
    last = integrate(last, 'Stamina', rate)
    # Exhaustion limits sprint; modest recovery threshold avoids per-frame oscillation.
    exhausted = g.core('UpdateSprintExhaustion')
    wire(g.get('Stamina'), 'Stamina', exhausted, 'CurrentStamina')
    wire(g.get('StaminaBeforeTick'), 'StaminaBeforeTick', exhausted, 'StaminaBeforeTick')
    wire(g.get('SprintExhausted'), 'SprintExhausted', exhausted, 'bWasExhausted')
    wire(g.data('StaminaRecoveryThreshold'), 'StaminaRecoveryThreshold', exhausted, 'RecoveryThreshold')
    last = g.setter(last, 'SprintExhausted', (exhausted, 'ReturnValue'))
    movement = g.get('CharacterMovement', '/Script/Engine.Character'); wire(pawn, 'ReturnValue', movement, 'self')
    held = g.call('PlayerController:IsInputKeyDown'); wire(pc, 'ReturnValue', held, 'self'); val(held, 'Key', '(KeyName="LeftShift")')
    request = g.math('BooleanOR', (held, 'ReturnValue'), (g.get('SprintRequested'), 'SprintRequested'))
    select = g.call('KismetMathLibrary:SelectFloat'); wire(request, 'ReturnValue', select, 'bPickA')
    fast, walk = g.data('SprintSpeed'), g.data('WalkSpeed'); wire(fast, output(fast), select, 'A'); wire(walk, output(walk), select, 'B')
    final = g.call('KismetMathLibrary:SelectFloat'); wire(exhausted, 'ReturnValue', final, 'bPickA')
    slow = g.data('ExhaustedSpeed'); wire(slow, output(slow), final, 'A'); wire(select, 'ReturnValue', final, 'B')
    setter = g.set('MaxWalkSpeed', '/Script/Engine.CharacterMovementComponent'); wire(last, 'then', setter, 'execute'); wire(movement, output(movement), setter, 'self'); wire(final, 'ReturnValue', setter, 'MaxWalkSpeed')
    power_zero = g.math('LessEqual_DoubleDouble', (g.get('Power'), 'Power'), 0)
    power_branch = g.branch(setter, 'then', power_zero)
    flashlight = g.call('Actor:GetComponentByClass'); val(flashlight, 'ComponentClass', '/Script/Engine.SpotLightComponent')
    wire(pawn, 'ReturnValue', flashlight, 'self')
    hide_light = g.call('SceneComponent:SetVisibility'); val(hide_light, 'bNewVisibility', 'false')
    wire(flashlight, 'ReturnValue', hide_light, 'self'); wire(power_branch, 'then', hide_light, 'execute')
    # Death can be initiated by either lethal resource. Integrity is also exposed
    # for hazards; storms are consumed through an explicitly assigned director ref.
    oxygen_zero = g.math('LessEqual_DoubleDouble', (g.get('Oxygen'), 'Oxygen'), 0)
    integrity_zero = g.math('LessEqual_DoubleDouble', (g.get('Integrity'), 'Integrity'), 0)
    lethal = g.math('BooleanOR', (oxygen_zero, 'ReturnValue'), (integrity_zero, 'ReturnValue'))
    death = g.branch(hide_light, 'then', lethal)
    wire(power_branch, 'else', death, 'execute')
    respawn = g.own('RespawnClone'); wire(death, 'then', respawn, 'execute')
    elapsed = g.math('Add_DoubleDouble', (g.get('SaveElapsed'), 'SaveElapsed'), (tick, 'DeltaSeconds'))
    age = g.setter(death, 'SaveElapsed', (elapsed, 'ReturnValue'), last_pin='else')
    due = g.math('GreaterEqual_DoubleDouble', (elapsed, 'ReturnValue'), (g.data('SaveIntervalSeconds'), 'SaveIntervalSeconds'))
    branch = g.branch(age, 'then', due)
    reset = g.setter(branch, 'SaveElapsed', value=0)
    save = g.own('SaveProgress'); wire(reset, 'then', save, 'execute')
    warning_age = g.math('Add_DoubleDouble', (g.get('WarningElapsed'), 'WarningElapsed'), (tick, 'DeltaSeconds'))
    warning_tick = g.setter(save, 'WarningElapsed', (warning_age, 'ReturnValue'))
    wire(branch, 'else', warning_tick, 'execute')
    low = g.math('LessEqual_DoubleDouble', (g.get('Oxygen'), 'Oxygen'), (g.data('OxygenWarningThreshold'), 'OxygenWarningThreshold'))
    ready = g.math('GreaterEqual_DoubleDouble', (warning_age, 'ReturnValue'), (g.data('OxygenWarningCooldown'), 'OxygenWarningCooldown'))
    alert = g.math('BooleanAND', (low, 'ReturnValue'), (ready, 'ReturnValue'))
    warn = g.branch(warning_tick, 'then', alert)
    play = g.call('GameplayStatics:PlaySound2D'); val(play, 'Sound', warning.get_path_name()); val(play, 'VolumeMultiplier', .65)
    wire(warn, 'then', play, 'execute')
    reset_warning = g.setter(play, 'WarningElapsed', value=0)
    count = g.math('Add_IntInt', (g.get('OxygenWarningCount'), 'OxygenWarningCount'), 1)
    g.setter(reset_warning, 'OxygenWarningCount', (count, 'ReturnValue'))
    compile_save(director)

    # Read the live saved anchor, so a clean clone/rebuild never depends on an
    # ignored or stale local authoring report.
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    all_actors = list(actors.get_all_level_actors())
    layout = runpy.run_path(str(ROOT / 'Scripts/habitat_layout.py'))
    origin = unreal.Vector(*layout['habitat_origin'](all_actors))
    cdo = unreal.get_default_object(director.generated_class())
    cdo.set_editor_property('Tuning', tuning)
    for name in ['Oxygen', 'Power', 'Integrity', 'Stamina']:
        cdo.set_editor_property(name, DEFAULTS['Max' + name])
    cdo.set_editor_property('CloneGeneration', 1)
    cdo.set_editor_property('WarningElapsed', DEFAULTS['OxygenWarningCooldown'])
    cdo.set_editor_property('SaveSlotName', 'Dustfall_Phase3')
    cdo.set_editor_property('HabitatCenter', origin + unreal.Vector(0, 0, 235))
    cdo.set_editor_property('HabitatHalfExtent', unreal.Vector(475, 325, 185))
    cdo.set_editor_property('CloneSpawn', origin + unreal.Vector(-120, 0, 148))
    compile_save(director)
    actor = next((a for a in all_actors if a.get_class() == director.generated_class()), None)
    if not actor:
        actor = actors.spawn_actor_from_class(director.generated_class(), origin)
    actor.modify(); actor.set_actor_label('Dustfall Survival Director'); actor.set_editor_property('is_spatially_loaded', False)
    for name in ['Tuning', 'HabitatCenter', 'HabitatHalfExtent', 'CloneSpawn']:
        actor.set_editor_property(name, cdo.get_editor_property(name))
    environment_actor = need(next((a for a in all_actors if a.get_class() == environment_bp.generated_class()), None), 'Environment actor missing')
    actor.set_editor_property('EnvironmentDirector', environment_actor)
    crate = next((a for a in all_actors if a.get_class() == crate_bp.generated_class()), None)
    if not crate:
        crate = actors.spawn_actor_from_class(crate_bp.generated_class(), origin)
    crate.modify(); crate.set_actor_label('Recoverable Death Cache'); crate.set_editor_property('is_spatially_loaded', False)
    crate.set_actor_hidden_in_game(True); actor.set_editor_property('RecoveryActor', crate)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    (ROOT / 'Saved/Codex/phase3_survival_build.json').write_text(json.dumps({'status': 'built', 'director': DIRECTOR,
        'save_slot': 'Dustfall_Phase3', 'functions': names, 'defaults': DEFAULTS,
        'cache_policy': 'Single cache accumulates unrecovered scrap at latest death location',
        'scope': 'Blueprint runtime; scalar scrap contract precedes full Phase 4 inventory'}, indent=2))
    unreal.log('DUSTFALL Phase 3 survival built')


if __name__ == '__main__':
    main()
