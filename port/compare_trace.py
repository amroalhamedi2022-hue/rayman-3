#!/usr/bin/env python3
"""Compare explicitly normalized private traces without inferring alignments or offsets."""
import argparse,json,math,pathlib,sys,unittest
EXACT=("schema","tick","game_frame","map_id","input_mask","action_id","animation_id",
       "animation_frame","animation_timer","hit_points","flip_x","flip_y","paused")
FLOAT=("x","y","vx","vy","camera_x","camera_y")
def validate(rows):
    if not rows: raise ValueError("Empty trace")
    for i,r in enumerate(rows):
        if not isinstance(r,dict): raise ValueError("Invalid row")
        missing=set(EXACT+FLOAT)-r.keys()
        if missing: raise ValueError(f"Tick {i}: missing {sorted(missing)}")
        if r["schema"]!=1 or r["tick"]!=i: raise ValueError(f"Tick {i}: invalid schema or alignment")
        for k in FLOAT:
            if isinstance(r[k],bool) or not isinstance(r[k],(int,float)) or not math.isfinite(r[k]):
                raise ValueError(f"Tick {i}: invalid numeric {k}")
        for k in ("flip_x","flip_y","paused"):
            if type(r[k]) is not bool: raise ValueError(f"Tick {i}: invalid boolean {k}")
        for k in set(EXACT)-{"flip_x","flip_y","paused"}:
            if type(r[k]) is not int: raise ValueError(f"Tick {i}: invalid integer {k}")
def compare(reference,candidate,tolerance=0.0):
    validate(reference);validate(candidate)
    if not math.isfinite(tolerance) or tolerance<0: raise ValueError("Invalid tolerance")
    counts={};first=None
    if len(reference)!=len(candidate):
        counts["length"]=1;first={"field":"length","reference":len(reference),"candidate":len(candidate)}
    for i,(a,b) in enumerate(zip(reference,candidate)):
        for key in EXACT+FLOAT:
            different=abs(a[key]-b[key])>tolerance if key in FLOAT else a[key]!=b[key]
            if different:
                counts[key]=counts.get(key,0)+1
                if first is None: first={"tick":i,"field":key,"reference":a[key],"candidate":b[key]}
    return {"pass":not counts,"reference_ticks":len(reference),"candidate_ticks":len(candidate),
            "coordinate_speed_tolerance":tolerance,"mismatch_counts":counts,"first_mismatch":first}
def load(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]
def fixture():
    return {**{k:0 for k in EXACT},**{k:0.0 for k in FLOAT},"schema":1,"flip_x":False,"flip_y":False,"paused":False}
class Tests(unittest.TestCase):
    def test_equal(self): self.assertTrue(compare([fixture()],[fixture()])["pass"])
    def test_position(self):
        a=fixture();b=fixture();b["x"]=0.125
        self.assertFalse(compare([a],[b])["pass"])
        self.assertTrue(compare([a],[b],0.125)["pass"])
    def test_action_exact(self):
        a=fixture();b=fixture();b["action_id"]=1
        self.assertFalse(compare([a],[b],100)["pass"])
    def test_missing(self):
        a=fixture();del a["animation_timer"]
        with self.assertRaises(ValueError): compare([a],[fixture()])
    def test_length(self):
        a=fixture();b=fixture();b["tick"]=1
        self.assertFalse(compare([a],[a,b])["pass"])
    def test_alignment(self):
        a=fixture();a["tick"]=1
        with self.assertRaises(ValueError): compare([a],[fixture()])
    def test_nan(self):
        a=fixture();a["x"]=float("nan")
        with self.assertRaises(ValueError): compare([a],[fixture()])
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--reference",type=pathlib.Path);p.add_argument("--candidate",type=pathlib.Path)
    p.add_argument("--tolerance",type=float,default=0.0)
    a=p.parse_args()
    if a.self_test: sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1)
    if not a.reference or not a.candidate: p.error("--reference and --candidate required")
    result=compare(load(a.reference),load(a.candidate),a.tolerance)
    print(json.dumps(result,indent=2));sys.exit(0 if result["pass"] else 1)
