"""Summarize Phase 3 profiler CSVs with measured resolution/PCG context.

Standalone Python, no Unreal or pandas. Uses the established Phase 2 CSV parser.
"""
import argparse
import json
import pathlib
import runpy

ROOT=pathlib.Path(__file__).resolve().parent.parent
summarize=runpy.run_path(str(ROOT/'Scripts/summarize_phase2_csv.py'))['summarize']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',type=pathlib.Path,default=ROOT/'Saved/Codex/profile_phase3.json')
    parser.add_argument('--output',type=pathlib.Path,required=True)
    parser.add_argument('--discard',type=int,default=0)
    args=parser.parse_args()
    profile=json.loads(args.profile.read_text(encoding='utf-8'))
    directory=pathlib.Path(profile.get('csv_directory',ROOT/'Saved/Profiling/CSV'))
    result={'status':'complete','profile_status':profile.get('status'),
            'scope':profile.get('scope'),'settings':profile.get('settings'),
            'viewport_size':profile.get('viewport_size'),'runtime_render_cvars':profile.get('runtime_render_cvars'),
            'captures':[],'errors':list(profile.get('errors',[])),
            'limits':'PIE visibility is not asserted. Actual viewport dimensions may differ from1080p. Loaded instances are not rendered/visible-instance counts. Stationary cases exclude teleports, and do not establish packaged traversal or representative hardware60FPS.'}
    for case in profile.get('cases',[]):
        path=directory/case['csv']
        if not path.exists() and pathlib.Path(str(path)+'.gz').exists(): path=pathlib.Path(str(path)+'.gz')
        if not path.exists():
            result['errors'].append('Missing CSV: '+str(path)); continue
        entry=summarize(path,args.discard)
        entry.update(name=case['name'],viewport_size=case.get('viewport_size',profile.get('viewport_size')),
                     loaded_pcg=case.get('loaded_pcg'),
                     game_delta_median_ms=case.get('game_delta_median_ms'),
                     game_delta_p95_ms=case.get('game_delta_p95_ms'))
        if not entry['timings_ms']: result['errors'].append('No valid CSV timing rows: '+str(path))
        result['captures'].append(entry)
    if result['errors'] or profile.get('status')!='completed' or len(result['captures'])!=7: result['status']='incomplete'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
