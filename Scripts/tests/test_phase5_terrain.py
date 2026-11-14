"""Focused offline checks; no Unreal import, launch, build or asset writes.

Run: <UE Python> -m unittest discover -s Scripts/tests -p test_phase5_terrain.py
Native generator tests are Dustfall.Core.Terrain.Switchback (Lead runs after build).
"""
import copy
import importlib.util
import json
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


class SchemaTests(unittest.TestCase):
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

    def test_capsule_and_turn_clearance_rejected(self):
        for key, value in [('minimum_tread_width_cm',67),('minimum_turn_radius_cm',100)]:
            data=copy.deepcopy(DATA)
            next(f for f in data['features'] if f['type']=='descent')[key]=value
            with self.assertRaises(ValueError): BUILDER.resolve_features(data,(0,40000),ROUTES)


class DryRunOrderingTests(unittest.TestCase):
    def exercise(self, passes, validate_only):
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


if __name__ == '__main__':
    unittest.main()
