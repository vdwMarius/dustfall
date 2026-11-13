"""Small offline geometry/determinism tests; does not launch/import Unreal."""
import json
import math
import pathlib
import random
import runpy
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
PURE=runpy.run_path(str(ROOT/'Scripts/phase5_dressing_rules.py'))


def inputs():
    rules=json.loads((ROOT/'Scripts/Data/world_dressing_phase5.json').read_text())
    features={'features':[], 'resolved':{'discs_cm':[[0,0,3300]], 'routes':[
        {'line_cm':[[-9000,-6000],[-5000,-6000]]}]},'protection':{'route_inner_cm':850}}
    paths=[dict(width_cm=350,polyline_cm=[[-8000,5000,0],[0,5000,0],[8000,5000,0]])]
    return PURE['Inputs'](rules,features,paths,[-10000,-10000,10000,10000],8,bytes(range(64)),bytes(64))


class DressingRulesTests(unittest.TestCase):
    def test_raw_mask_orientation_and_inclusive_extrema(self):
        data=inputs()
        self.assertEqual(data.mask(data.path_mask,-10000,-10000),0)
        self.assertEqual(data.mask(data.path_mask,10000,10000),63)
        self.assertEqual(data.mask(data.path_mask,-10000,10000),56)
        self.assertEqual(data.mask(data.path_mask,10000,-10000),7)

    def test_corridor_end_caps_and_large_footprints(self):
        data=inputs()
        self.assertFalse(data.clear(0,5100,0))
        self.assertFalse(data.clear(8200,5000,100))
        self.assertTrue(data.clear(8200,5000,0))
        self.assertFalse(data.clear(0,5600,500))
        self.assertTrue(data.clear(0,5600,400))
        self.assertFalse(data.clear(-7000,-5200,0)) # Original route is wider.
        self.assertFalse(data.clear(4000,0,800)) # Protected disc + mesh.

    def test_segment_index_matches_brute_force(self):
        data=inputs(); rng=random.Random(2042)
        for _ in range(1000):
            x,y=rng.uniform(-10000,10000),rng.uniform(-10000,10000);radius=rng.uniform(0,1800)
            expected=(-10000+radius<=x<=10000-radius and -10000+radius<=y<=10000-radius
                and math.hypot(x,y)>=3300+radius
                and all(PURE['project'](x,y,line)[0]>=half+radius for line,half in data.corridors))
            self.assertEqual(data.clear(x,y,radius),expected)

    def test_seeded_candidates_repeat(self):
        first=list(PURE['candidates'](inputs()));second=list(PURE['candidates'](inputs()))
        self.assertEqual(first,second)
        self.assertGreater(len(first),0)
        altered=inputs();altered.rules['seed']+=1
        self.assertNotEqual(first,list(PURE['candidates'](altered)))

    def test_tilted_tall_mesh_expands_clearance(self):
        bounds=([0,0,500],[100,100,500])
        upright=PURE['footprint'](bounds,[1,1,6])[0]
        leaning=PURE['footprint'](bounds,[1,1,6],13,0)[0]
        self.assertGreater(leaning,upright+1000)

    def test_corrupt_mask_rejected(self):
        with self.assertRaises(ValueError):PURE['Inputs']({}, {}, [], [0,0,1,1],8,b'',b'')


if __name__=='__main__':unittest.main()
