#!/usr/bin/env python3
"""Check a private local APK byte-for-byte against its staging inventory.
No APK is uploaded. Runtime verification and release signing are distinct gates.
"""
import argparse,hashlib,json,pathlib,unittest,zipfile,tempfile,sys

def sha(data):return hashlib.sha256(data).hexdigest()
def verify(apk,inventory):
    expected={"assets/"+k:v for k,v in inventory["files"].items()}
    expected["lib/arm64-v8a/libsoloud.so"]=inventory["native_sha256"]
    with zipfile.ZipFile(apk) as z:
        names=z.namelist()
        if len(set(names))!=len(names):raise ValueError("Duplicate APK ZIP entries")
        if "AndroidManifest.xml" not in names:raise ValueError("No Android manifest")
        for n in names:
            p=pathlib.PurePosixPath(n)
            if p.is_absolute() or ".." in p.parts:raise ValueError("Unsafe ZIP path")
            if p.suffix.lower() in {".gba",".gbc",".rom",".sav",".srm",".app",".keystore",".jks"}:
                raise ValueError("Disallowed private/game source file: "+n)
            if n.startswith("lib/") and len(p.parts)>2 and p.parts[1]!="arm64-v8a":
                raise ValueError("Unexpected ABI: "+n)
        missing=expected.keys()-set(names)
        if missing:raise ValueError("Missing staged entries: "+str(sorted(missing)[:8]))
        for name,digest in expected.items():
            with z.open(name) as f:
                actual=hashlib.file_digest(f,"sha256").hexdigest()
            if actual!=digest:raise ValueError("Changed packaged bytes: "+name)
        unexpected=[n for n in names if n.startswith("assets/Assets/") and not n.endswith("/") and n not in expected]
        if unexpected:raise ValueError("Unexpected staged assets: "+str(unexpected[:8]))
    return {"package_verified":True,"verified_entries":len(expected),"apk_bytes":apk.stat().st_size,
            "full_audio_abi":inventory["native_full_abi"],"release_ready":False}
class Checks(unittest.TestCase):
    def run_fixture(self,alter=None):
        with tempfile.TemporaryDirectory() as d:
            apk=pathlib.Path(d)/"test.apk"
            files={"AndroidManifest.xml":b"synthetic","assets/Assets/test.xnb":b"data","lib/arm64-v8a/libsoloud.so":b"test"}
            inv={"files":{"Assets/test.xnb":sha(b"data")},"native_sha256":sha(b"test"),"native_full_abi":False}
            if alter:alter(files)
            with zipfile.ZipFile(apk,"w") as z:
                for k,v in files.items():z.writestr(k,v)
            return verify(apk,inv)
    def test_match(self):self.assertTrue(self.run_fixture()["package_verified"])
    def test_missing(self):
        with self.assertRaises(ValueError):self.run_fixture(lambda f:f.pop("assets/Assets/test.xnb"))
    def test_changed(self):
        with self.assertRaises(ValueError):self.run_fixture(lambda f:f.update({"assets/Assets/test.xnb":b"wrong"}))
    def test_rom(self):
        with self.assertRaises(ValueError):self.run_fixture(lambda f:f.update({"assets/example.gba":b"fake"}))
    def test_abi(self):
        with self.assertRaises(ValueError):self.run_fixture(lambda f:f.update({"lib/x86/libx.so":b"fake"}))
    def test_extra(self):
        with self.assertRaises(ValueError):self.run_fixture(lambda f:f.update({"assets/Assets/extra.wav":b"fake"}))
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--apk",type=pathlib.Path);p.add_argument("--inventory",type=pathlib.Path)
    a=p.parse_args()
    if a.self_test:sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks)).wasSuccessful() else 1)
    if not a.apk or not a.inventory:p.error("--apk and --inventory required")
    print(json.dumps(verify(a.apk,json.loads(a.inventory.read_text(encoding="utf-8"))),indent=2))
