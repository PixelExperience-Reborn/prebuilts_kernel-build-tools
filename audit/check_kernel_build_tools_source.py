#!/usr/bin/env python3
"""Fail-closed source-only audit of legacy kernel build tool prebuilts.

Reads JSON git-tree metadata; does NOT fetch or execute prebuilt executables.
The Android platform and kernel build are distinct source manifests.
"""
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

OLD_SHA = "083e34d8c2c4239be4967172427268c267585951"
OLD_TREE = "aa62325a8144238dfe666777580b08b6cd8db875"
OLD_MANIFEST_BLOB = "7b3374649e0d8b972c89009e75d0eb90f8d621b3"
BLOB_COUNT = 148
TOTAL_BYTES = 130_001_378
BY_GROUP = {
    "root": (5, 11_921),
    "linux-x86/bin": (33, 115_808_313),
    "linux-x86/include": (86, 1_502_820),
    "linux-x86/lib64": (23, 12_676_649),
    "linux-x86/share": (1, 1_675),
}
KEY_BLOBS = {
    "BUILD.bazel": ("100644", "e5465d9878f835b738edb8e029ac7088bfe780cf"),
    "manifest.xml": ("100644", OLD_MANIFEST_BLOB),
    "build-prebuilts.sh": ("100755", "8f8c40a2fab42fe3330400844a6328ded106ce0a"),
    "update-prebuilts.sh": ("100755", "9d77a1ae8bfc47ccc9221e6976546858853848d8"),
    "linux-x86/bin/abidiff": ("100755", "c61152c1c77e5acff2bf6dd38552051426ed5aa5"),
    "linux-x86/bin/avbtool": ("100755", "6af5ec98880d7329e27df91fb3e4cc81f9c5ac52"),
    "linux-x86/bin/certify_bootimg": ("100755", "839134e839aa8f3fe597541ca4b31982e4452b0e"),
    "linux-x86/bin/mkdtboimg.py": ("100755", "55a1555fbcd13e834e2b02656aa9015c4b1d641c"),
    "linux-x86/bin/pahole": ("100755", "b8bcbb050db590a441fe36b02187a1b5bece31f2"),
    "linux-x86/bin/soong_zip": ("100755", "29cd68aa0878fe4c6737ce1f1ee5e087f5d6f1cb"),
    "linux-x86/bin/stginfo": ("100755", "7f6a7796839866af5f8bb5127f33621f0157147e"),
    "linux-x86/lib64/libcrypto.so": ("120000", "34ab95ee0eba8d143ddffa84c2ce28b274b0b94e"),
    "linux-x86/share/avb/testkey_rsa2048.pem":
        ("100644", "867dcff54fcae594321503ec02978929bae1542f"),
}


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args],
                                   text=True).strip()


def group(path):
    pieces = path.split("/")
    return "/".join(pieces[:2]) if pieces[0] == "linux-x86" else "root"


def check_legacy(root, tree_json):
    ref = git(root, "rev-parse", "refs/remotes/origin/seventeen")
    require(ref == OLD_SHA, f"legacy branch moved: {ref}")
    require(git(root, "rev-parse", f"{OLD_SHA}^{{tree}}") == OLD_TREE,
            "archived git tree changed")
    data = json.loads(tree_json.read_text(encoding="utf-8"))
    require(data.get("sha") == OLD_TREE and data.get("truncated") is False,
            "wrong or truncated GitHub historical tree JSON")
    entries = data.get("tree")
    require(isinstance(entries, list), "missing historical git tree entries")
    require(len(entries) == 156, f"legacy tree item count changed: {len(entries)}")
    blobs = {}
    totals = {k: [0, 0] for k in BY_GROUP}
    for entry in entries:
        if entry.get("type") != "blob":
            require(entry.get("type") == "tree",
                    f"unexpected git object: {entry!r}")
            continue
        path, sha, size, mode = (entry.get("path"), entry.get("sha"),
                                 entry.get("size"), entry.get("mode"))
        require(isinstance(path, str) and path not in blobs,
                "bad/duplicate Git tree path")
        require(type(size) is int and size >= 0, f"missing blob size: {path}")
        require(mode in {"100644", "100755", "120000"},
                f"unreviewed file mode: {path}: {mode}")
        key = group(path)
        require(key in totals, f"unexpected payload group: {path}")
        totals[key][0] += 1
        totals[key][1] += size
        blobs[path] = (mode, sha, size)
    require(len(blobs) == BLOB_COUNT, f"legacy blobs changed: {len(blobs)}")
    require(sum(item[2] for item in blobs.values()) == TOTAL_BYTES,
            "historical payload sizes changed")
    require({k: tuple(v) for k, v in totals.items()} == BY_GROUP,
            f"legacy groups changed: {totals}")
    for path, expected in KEY_BLOBS.items():
        require(path in blobs and blobs[path][:2] == expected,
                f"critical archived tool/blob changed: {path}")
    symlinks = [x for x, v in blobs.items() if v[0] == "120000"]
    require(symlinks == ["linux-x86/lib64/libcrypto.so"],
            f"unexpected historical symlinks: {symlinks}")
    require("linux-x86/bin/clang" not in blobs and
            "linux-x86/bin/bazel" not in blobs,
            "unexpected unreviewed compiler or Bazel")
    print("PASS: immutable 2023 legacy SHA and tree with 148 blobs / 130001378 bytes")
    print("PASS: 33 old Linux host executables, 23 lib64, 86 headers, 1 AVB test key")
    print("PASS: critical blob Git SHAs and symlink layout unchanged")


