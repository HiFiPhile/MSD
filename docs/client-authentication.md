# Daemon client authentication

The UI uses Android's existing `untrusted_app` SELinux domain so it can start on
kernels whose SELinux hiding feature rejects app contexts absent from the original
policy. The daemon keeps its `msd_daemon` domain, system UID, and CAP_CHOWN.

Because other apps share `untrusted_app`, SELinux socket access alone no longer
identifies MSD. Authentication is mandatory before negotiating the protocol or
spawning a client worker, and again before executing each request.

## Trust boundary

A root `app_process` supervisor starts the daemon through Android's `runcon`.
The daemon obtains the client's full UID using SO_PEERCRED and sends a big-endian
32-bit UID to the supervisor over private inherited pipes. The supervisor returns
one byte: 0 for deny, 1 for allow. Neither a client-provided UID nor a
client-provided certificate is trusted.

The supervisor queries Package Manager for the UID's Android user and requires:

- An application UID whose only package is `com.chiller3.msd`.
- Package metadata containing exactly that full UID and package name.
- No shared UID and exactly one current APK signer.
- A SHA-256 digest matching `client-cert.sha256` in the root-owned module.

The module build derives the pin from its APK signing configuration. The pin is
public; integrity of the module and Package Manager is trusted. Certificate
rotation requires updating the pin. Multiple signers and historical signers are
not accepted as substitutes for the configured current signer.

UID 0 retains administrative CLI access. Neither shell nor UID 1000 bypasses
authentication. `sepatch --allow-adb` can grant shell SELinux connectivity, but
shell still cannot authenticate; use the CLI through `su`.

The supervisor handles only UID decisions, never client protocol messages, image
descriptors, or USB configuration. The daemon still requires enforcing SELinux
and checks that its policy denies a connection to itself.

## Failure behavior

Package Manager lookup failures deny that request. The next request queries the
service again; decisions are not cached across requests. A response timeout,
EOF, malformed byte, or other pipe error permanently disables non-root
authentication until the daemon restarts. This prevents a delayed response from
authorizing a different request. The response timeout is five seconds.

The supervisor must run as root and exits if its child dies. Process supervision
and Package Manager availability are additional runtime dependencies. Root or
framework compromise is outside this authentication boundary.

## Validation

The native `auth::tests::` tests cover full-UID transport, revalidation, root-only
bypass, malformed responses, supervisor EOF, and a late response after timeout.
Build the Android test executable with `cargo test --target
<android-target> --release --no-run`, then run it on the device with
`auth::tests:: --test-threads=1`.

Device checks should also verify a valid package/certificate, a wrong pin, an
unrelated app in `untrusted_app`, and startup after reboot with SELinux Hide
enabled and SELinux enforcing. Verify both debug and release module packaging
so the shipped pin matches the shipped APK.
