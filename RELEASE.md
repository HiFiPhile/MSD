MSD-KSU 2.6 is the first signed release of the KernelSU-compatible fork of [MSD by chenxiaolong](https://github.com/chenxiaolong/MSD).

## Changes

- Launch with SELinux Hide enabled using UID and signing-certificate authentication.
- Fix host I/O failures when exporting images from emulated storage.
- Include a Hybrid Mount OverlayFS configuration example and KernelSU unmount-profile instructions.
- Use a persistent fork signing key and enable the fork's module update channel.

## Installation

Download **MSD-KSU-2.6-release.zip** and install it through KernelSU Manager. Follow the [setup guide](https://github.com/HiFiPhile/MSD/blob/v2.6/README.md#kernelsu-setup): install Hybrid Mount, set `com.chiller3.msd` to OverlayFS, and disable module unmounting globally or for MSD, your launcher, and Settings. Reboot afterward. SELinux Hide can remain enabled; SELinux must remain enforcing.

This release has a different APK signing key from upstream MSD and CI debug builds. Android cannot perform an in-place APK update across those keys. Back up any needed settings and remove the previous module/app installation before switching. Subsequent MSD-KSU releases will use this fork key.

## Verification

The module contains native binaries for arm64-v8a, armeabi-v7a, and x86_64. Check its ZIP against `SHA256SUMS`. The bundled release APK is signed; its signer certificate SHA-256 is:

```text
3ef014bc33fa327835b5d664f3adea5f10d221d3121b891d07e7709c6aaabe99
```

The public certificate is attached. The ZIP has a checksum; it does not have a separate detached signature.

## Validation

- Compatibility changes were tested on OnePlus CPH2747, Android 16, KernelSU Next userspace 3.4.0, with SELinux enforcing and SELinux Hide enabled.
- Authentication tests passed, and the host could read the emulated-storage image after the FUSE policy fix.
- This release is built with release shrinking and lint enabled. Packaging verification checks the APK signature, daemon certificate pin, native ABIs, and retained authentication supervisor.
- This exact release-signed APK and the current Hybrid Mount release have not been installed on the test phone; earlier device tests used the upstream-signed UI with a separate supervisor DEX.
