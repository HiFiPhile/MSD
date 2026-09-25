#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Verify a tagged release module and prepare its public verification assets."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"v[0-9]+\.[0-9]+", sys.argv[1]):
        raise SystemExit("Expected a vMAJOR.MINOR release tag")
    version = sys.argv[1][1:]
    major, minor = map(int, version.split("."))
    output = Path("app/build/distributions/release")
    module = output / f"MSD-KSU-{version}-release.zip"
    expected_pin = Path("release-signing-certificate.sha256").read_text().strip()
    assert re.fullmatch(r"[0-9a-f]{64}", expected_pin)
    with zipfile.ZipFile(module) as archive:
        props = dict(line.split("=", 1) for line in archive.read("module.prop").decode().splitlines() if "=" in line)
        assert props["id"] == "com.chiller3.msd"
        assert props["name"] == "MSD-KSU"
        assert props["version"] == "v" + version
        assert int(props["versionCode"]) == (major << 16) | (minor << 8)
        assert props["updateJson"] == "https://github.com/HiFiPhile/MSD/raw/master/app/module/updates/release/info.json"
        assert archive.read("client-cert.sha256").decode().strip() == expected_pin
        config = tomllib.loads(archive.read("examples/hybrid-mount.toml").decode())
        assert config["rules"]["com.chiller3.msd"]["default_mode"] == "overlay"
        for abi in ["arm64-v8a", "armeabi-v7a", "x86_64"]:
            assert archive.read("msd-tool." + abi).startswith(b"\x7fELF")
        with tempfile.TemporaryDirectory() as temporary:
            apk = Path(temporary) / "app-release.apk"
            apk.write_bytes(archive.read("system/priv-app/com.chiller3.msd/app-release.apk"))
            sdk = Path(os.environ["ANDROID_HOME"]) / "build-tools/37.0.0"
            verified = subprocess.check_output([str(sdk / "apksigner"), "verify", "--print-certs", str(apk)], text=True)
            # Recent SDKs include signer SDK ranges in the output prefix.
            # Require every reported certificate digest to match our one key.
            actual_pins = re.findall(r"certificate SHA-256 digest:\s*([0-9a-fA-F]{64})", verified)
            assert actual_pins, f"No signing certificate digest in apksigner output:\n{verified}"
            assert {pin.lower() for pin in actual_pins} == {expected_pin}, "APK signer differs from daemon pin"
            with zipfile.ZipFile(apk) as app:
                assert any(b"Lcom/chiller3/msd/standalone/AuthenticatedDaemon;" in app.read(name)
                           for name in app.namelist() if re.fullmatch(r"classes[0-9]*\.dex", name)), "Supervisor removed by shrinking"
    for name in ["release-signing-certificate.pem", "release-signing-certificate.sha256"]:
        shutil.copyfile(name, output / name)
    digest = hashlib.sha256(module.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {module.name}\n")
    print(f"Verified {module.name}: metadata, three ABIs, config, APK signature, pin, and supervisor")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
