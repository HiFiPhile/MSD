# MSD-KSU

<img src="app/images/icon.svg" alt="app icon" width="72" />

MSD-KSU is a KernelSU-compatible fork of [MSD by chenxiaolong](https://github.com/chenxiaolong/MSD), an Android app for emulating CD-ROM and disk devices over USB.

This fork maintains compatibility with KernelSU's SELinux Hide feature and fixes host I/O failures for images on emulated storage. SELinux remains enforcing. The app and module are installed through KernelSU; their package/module ID remains `com.chiller3.msd`.

Fork-specific support and compatibility work belong in [HiFiPhile/MSD](https://github.com/HiFiPhile/MSD/issues). The original project and its authors retain credit for MSD.

<img src="app/images/light.png" alt="light mode screenshot" width="200" /> <img src="app/images/dark.png" alt="dark mode screenshot" width="200" />

## Features

* Supports Android 11 and newer
* Supports emulating multiple mass storage devices at the same time
  * Including mixing and matching CD-ROM and disk devices
* Does not interfere with ADB, MTP, or any other normal USB functionality

## Limitations

* The device must use configfs for configuring USB gadgets
  * Run `ls /config/usb_gadget/g1` as root to check that the directory exists.
* The device's kernel must be compiled with support for the mass storage USB gadget
  * Run `zcat /proc/config.gz | grep CONFIG_USB_CONFIGFS_MASS_STORAGE` as root and check that it is `=y`.
* Only local files are supported
  * Android's Storage Access Framework allows cloud providers to present a file as a local file using FUSE (specifically, via `StorageManager.openProxyFileDescriptor`). Unfortunately, even for the few cloud providers that support this, these files cannot be used because Android's implementation of this mechanism does not allow files to be reopened. Setting up a mass storage device requires reopening the file because the kernel has no way to accept an already open file descriptor.

## KernelSU setup

### 1. Install Hybrid Mount

Download the metamodule ZIP from [Hybrid Mount releases](https://github.com/Hybrid-Mount/meta-hybrid_mount/releases) and install it through KernelSU Manager's module installer. Follow the metamodule's installation prompts and reboot when required. Use Hybrid Mount as the active mounting metamodule.

### 2. Install MSD-KSU

Download an MSD-KSU module ZIP from this fork's [releases](https://github.com/HiFiPhile/MSD/releases), when available, or a successful [CI build](https://github.com/HiFiPhile/MSD/actions/workflows/ci.yml). For CI builds, download the `MSD-KSU-debug-module` artifact, extract its outer archive, and install the contained `MSD-KSU-*-debug.zip` through KernelSU Manager.

CI builds use a debug signing key and are intended for testing. See [signing and updates](#signing-and-updates) before replacing an existing installation.

### 3. Set MSD to OverlayFS mode

In Hybrid Mount's module configuration, set `com.chiller3.msd` to **OverlayFS**. The equivalent file configuration is in `/data/adb/hybrid-mount/config.toml`:

```toml
[rules."com.chiller3.msd"]
default_mode = "overlay"
```

The quotes are required because the module ID contains dots. Merge this table into the existing configuration, or edit the table if it already exists. Other modules can retain their current mount modes. Existing path-specific rules for MSD take precedence; update any that would route its files away from OverlayFS.

A ready-to-copy module override is provided in [`examples/hybrid-mount.toml`](examples/hybrid-mount.toml). The module setting is `default_mode = "overlay"`; Hybrid Mount's separate `overlay_mode` setting selects its backing storage (`ext4` or `tmpfs`). Configuration changes take effect after reboot. See the [Hybrid Mount configuration reference](https://github.com/Hybrid-Mount/meta-hybrid_mount#configuration).

### 4. Keep MSD visible to the apps that need it

Choose either KernelSU configuration:

- **Global:** turn off **Umount modules by default** in KernelSU Manager. Check that existing per-app profiles do not explicitly enable **Umount modules** for MSD, your launcher, or Settings.
- **Per app:** leave the global setting enabled, then use custom app profiles with **Umount modules** disabled for MSD-KSU (`com.chiller3.msd`), your active launcher, and Android Settings (`com.android.settings`, or your ROM's Settings package). Enable the manager's system-app filter to find Settings if needed.

The per-app option keeps the existing policy for other apps. Profile changes do not require granting these apps root access. The launcher and Settings need visibility of MSD's module-mounted APK to load its app entry and resources. See [KernelSU's non-root app profiles](https://kernelsu.org/guide/app-profile.html#non-root-profile).

**SELinux Hide can stay enabled.** It is separate from the **Umount modules** setting. Keep SELinux enforcing.

### 5. Reboot and export an image

Reboot after configuring Hybrid Mount and the app profiles. Open MSD-KSU, add a local CD-ROM or disk image, then apply the settings. If the launcher entry is missing or has a blank icon, recheck the launcher profile and restart the launcher after the reboot.

MSD-KSU does not need to run in the background. Configured USB mass-storage devices remain available until disabled or the phone reboots.

## Tested configuration

- Device model: OnePlus CPH2747
- Android version: 16
- KernelSU Next userspace version: 3.4.0
- Base MSD version: 2.5
- SELinux: enforcing
- SELinux Hide: enabled

The authentication changes were verified after reboot, and adding the FUSE descriptor permission restored host access to an image on emulated storage. The Hybrid Mount setup above is configuration guidance; the current Hybrid Mount release has not been newly installed or validated as part of this fork rebrand. Other ROMs and root-manager versions may require additional testing.

## Permissions

The Android app part of MSD does not use any permissions at all. Also, despite that it is installed as a system app, the SELinux policy is configured so that it is not granted any more privileges than a regular user app.

The daemon part of MSD runs as the `system` user and with the `CAP_CHOWN` capability allowed. The daemon is responsible for all USB configuration. It accepts 3 requests from the app:

* Query the currently active USB gadget functions
* Set up mass storage devices from a list of file descriptors
* Query the currently active mass storage devices

When setting up mass storage devices, the daemon never opens files on its own. The app opens files itself and then sends the open file descriptor the daemon over a Unix socket. This way, even if a malicious client happened to be able to connect to the daemon, it can't expose files over mass storage devices that it didn't already have access to.

The app runs in Android's stock `untrusted_app` domain. The daemon authenticates clients using their kernel-reported UID and installed APK signing certificate, with Package Manager queries handled by a root supervisor. The daemon retains its restricted `msd_daemon` domain and SELinux safety checks.

## Advanced features

### Debug mode

MSD has hidden debug options that can be enabled or disabled by long pressing the version number.

### Logs

To access the MSD's logs, enable debug mode and press `Open log directory` to open the log directory in the system file manager (DocumentsUI). Or alternatively, browse to `/sdcard/Android/com.chiller3.msd/files` manually.

* `crash.log`: Logs for the last crash.
* `/data/local/tmp/msd/*`: Logs for the boot scripts.

To monitor the daemon's logs, run `adb logcat -v color -s msd-tool` or look at `/data/local/tmp/msd/msd-tool.log`.

When reporting bugs, please include all of the logs as they are extremely helpful for identifying what might be going wrong.

### CLI

MSD's functionality can also be accessed from the command line via the `msd-tool` executable. If installed via the module, the executable is in `/data/adb/modules/com.chiller3.msd/msd-tool.arm64-v8a`.

To list all active USB gadget functions:

```bash
msd-tool client get-functions
```

To list all configured mass storage devices:

```bash
msd-tool client get-mass-storage
```

To set up mass storage devices:

```bash
msd-tool client set-mass-storage -t {cdrom|disk-ro|disk-rw} -f /path/to/file.img
```

`-t` and `-f` can be specified multiple times to create multiple mass storage devices.

To clear all mass storage devices:

```bash
msd-tool client set-mass-storage
```

## Signing and updates

MSD-KSU builds use the key selected by the fork's build configuration. Upstream MSD's published signing certificate is not a verification key for new fork builds.

Inspect the APK bundled inside the module ZIP with:

```bash
apksigner verify --print-certs system/priv-app/com.chiller3.msd/app-debug.apk
```

For a release build, use `app-release.apk`. Verify a release against the certificate fingerprint published with that fork release. No fork release signing identity has been published yet. CI debug keys can differ between runs, so those artifacts are not a stable update channel.

Android requires the same signing identity for an in-place APK update. A fork build with a different key cannot directly replace an upstream-signed APK as an app update; preserve any needed settings before changing installations. Use a consistent signing key for your own builds. The module pins its bundled APK's signer for daemon authentication.

Automatic module update metadata is disabled until this fork has its own release channel.

## Building from source

### Building app and module

Make sure the [Rust toolchain](https://www.rust-lang.org/) is installed. Rust must be installed via rustup because it provides the required Android toolchains:

```bash
rustup target add aarch64-linux-android
rustup target add thumbv7neon-linux-androideabi
rustup target add x86_64-linux-android
```

[cargo-android](https://github.com/chenxiaolong/cargo-android) must also be installed.

Then, MSD-KSU can be built like most other Android apps using Android Studio or the gradle command line.

To build the APK:

```bash
./gradlew assembleDebug
```

To build the KernelSU module ZIP (which automatically runs the `assembleDebug` task if needed):

```bash
./gradlew zipDebug
```

The output file is written to `app/build/distributions/debug/`. The APK will be signed with the default autogenerated debug key.

To create a release build with a specific signing key, set up the following environment variables:

```bash
export RELEASE_KEYSTORE=/path/to/keystore.jks
export RELEASE_KEY_ALIAS=alias_name

read -r -s RELEASE_KEYSTORE_PASSPHRASE
read -r -s RELEASE_KEY_PASSPHRASE
export RELEASE_KEYSTORE_PASSPHRASE
export RELEASE_KEY_PASSPHRASE
```

and then build the release zip:

```bash
./gradlew zipRelease
```

## Contributing

Report KernelSU compatibility issues and send fork-specific changes to [HiFiPhile/MSD](https://github.com/HiFiPhile/MSD). Include the phone model, Android and KernelSU versions, mount backend, and relevant MSD logs.

The original project is [chenxiaolong/MSD](https://github.com/chenxiaolong/MSD). Existing upstream code, artwork, translations, and copyright notices are retained.

## License

MSD-KSU retains MSD's GPL-3.0-only license. Please see [`LICENSE`](./LICENSE) for the full license text.
