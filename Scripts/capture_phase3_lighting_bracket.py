"""Bracket actual world exposure with measured baseline/storm captures.

Changes temporary native PostProcessVolume settings, not image pixels. The
visibility helper copies those same settings into its warmed scene capture.
All original settings restored after this thirty-second asynchronous sequence.
"""
import json
import pathlib
import runpy
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir())
OUT = ROOT/'Saved/Codex/Phase3Lighting'
OUT.mkdir(parents=True,exist_ok=True)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
exposure = next(a for a in actors.get_all_level_actors() if isinstance(a,unreal.PostProcessVolume) and 'DF_Phase1_Exposure' in [str(t) for t in a.tags])
original = exposure.get_editor_property('settings')
state = {'index':0}
candidates = [{'name':'EV0_Sun96_Sky2','ev':0.,'sun':96.,'sky':2.},
              {'name':'EV-1_Sun96_Sky2','ev':-1.,'sun':96.,'sky':2.},
              {'name':'EV0_Sun192_Sky3','ev':0.,'sun':192.,'sky':3.}]
report = {'status':'running','candidates':candidates,'results':[],
          'method':'Native world postprocess exposure changes plus matched scene-capture settings; original settings restored.'}


def persist():
    (OUT/'report.json').write_text(json.dumps(report,indent=2))


def finish(status,child):
    report['results'].append({'candidate':candidates[state['index']]['name'],'status':status,'errors':child.get('errors',[])})
    if status.startswith('failed'):
        exposure.set_editor_property('settings',original)
        report['status']='failed'; persist(); return
    state['index']+=1
    if state['index']==len(candidates):
        exposure.set_editor_property('settings',original)
        report['status']='complete; select by visual review'; persist(); return
    start()


def start():
    candidate = candidates[state['index']]
    post = exposure.get_editor_property('settings')
    post.set_editor_property('override_auto_exposure_min_brightness',True)
    post.set_editor_property('override_auto_exposure_max_brightness',True)
    post.set_editor_property('auto_exposure_min_brightness',candidate['ev'])
    post.set_editor_property('auto_exposure_max_brightness',candidate['ev'])
    exposure.set_editor_property('settings',post)
    persist()
    runpy.run_path(str(ROOT/'Scripts/capture_phase3_visibility.py'),init_globals={
        'OUTPUT_SUBDIR':'Phase3Lighting/'+candidate['name'],
        'CAPTURE_WEATHERS':[('baseline',0),('storm',2)],
        'LIGHTING_CANDIDATE':candidate,'ON_COMPLETE':finish})


try:
    start()
except Exception:
    exposure.set_editor_property('settings',original)
    report['status']='failed during setup'; persist()
    raise
