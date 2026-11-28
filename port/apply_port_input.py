#!/usr/bin/env python3
"""Apply stage-02 input/ROM-import sources ONLY to a clean disposable upstream checkout.
No gameplay, save format, original ROM, asset, or Godot modification. No automatic build.
"""
import argparse, hashlib, pathlib, subprocess, sys, tempfile, unittest
PIN = 'dd8fb6d9ea34decedc4e57d4c5deebc008b8adbd'
REL = pathlib.Path('src/GbaMonoGame/MonoGame/InputManager.Gba.cs')
ANCHOR = b'        // Cancel out if opposite directions are pressed'
CALL = b'        inputs |= TouchInputBridge.Snapshot();'
FILES = ('TouchInputBridge.cs', 'AndroidTouchLayout.cs', 'PrivateRomStore.cs')
EXPECTED_BLOB = '1d27020a5ac2e8fd8763a0f91cfd776d19bef95a'

def git(repo,*args): return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
def blob(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def patch(data):
    if data.count(ANCHOR)!=1 or CALL in data: raise ValueError('Missing/duplicate insertion anchor or already patched')
    nl=b'\r\n' if b'\r\n' in data else b'\n'
    return data.replace(ANCHOR,CALL+nl+nl+ANCHOR,1)
def apply(repo):
    if git(repo,'rev-parse','HEAD')!=PIN: raise ValueError('Wrong upstream commit')
    if git(repo,'status','--porcelain'): raise ValueError('Not a clean checkout')
    p=repo/REL; old=p.read_bytes()
    if blob(old)!=EXPECTED_BLOB: raise ValueError('Input source does not match pinned upstream blob')
    new=patch(old); staged=[]
    src=pathlib.Path(__file__).resolve().parent
    for name in FILES:
        dst=p.parent/name
        if dst.exists(): raise FileExistsError(dst)
        staged.append((dst,(src/name).read_bytes()))
    created=[]
    try:
        for dst,data in staged:
            with dst.open('xb') as f: f.write(data)
            created.append(dst)
        p.write_bytes(new)
    except Exception:
        p.write_bytes(old)
        for dst in created: dst.unlink()
        raise
    print('Applied stage-02: 3 source files and one input hook. Build and Android UI wiring remain required.')
class Tests(unittest.TestCase):
    def test_insert_before_conflict_resolution(self):
        old=b'init\n'+ANCHOR+b'\nresolve\nreturn inputs;'
        new=patch(old); self.assertLess(new.index(CALL),new.index(ANCHOR))
        self.assertEqual(new.replace(CALL+b'\n\n',b'',1),old)
    def test_crlf(self):
        old=b'init\r\n'+ANCHOR+b'\r\nend'; self.assertEqual(patch(old).replace(CALL+b'\r\n\r\n',b'',1),old)
    def test_missing_anchor(self):
        with self.assertRaises(ValueError): patch(b'wrong')
    def test_duplicate_anchor(self):
        with self.assertRaises(ValueError): patch(ANCHOR+b'\n'+ANCHOR)
    def test_already_applied(self):
        with self.assertRaises(ValueError): patch(patch(ANCHOR))
    def test_blob(self):
        self.assertEqual(blob(b''),'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
    def test_source_files_exist(self):
        for name in FILES: self.assertTrue((pathlib.Path(__file__).parent/name).is_file())
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--checkout',type=pathlib.Path); p.add_argument('--self-test',action='store_true'); a=p.parse_args()
    if a.self_test: sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1)
    if not a.checkout: p.error('--checkout required')
    apply(a.checkout)
