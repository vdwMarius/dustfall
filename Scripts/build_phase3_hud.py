"""Author a small runtime suit HUD. Run after build_phase3_survival.py.

Uses Unreal's native Canvas HUD in Blueprint; no Python runs in packaged play.
"""
import pathlib
import json
import unreal

BEL = unreal.BlueprintEditorLibrary
LIB = unreal.EditorAssetLibrary
IN = unreal.EdGraphPinDirection.EGPD_INPUT
OUT = unreal.EdGraphPinDirection.EGPD_OUTPUT


def require(v, message):
    if not v:
        raise RuntimeError(message)
    return v


def pin(n, name, direction):
    return next(p for p in n.list_all_pins() if str(p.get_pin_name()) == name and p.get_pin_direction() == direction)


def wire(a, ap, b, bp):
    require(pin(a, ap, OUT).try_create_connection(pin(b, bp, IN)), 'HUD connection: ' + ap + ' -> ' + bp)


def val(n, p, v):
    require(pin(n, p, IN).set_pin_value(str(v)), 'HUD default: ' + p)


def build():
    survival = require(unreal.load_asset('/Game/Systems/BP_SurvivalDirector'), 'Build survival first')
    # Phase 5: once BP_SurvivalDirector is parented to the native director its
    # Tuning property is a UDustfallSurvivalTuning, so read maxima from that class.
    native = hasattr(unreal, 'DustfallSurvivalDirector') and         BEL.get_blueprint_parent_class(survival) == unreal.DustfallSurvivalDirector.static_class()
    tuning_class_path = '/Script/dustfall.DustfallSurvivalTuning' if native else         require(unreal.load_asset('/Game/Data/BP_SurvivalData'), 'Survival tuning class').generated_class().get_path_name()
    path = '/Game/UI/BP_DustfallSuitHUD'
    bp = unreal.load_asset(path)
    if not bp:
        f = unreal.BlueprintFactory()
        f.set_editor_property('parent_class', unreal.HUD)
        bp = require(unreal.AssetToolsHelpers.get_asset_tools().create_asset('BP_DustfallSuitHUD', '/Game/UI', None, f), 'Create HUD')
    ed = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(bp))
    ed.remove_nodes(ed.list_all_nodes())
    event = require(ed.create_node_from_name('AddEvent|EventReceiveDrawHUD', unreal.Vector2D(), []), 'Draw HUD event')
    serial = [0]

    def call(name):
        n = require(ed.add_call_function_node('/Script/Engine.' + name), name)
        serial[0] += 1
        n.set_node_pos(unreal.IntPoint(300 + serial[0] * 240, 0))
        return n

    find = call('GameplayStatics:GetActorOfClass')
    val(find, 'ActorClass', survival.generated_class().get_path_name())
    wire(event, 'then', find, 'execute')
    valid = call('KismetSystemLibrary:IsValid')
    wire(find, 'ReturnValue', valid, 'Object')
    branch = ed.add_branch_node()
    wire(find, 'then', branch, 'execute')
    wire(valid, 'ReturnValue', branch, 'Condition')
    tail = [branch, 'then']

    def chain(n):
        wire(tail[0], tail[1], n, 'execute')
        tail[:] = [n, 'then']

    def get(name):
        n = require(ed.add_get_member_variable_node(unreal.Name(name), survival.generated_class().get_path_name()), name)
        wire(find, 'ReturnValue', n, 'self')
        return n

    def rect(x, y, width, height, color):
        n = call('HUD:DrawRect')
        for p, v in [('ScreenX', x), ('ScreenY', y), ('ScreenW', width), ('ScreenH', height), ('RectColor', color)]:
            val(n, p, v)
        chain(n)
        return n

    def text(label, x, y, color='(R=0.95,G=0.72,B=0.38,A=1.0)', scale=1.0):
        n = call('HUD:DrawText')
        for p, v in [('Text', label), ('ScreenX', x), ('ScreenY', y), ('Scale', scale), ('TextColor', color), ('Font', '/Engine/EngineFonts/Roboto.Roboto')]:
            val(n, p, v)
        chain(n)
        return n

    rect(18, 18, 274, 198, '(R=0.012,G=0.018,B=0.022,A=0.78)')
    text('DUSTFALL  /  SUIT TELEMETRY', 30, 28, scale=.8)
    colors = ['(R=0.45,G=0.8,B=0.86,A=1)', '(R=0.95,G=0.70,B=0.24,A=1)', '(R=0.72,G=0.83,B=0.63,A=1)', '(R=0.72,G=0.7,B=0.6,A=1)']
    tuning = get('Tuning')
    for i, (name, label) in enumerate([('Oxygen', 'OXYGEN'), ('Power', 'POWER'), ('Integrity', 'INTEGRITY'), ('Stamina', 'STAMINA')]):
        y = 58 + i * 29
        text(label, 30, y, scale=.75)
        rect(116, y + 5, 160, 8, '(R=0.11,G=0.12,B=0.12,A=1)')
        stat = get(name)
        maximum = require(ed.add_get_member_variable_node(unreal.Name('Max' + name), tuning_class_path), 'Maximum ' + name)
        wire(tuning, 'Tuning', maximum, 'self')
        safe = call('KismetMathLibrary:FMax')
        wire(maximum, 'Max' + name, safe, 'A')
        val(safe, 'B', 1)
        fraction = call('KismetMathLibrary:Divide_DoubleDouble')
        wire(stat, name, fraction, 'A')
        wire(safe, 'ReturnValue', fraction, 'B')
        clamp = call('KismetMathLibrary:FClamp')
        wire(fraction, 'ReturnValue', clamp, 'Value')
        val(clamp, 'Min', 0)
        val(clamp, 'Max', 1)
        mul = call('KismetMathLibrary:Multiply_DoubleDouble')
        wire(clamp, 'ReturnValue', mul, 'A')
        val(mul, 'B', 160)
        bar = rect(116, y + 5, 160, 8, colors[i])
        wire(mul, 'ReturnValue', bar, 'ScreenW')
    inside = get('InHabitat')
    status = call('KismetMathLibrary:SelectString')
    val(status, 'A', 'HABITAT / PRESSURIZED')
    val(status, 'B', 'EXTERIOR / SUIT SEALED')
    wire(inside, 'InHabitat', status, 'bPickA')
    label = text('', 30, 182, scale=.72)
    wire(status, 'ReturnValue', label, 'Text')
    clone = get('CloneGeneration')
    identity = call('KismetStringLibrary:BuildString_Int')
    val(identity, 'Prefix', 'CLONE  ')
    wire(clone, 'CloneGeneration', identity, 'InInt')
    identity_text = text('', 20, 210, scale=.65)
    wire(identity, 'ReturnValue', identity_text, 'Text')
    text('E  AIRLOCK / RECOVER     F5  SAVE     F9  LOAD', 20, 230, scale=.65)
    text('F  LIGHT     V  VIEW     SHIFT  SPRINT', 20, 250, scale=.65)
    # Warning supplements the bars; critical suit readings remain reliable.
    oxygen = get('Oxygen')
    low = call('KismetMathLibrary:LessEqual_DoubleDouble')
    wire(oxygen, 'Oxygen', low, 'A')
    val(low, 'B', 20)
    warning = call('KismetMathLibrary:SelectString')
    val(warning, 'A', 'LOW OXYGEN - RETURN TO HABITAT')
    val(warning, 'B', '')
    wire(low, 'ReturnValue', warning, 'bPickA')
    warntext = text('', 20, 278, '(R=1,G=0.3,B=0.12,A=1)', .8)
    wire(warning, 'ReturnValue', warntext, 'Text')
    require(BEL.compile_blueprint(bp), 'HUD compilation: ' + str(list(ed.list_nodes_with_errors())))
    require(LIB.save_loaded_asset(bp, False), 'Save HUD')
    mode = require(unreal.load_asset('/Game/Core/BP_DustfallGameMode'), 'GameMode')
    # This is the historical Phase 3 HUD. Never replace the native Phase 4+
    # exploration HUD unless a caller explicitly asks (ASSIGN_LEGACY_HUD=True).
    if globals().get('ASSIGN_LEGACY_HUD', not hasattr(unreal, 'DustfallExplorationHUD')):
        unreal.get_default_object(mode.generated_class()).set_editor_property('hud_class', bp.generated_class())
        require(LIB.save_loaded_asset(mode, False), 'Save GameMode HUD assignment')
    root = pathlib.Path(unreal.Paths.project_dir())
    (root / 'Saved/Codex/phase3_hud_build.json').write_text(json.dumps({'status': 'built', 'hud': path, 'graph_errors': len(ed.list_nodes_with_errors())}, indent=2))


if __name__ == '__main__':
    build()
