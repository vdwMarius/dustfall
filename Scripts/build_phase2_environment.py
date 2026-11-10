"""Build the Phase 2 runtime environment in the currently open foundation map.

Run in Unreal Editor Python after opening L_Dustfall_Foundation. Runtime logic
is Blueprint; Python is used only to author assets and place the director.
"""
import unreal

TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
IN = unreal.EdGraphPinDirection.EGPD_INPUT
OUT = unreal.EdGraphPinDirection.EGPD_OUTPUT
DATA_PATH = '/Game/Data/BP_EnvironmentPhase2Data'
INSTANCE_PATH = '/Game/Data/DA_Environment_Phase2'
DIRECTOR_PATH = '/Game/World/Blueprints/BP_DustfallEnvironmentDirector'
DEFAULTS = {'DayLengthSeconds': 1800.0, 'CalmFogDensity': 0.018,
            'HazeFogDensity': 0.045, 'StormFogDensity': 0.13,
            'WeatherBlendSpeed': 0.2, 'SunIntensity': 15.0,
            'CalmDuration': 180.0, 'HazeDuration': 120.0, 'StormDuration': 60.0,
            'DaySkyIntensity': 0.6, 'NightSkyIntensity': 0.002,
            'StormLightMultiplier': 0.22,
            'WindBaseVolume': 0.15, 'WindStormVolume': 0.8,
            'FogRed': 0.30, 'FogGreen': 0.115, 'FogBlue': 0.055}


def require(v, message):
    if not v:
        raise RuntimeError(message)
    return v


def blueprint(path, parent):
    if LIB.does_asset_exist(path):
        return LIB.load_asset(path)
    folder, name = path.rsplit('/', 1)
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', parent)
    return require(TOOLS.create_asset(name, folder, None, factory), 'Cannot create ' + path)


def member(bp, name, typ):
    existing = [str(n) for n in BEL.list_member_variable_names(bp, False)]
    if name not in existing:
        require(BEL.add_member_variable(bp, name, typ), 'Cannot create variable ' + name)
    BEL.set_blueprint_variable_instance_editable(bp, name, True)


def object_type(cls):
    return BEL.get_object_reference_type(cls)


def pin(node, name, direction):
    for p in node.list_all_pins():
        if str(p.get_pin_name()) == name and p.get_pin_direction() == direction:
            return p
    raise RuntimeError('Missing pin %s on %s (%s)' % (name, node.get_node_title(), [str(p.get_pin_name()) for p in node.list_all_pins()]))


def wire(a, ap, b, bp):
    require(pin(a, ap, OUT).try_create_connection(pin(b, bp, IN)), 'Cannot connect %s to %s' % (ap, bp))


def val(node, name, value):
    require(pin(node, name, IN).set_pin_value(str(value)), 'Cannot set ' + name)


def output(node):
    return str(next(p for p in node.list_all_pins() if p.get_pin_direction() == OUT and str(p.get_pin_type_display_string()) != 'Exec').get_pin_name())