def check_old_kernel_manifest(root):
    # Source-only parse; NEVER run the archived scripts or their host payloads.
    xml = ET.parse(root / "manifest.xml").getroot()
    default = xml.find("default")
    require(default is not None and
            default.get("revision") == "build-tools-2022",
            "historical kernel tool build manifest changed")
    projects = xml.findall("project")
    require(len(projects) == 52,
            f"unexpected old kernel tool build graph: {len(projects)}")
    found = [p for p in projects
             if p.get("path") == "prebuilts/kernel-build-tools"]
    require(len(found) == 1 and
            found[0].get("name") == "kernel/prebuilts/build-tools" and
            found[0].get("revision") ==
            "0fb21fa343b2157c91e21b7ead1e99c1ea82125b",
            "self-pinned build-tools-2022 project changed")
    names = {p.get("path") for p in projects}
    require("external/python/cpython2" in names,
            "historic Python 2 requirement unexpectedly changed")
    script = (root / "build-prebuilts.sh").read_text(encoding="utf-8")
    for needle in ("build/soong/soong_ui.bash", "pahole",
                   "certify_bootimg", "testkey_rsa2048.pem"):
        require(needle in script, f"historical generator changed: {needle}")
    print("PASS: old standalone kernel-build-tools-2022 manifest has 52 projects")
    print("PASS: old Soong generator/AVB TEST key are documented, NOT executed")


def check_aosp17_manifest(root):
    base = ET.parse(root / "aosp17_reference.xml").getroot()
    defaults = base.find("default")
    require(defaults is not None and
            defaults.get("revision") == "refs/tags/android-17.0.0_r1" and
            defaults.get("remote") == "aosp", "wrong AOSP17 base release")
    projects = {p.get("path") or p.get("name"): p.get("name")
                for p in base.findall("project")}
    require("prebuilts/kernel-build-tools" not in projects,
            "historical extra kernel host tool project in AOSP17")
    for path, upstream in {
        "prebuilts/build-tools": "platform/prebuilts/build-tools",
        "prebuilts/tools": "platform/prebuilts/tools",
        "prebuilts/clang/host/linux-x86":
            "platform/prebuilts/clang/host/linux-x86",
        "system/tools/mkbootimg": "platform/system/tools/mkbootimg",
    }.items():
        require(projects.get(path) == upstream,
                f"official Android17 source dependency replaced: {path}")
    subprocess.run([sys.executable,
                    str(root / "tools/validate_aosp17_base_profiles.py")],
                   cwd=root, check=True)
    entry = ET.parse(root / "default.xml").getroot()
    require(len(entry) == 1 and entry[0].tag == "include" and
            entry[0].get("name") == "aosp17_pe_p2_kernel_configs.xml",
            "staged manifest changed; redo source audit before progressing")
    print("PASS: active Android17 source graph excludes the old kernel tool bundle")
    print("PASS: official Android17 build/clang/mkbootimg owners retained")


def main():
    require(len(sys.argv) == 4,
            "usage: check_kernel_build_tools_source.py LEGACY_REPO TREE_JSON A17_MANIFEST")
    legacy = Path(sys.argv[1]).resolve()
    tree_json = Path(sys.argv[2]).resolve()
    manifest = Path(sys.argv[3]).resolve()
    require(legacy.is_dir() and tree_json.is_file() and manifest.is_dir(),
            "expected audit inputs not present")
    check_legacy(legacy, tree_json)
    check_old_kernel_manifest(legacy)
    check_aosp17_manifest(manifest)
    print("PASS: isolated kernel-build-tools source-only audit")
    print("NOT TESTED: binary execution, modern kernel Kbuild/Kleaf, Soong, ABI/VTS, mondrian boot")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, json.JSONDecodeError,
            subprocess.CalledProcessError, ValueError, ET.ParseError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