def main():
    real = BEL.get_basic_type_by_name('real')
    integer = BEL.get_basic_type_by_name('int')
    data_bp = blueprint(DATA_PATH, unreal.PrimaryDataAsset)
    previous_fields = [str(n) for n in BEL.list_member_variable_names(data_bp, False)]
    for name in DEFAULTS:
        member(data_bp, name, real)
    require(BEL.compile_blueprint(data_bp), 'Data class compile failed')
    data = LIB.load_asset(INSTANCE_PATH) if LIB.does_asset_exist(INSTANCE_PATH) else None
    new_data = not data
    if new_data:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', data_bp.generated_class())
        data = require(TOOLS.create_asset('DA_Environment_Phase2', '/Game/Data', None, factory), 'Cannot create data asset')
    for name, value in DEFAULTS.items():
        if new_data or name not in previous_fields:
            data.set_editor_property(name, value)
    if not new_data and abs(data.get_editor_property('DayLengthSeconds') - 1200.0) < 0.001:
        data.set_editor_property('DayLengthSeconds', 1800.0)
    # Migrate only untouched values from our initial Phase 2 visual test.
    if not new_data and abs(data.get_editor_property('SunIntensity') - 3.) < .001:
        data.set_editor_property('SunIntensity', 15.)
    if not new_data and abs(data.get_editor_property('DaySkyIntensity') - .35) < .001:
        data.set_editor_property('DaySkyIntensity', .6)
    LIB.save_loaded_asset(data_bp)
    LIB.save_loaded_asset(data)

    bp = blueprint(DIRECTOR_PATH, unreal.Actor)
    for name, typ in [('TimeOfDay', real), ('Weather', integer), ('CurrentFogDensity', real), ('StormIntensity', real), ('WeatherElapsed', real), ('WeatherStage', integer),
                      ('EnvironmentData', object_type(data_bp.generated_class())),
                      ('FogComponent', object_type(unreal.ExponentialHeightFogComponent)),
                      ('SunComponent', object_type(unreal.DirectionalLightComponent)),
                      ('SkyComponent', object_type(unreal.SkyLightComponent))]:
        member(bp, name, typ)
    if 'OnEnvironmentChanged' not in [str(n) for n in BEL.list_event_dispatchers(bp)]:
        require(BEL.add_event_dispatcher(bp, unreal.Name('OnEnvironmentChanged')), 'Cannot add environment notification')
    require(BEL.compile_blueprint(bp), 'Director variables compile failed')
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    sublib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = sub.k2_gather_subobject_data_for_blueprint(bp)
    components = [(h, sublib.get_associated_object(sublib.get_data(h)), str(sublib.get_variable_name(sublib.get_data(h)))) for h in handles]
    wind = next((x for x in components if x[2] == 'WindAudio'), None)
    if not wind:
        handle, reason = sub.add_new_subobject(unreal.AddNewSubobjectParams(handles[0], unreal.AudioComponent, bp))
        if not reason.is_empty():
            raise RuntimeError('Cannot add wind audio: ' + str(reason))
        require(sub.rename_subobject(handle, unreal.Text('WindAudio')), 'Cannot name wind audio')
        require(BEL.compile_blueprint(bp), 'Cannot compile wind component')
        handles = sub.k2_gather_subobject_data_for_blueprint(bp)
        components = [(h, sublib.get_associated_object(sublib.get_data(h)), str(sublib.get_variable_name(sublib.get_data(h)))) for h in handles]
        wind = require(next((x for x in components if x[2] == 'WindAudio'), None), 'Wind component unavailable')
    wind[1].set_editor_property('sound', require(LIB.load_asset('/Game/Audio/Environment/S_WindBed_Phase2'), 'Wind sound missing'))
    wind[1].set_editor_property('auto_activate', True)
    wind[1].set_editor_property('volume_multiplier', 0.15)
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('EnvironmentData', data)
    cdo.set_editor_property('TimeOfDay', 0.65)
    cdo.set_editor_property('Weather', 1)
    cdo.set_editor_property('WeatherStage', 1)
    cdo.set_editor_property('CurrentFogDensity', 0.045)

    ed = unreal.BlueprintGraphEditor.get_graph_editor(BEL.find_event_graph(bp))
    tick = require(ed.find_event_node('ReceiveTick'), 'Default Tick event missing')
    begin = ed.find_event_node('ReceiveBeginPlay')
    keep = [tick, begin]
    ed.remove_nodes([n for n in ed.list_all_nodes() if n not in keep])
    def call(path, x, y):
        n = require(ed.add_call_function_node('/Script/Engine.' + path), 'Cannot add ' + path)
        n.set_node_pos(unreal.IntPoint(x, y))
        return n
    def get(name, x, y, owner=''):
        n = require(ed.add_get_member_variable_node(unreal.Name(name), owner), 'Cannot get ' + name)
        n.set_node_pos(unreal.IntPoint(x, y))
        return n
    def setvar(name, x, y):
        n = require(ed.add_set_member_variable_node(unreal.Name(name)), 'Cannot set ' + name)
        n.set_node_pos(unreal.IntPoint(x, y))
        return n
    def data_get(name, x, y):
        d = get('EnvironmentData', x-200, y)
        n = get(name, x, y, data_bp.generated_class().get_path_name())
        wire(d, output(d), n, 'self')
        return n
    # The clock wraps at one and uses the data asset duration at runtime.
    day = data_get('DayLengthSeconds', 0, 500)
    div = call('KismetMathLibrary:Divide_DoubleDouble', 300, 250)
    day_min = call('KismetMathLibrary:FMax', 100, 600)
    wire(day, output(day), day_min, 'A'); val(day_min, 'B', '1.0')
    wire(tick, 'DeltaSeconds', div, 'A'); wire(day_min, 'ReturnValue', div, 'B')
    clock = get('TimeOfDay', 100, 100)
    add = call('KismetMathLibrary:Add_DoubleDouble', 500, 150)
    wire(clock, output(clock), add, 'A'); wire(div, 'ReturnValue', add, 'B')
    mod = call('KismetMathLibrary:FMod', 700, 150)
    wire(add, 'ReturnValue', mod, 'Dividend'); val(mod, 'Divisor', '1.0')
    set_time = setvar('TimeOfDay', 900, 0)
    wire(mod, 'Remainder', set_time, 'TimeOfDay')
    mult = call('KismetMathLibrary:Multiply_DoubleDouble', 1100, 250)
    wire(set_time, 'Output_Get', mult, 'A'); val(mult, 'B', '360.0')
    cos = call('KismetMathLibrary:DegCos', 1150, 400)
    wire(mult, 'ReturnValue', cos, 'A')
    pitch = call('KismetMathLibrary:Multiply_DoubleDouble', 1250, 400)
    wire(cos, 'ReturnValue', pitch, 'A'); val(pitch, 'B', '90.0')
    rot = call('KismetMathLibrary:MakeRotator', 1300, 250)
    wire(pitch, 'ReturnValue', rot, 'Pitch')
    sun = get('SunComponent', 1300, 450)
    set_rot = call('SceneComponent:K2_SetWorldRotation', 1500, 0)
    wire(set_time, 'then', set_rot, 'execute'); wire(sun, output(sun), set_rot, 'self'); wire(rot, 'ReturnValue', set_rot, 'NewRotation')
    negative = call('KismetMathLibrary:Multiply_DoubleDouble', 1300, 650)
    wire(cos, 'ReturnValue', negative, 'A'); val(negative, 'B', '-1.0')
    daylight = call('KismetMathLibrary:FClamp', 1500, 650)
    wire(negative, 'ReturnValue', daylight, 'Value'); val(daylight, 'Min', '0.0'); val(daylight, 'Max', '1.0')
    sun_strength = data_get('SunIntensity', 1300, 900)
    sun_scaled = call('KismetMathLibrary:Multiply_DoubleDouble', 1700, 650)
    wire(daylight, 'ReturnValue', sun_scaled, 'A'); wire(sun_strength, output(sun_strength), sun_scaled, 'B')
    storm_light = data_get('StormLightMultiplier', 1600, 3400)
    storm_current = get('StormIntensity', 1600, 3650)
    storm_light_lerp = call('KismetMathLibrary:Lerp', 1850, 3400)
    val(storm_light_lerp, 'A', '1.0'); wire(storm_light, output(storm_light), storm_light_lerp, 'B'); wire(storm_current, output(storm_current), storm_light_lerp, 'Alpha')
    sun_dim = call('KismetMathLibrary:Multiply_DoubleDouble', 2050, 3400)
    wire(sun_scaled, 'ReturnValue', sun_dim, 'A'); wire(storm_light_lerp, 'ReturnValue', sun_dim, 'B')
    light = call('LightComponent:SetIntensity', 1750, 0)
    wire(set_rot, 'then', light, 'execute'); wire(sun, output(sun), light, 'self'); wire(sun_dim, 'ReturnValue', light, 'NewIntensity')
    # Two selects select one of three authored fog densities.
    weather = get('Weather', 500, 900)
    ge1 = call('KismetMathLibrary:GreaterEqual_IntInt', 700, 850)
    ge2 = call('KismetMathLibrary:GreaterEqual_IntInt', 700, 1050)
    wire(weather, output(weather), ge1, 'A'); val(ge1, 'B', '1')
    wire(weather, output(weather), ge2, 'A'); val(ge2, 'B', '2')
    calm = data_get('CalmFogDensity', 400, 1250)
    haze = data_get('HazeFogDensity', 400, 1450)
    storm = data_get('StormFogDensity', 400, 1650)
    select1 = call('KismetMathLibrary:SelectFloat', 950, 1100)
    wire(ge1, 'ReturnValue', select1, 'bPickA'); wire(haze, output(haze), select1, 'A'); wire(calm, output(calm), select1, 'B')
    select2 = call('KismetMathLibrary:SelectFloat', 1150, 1050)
    wire(ge2, 'ReturnValue', select2, 'bPickA'); wire(storm, output(storm), select2, 'A'); wire(select1, 'ReturnValue', select2, 'B')
    fog_current = get('CurrentFogDensity', 1150, 1350)
    speed = data_get('WeatherBlendSpeed', 1150, 1550)
    interp = call('KismetMathLibrary:FInterpTo', 1450, 1200)
    wire(fog_current, output(fog_current), interp, 'Current'); wire(select2, 'ReturnValue', interp, 'Target')
    wire(tick, 'DeltaSeconds', interp, 'DeltaTime'); wire(speed, output(speed), interp, 'InterpSpeed')
    set_current = setvar('CurrentFogDensity', 1950, 0)
    sky_ref = get('SkyComponent', 1900, -1000)
    day_sky = data_get('DaySkyIntensity', 1400, -1000)
    night_sky = data_get('NightSkyIntensity', 1400, -1250)
    sky_lerp = call('KismetMathLibrary:Lerp', 1700, -1000)
    wire(night_sky, output(night_sky), sky_lerp, 'A'); wire(day_sky, output(day_sky), sky_lerp, 'B')
    wire(daylight, 'ReturnValue', sky_lerp, 'Alpha')
    sky_set = call('SkyLightComponent:SetIntensity', 1950, -200)
    sky_dim = call('KismetMathLibrary:Multiply_DoubleDouble', 2050, -1200)
    wire(sky_lerp, 'ReturnValue', sky_dim, 'A'); wire(storm_light_lerp, 'ReturnValue', sky_dim, 'B')
    wire(light, 'then', sky_set, 'execute'); wire(sky_ref, output(sky_ref), sky_set, 'self')
    wire(sky_dim, 'ReturnValue', sky_set, 'NewIntensity')
    wire(sky_set, 'then', set_current, 'execute'); wire(interp, 'ReturnValue', set_current, 'CurrentFogDensity')
    fog = get('FogComponent', 1650, 1000)
    set_fog = call('ExponentialHeightFogComponent:SetFogDensity', 2150, 0)
    wire(set_current, 'then', set_fog, 'execute'); wire(fog, output(fog), set_fog, 'self'); wire(set_current, 'Output_Get', set_fog, 'Value')
    intensity_target = call('KismetMathLibrary:SelectFloat', 1500, 1850)
    wire(ge2, 'ReturnValue', intensity_target, 'bPickA'); val(intensity_target, 'A', '1.0'); val(intensity_target, 'B', '0.0')
    intensity_current = get('StormIntensity', 1300, 2050)
    wind_interp = call('KismetMathLibrary:FInterpTo', 1700, 1800)
    wire(intensity_current, output(intensity_current), wind_interp, 'Current'); wire(intensity_target, 'ReturnValue', wind_interp, 'Target')
    wire(tick, 'DeltaSeconds', wind_interp, 'DeltaTime'); wire(speed, output(speed), wind_interp, 'InterpSpeed')
    set_intensity = setvar('StormIntensity', 2350, 0)
    wire(set_fog, 'then', set_intensity, 'execute'); wire(wind_interp, 'ReturnValue', set_intensity, 'StormIntensity')
    wind_base = data_get('WindBaseVolume', 1750, 2100)
    wind_storm = data_get('WindStormVolume', 1950, 2350)
    wind_add = call('KismetMathLibrary:Lerp', 2150, 1700)
    wire(wind_base, output(wind_base), wind_add, 'A'); wire(wind_storm, output(wind_storm), wind_add, 'B')
    wire(set_intensity, 'Output_Get', wind_add, 'Alpha')
    wind_component = get('WindAudio', 2150, 1900)
    set_volume = call('AudioComponent:SetVolumeMultiplier', 2550, 0)
    wire(set_intensity, 'then', set_volume, 'execute'); wire(wind_component, output(wind_component), set_volume, 'self'); wire(wind_add, 'ReturnValue', set_volume, 'NewVolumeMultiplier')
    # Reduce the otherwise self-lit orange fog at night, keeping the amber home
    # lamp as a distinct local landmark rather than bright global fill.
    fog_color = call('KismetMathLibrary:MakeColor', 2800, 700)
    for name, channel, yy in [('FogRed', 'R', 0), ('FogGreen', 'G', 250), ('FogBlue', 'B', 500)]:
        channel_value = data_get(name, 2300, 2600 + yy)
        scaled = call('KismetMathLibrary:Multiply_DoubleDouble', 2550, 2600 + yy)
        wire(channel_value, output(channel_value), scaled, 'A')
        floor = call('KismetMathLibrary:FMax', 2200, 2900 + yy)
        wire(daylight, 'ReturnValue', floor, 'A'); val(floor, 'B', '.015')
        wire(floor, 'ReturnValue', scaled, 'B'); wire(scaled, 'ReturnValue', fog_color, channel)
    val(fog_color, 'A', '1.0')
    fog_color_set = call('ExponentialHeightFogComponent:SetFogInscatteringColor', 2800, 0)
    wire(set_volume, 'then', fog_color_set, 'execute'); wire(fog, output(fog), fog_color_set, 'self')
    wire(fog_color, 'ReturnValue', fog_color_set, 'Value')
    changed = require(ed.create_node_from_name('Default|CallOnEnvironmentChanged', unreal.Vector2D(3100, 0), []), 'Cannot create environment notification')
    wire(fog_color_set, 'then', changed, 'execute')
    # Calm -> haze -> storm -> haze cycle. Manual SetWeather remains active
    # until the next scheduled transition; durations are asset-authored.
    elapsed = get('WeatherElapsed', -1800, -250)
    elapsed_add = call('KismetMathLibrary:Add_DoubleDouble', -1600, -250)
    wire(elapsed, output(elapsed), elapsed_add, 'A'); wire(tick, 'DeltaSeconds', elapsed_add, 'B')
    set_elapsed = setvar('WeatherElapsed', -1400, -100)
    wire(tick, 'then', set_elapsed, 'execute'); wire(elapsed_add, 'ReturnValue', set_elapsed, 'WeatherElapsed')
    calm_duration = data_get('CalmDuration', -1800, -1000)
    haze_duration = data_get('HazeDuration', -1800, -1250)
    storm_duration = data_get('StormDuration', -1800, -1500)
    dur1 = call('KismetMathLibrary:SelectFloat', -1300, -1000)
    wire(ge1, 'ReturnValue', dur1, 'bPickA'); wire(haze_duration, output(haze_duration), dur1, 'A'); wire(calm_duration, output(calm_duration), dur1, 'B')
    dur2 = call('KismetMathLibrary:SelectFloat', -1100, -1000)
    wire(ge2, 'ReturnValue', dur2, 'bPickA'); wire(storm_duration, output(storm_duration), dur2, 'A'); wire(dur1, 'ReturnValue', dur2, 'B')
    due = call('KismetMathLibrary:GreaterEqual_DoubleDouble', -900, -800)
    wire(set_elapsed, 'Output_Get', due, 'A'); wire(dur2, 'ReturnValue', due, 'B')
    branch = require(ed.add_branch_node(), 'Cannot create weather transition branch')
    branch.set_node_pos(unreal.IntPoint(-700, -100))
    wire(set_elapsed, 'then', branch, 'execute'); wire(due, 'ReturnValue', branch, 'Condition')
    wire(branch, 'else', set_time, 'execute')
    reset_elapsed = setvar('WeatherElapsed', -500, -300)
    wire(branch, 'then', reset_elapsed, 'execute'); val(reset_elapsed, 'WeatherElapsed', '0.0')
    stage = get('WeatherStage', -700, -600)
    increment = call('KismetMathLibrary:Add_IntInt', -500, -650)
    wire(stage, output(stage), increment, 'A'); val(increment, 'B', '1')
    wrap = call('KismetMathLibrary:Percent_IntInt', -300, -650)
    wire(increment, 'ReturnValue', wrap, 'A'); val(wrap, 'B', '4')
    set_stage = setvar('WeatherStage', -250, -300)
    wire(reset_elapsed, 'then', set_stage, 'execute'); wire(wrap, 'ReturnValue', set_stage, 'WeatherStage')
    last_stage = call('KismetMathLibrary:GreaterEqual_IntInt', -100, -700)
    wire(set_stage, 'Output_Get', last_stage, 'A'); val(last_stage, 'B', '3')
    select_stage = call('KismetMathLibrary:SelectInt', 100, -700)
    wire(last_stage, 'ReturnValue', select_stage, 'bPickA'); val(select_stage, 'A', '1'); wire(set_stage, 'Output_Get', select_stage, 'B')
    set_weather = setvar('Weather', 0, -300)
    wire(set_stage, 'then', set_weather, 'execute'); wire(select_stage, 'ReturnValue', set_weather, 'Weather')
    wire(set_weather, 'then', set_time, 'execute')
    require(BEL.compile_blueprint(bp), 'Director event graph failed compilation: %s' % list(ed.list_nodes_with_errors()))

    # Remove earlier generated variants, then compile before allocating the same
    # public names. Otherwise the stale skeleton UFunctions force _0 suffixes.
    for graph_name in list(BEL.list_graph_names(bp)):
        name = str(graph_name)
        if any(name == f or name.startswith(f + '_') for f in ['SetWeather', 'SetTimeOfDay', 'GetEnvironmentState']):
            BEL.remove_function_graph(bp, name)
    require(BEL.compile_blueprint(bp), 'Cannot clear old generated function names')
    # Callable controls are normal Blueprint functions and update on next tick.
    for function, variable, typ in [('SetWeather', 'Weather', integer), ('SetTimeOfDay', 'TimeOfDay', real)]:
        fed = unreal.BlueprintGraphEditor.create_and_edit_function_graph(bp, function)
        require(fed.add_graph_input_parameter(unreal.Name('Value'), typ), 'Cannot add function input')
        entry = next(n for n in fed.list_all_nodes() if any(str(p.get_pin_name()) == 'Value' and p.get_pin_direction() == OUT for p in n.list_all_pins()))
        setter = require(fed.add_set_member_variable_node(unreal.Name(variable)), 'Cannot create setter')
        clamp = require(fed.add_call_function_node('/Script/Engine.KismetMathLibrary:' + ('Clamp' if variable == 'Weather' else 'FClamp')), 'Cannot create input clamp')
        val(clamp, 'Min', '0'); val(clamp, 'Max', '2' if variable == 'Weather' else '1')
        wire(entry, 'then', setter, 'execute'); wire(entry, 'Value', clamp, 'Value'); wire(clamp, 'ReturnValue', setter, variable)
        if variable == 'Weather':
            reset = require(fed.add_set_member_variable_node(unreal.Name('WeatherElapsed')), 'Cannot reset weather age')
            phase = require(fed.add_set_member_variable_node(unreal.Name('WeatherStage')), 'Cannot set weather stage')
            wire(setter, 'then', reset, 'execute'); val(reset, 'WeatherElapsed', '0.0')
            wire(reset, 'then', phase, 'execute'); wire(setter, 'Output_Get', phase, 'WeatherStage')
    query = unreal.BlueprintGraphEditor.create_and_edit_function_graph(bp, 'GetEnvironmentState')
    result = None
    for name, typ in [('Weather', integer), ('TimeOfDay', real), ('StormIntensity', real)]:
        result = require(query.add_graph_output_parameter(unreal.Name(name), typ), 'Cannot create state output')
    entry_pin = query.find_graph_entry_pin()
    require(entry_pin.try_create_connection(pin(result, 'execute', IN)), 'Cannot wire state return')
    for name in ['Weather', 'TimeOfDay', 'StormIntensity']:
        n = query.add_get_member_variable_node(unreal.Name(name))
        wire(n, output(n), result, name)
    require(BEL.compile_blueprint(bp), 'Director function compilation failed')
    cdo = unreal.get_default_object(bp.generated_class())
    cdo.set_editor_property('EnvironmentData', data)
    cdo.set_editor_property('TimeOfDay', 0.65)
    cdo.set_editor_property('Weather', 1)
    cdo.set_editor_property('WeatherStage', 3)
    cdo.set_editor_property('CurrentFogDensity', 0.045)
    require(LIB.save_loaded_asset(bp, False), 'Cannot save director')
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    fog_actor = require(next((a for a in actors if isinstance(a, unreal.ExponentialHeightFog)), None), 'No fog actor')
    sun_actor = require(next((a for a in actors if isinstance(a, unreal.DirectionalLight)), None), 'No sun actor')
    sky_actor = require(next((a for a in actors if isinstance(a, unreal.SkyLight)), None), 'No sky actor')
    directors = [a for a in actors if a.get_class() == bp.generated_class()]
    director = directors[0] if directors else unreal.EditorLevelLibrary.spawn_actor_from_class(bp.generated_class(), unreal.Vector())
    director.modify()
    director.set_actor_label('Dustfall Environment Director')
    director.set_editor_property('is_spatially_loaded', False)
    director.set_editor_property('FogComponent', fog_actor.get_component_by_class(unreal.ExponentialHeightFogComponent))
    director.set_editor_property('SunComponent', sun_actor.get_component_by_class(unreal.DirectionalLightComponent))
    director.set_editor_property('SkyComponent', sky_actor.get_component_by_class(unreal.SkyLightComponent))
    for a in [fog_actor, sun_actor, sky_actor]:
        a.modify()
        a.set_editor_property('is_spatially_loaded', False)
        for c in a.get_components_by_class(unreal.SceneComponent):
            c.modify()
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_actor.get_component_by_class(unreal.SkyLightComponent).set_editor_property('real_time_capture', True)
    require(unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level(), 'Cannot save level')
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    unreal.log('DUSTFALL Phase 2 environment built')


if __name__ == '__main__':
    main()
