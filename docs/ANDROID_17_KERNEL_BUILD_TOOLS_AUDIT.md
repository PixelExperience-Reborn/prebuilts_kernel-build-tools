# Android 17 — archived kernel build tools audit (P2, matrix row 159)

## Decision, 2026-11-06

**Do not import historical `prebuilts/kernel-build-tools` into the active Android 17 ROM manifest.** Keep the old PixelExperience-Reborn fork as a **read-only host tooling reference**; retain its Git ancestry and binary contents. Any modern kernel build-tools source owner must be selected when the independent PE-Reborn **mondrian** device/kernel build graph actually exists, not through an unrelated ROM-wide override.

This decision **does not** mean that kernel-build tools, AVB, DTBO, pahole, Soong host tools or ABI checks are unnecessary. It means these **specific 2022/2023 binaries and pinned mini-manifest have not been validated for Android 17 / the actual mondrian kernel build.**

## Verified provenance and source inventory

- Original PE branch `seventeen`, `fourteen` and `thirteen` all point to **`083e34d8c2c4239be4967172427268c267585951`** (commit date 2023-02-17, title `Update kernel-build-tools-2022 to ab/9621999`).
- Exact tree `aa62325a8144238dfe666777580b08b6cd8db875` with **156 entries, 148 blobs, 130,001,378 bytes** according to the GitHub tree object.
- 33 `linux-x86/bin` binaries / 115,808,313 bytes, including `abidiff`, `abidw`, `abitidy`, `avbtool`, `build_image`, `build_super_image`, `certify_bootimg`, `dtc`, `mkdtboimg.py`, `mkdtimg`, `pahole`, `stgdiff`, `stginfo`, `soong_zip`, `ufdt_apply_overlay`.
- 86 `linux-x86/include` files / 1,502,820 bytes; 23 `linux-x86/lib64` files / 12,676,649 bytes, including an explicit symlink `libcrypto.so -> libcrypto-host.so`.
- `linux-x86/share/avb/testkey_rsa2048.pem` / 1,675 bytes is an **AVB test key**, NOT a production/release signing key.
- 5 root source/metadata files (including `BUILD.bazel`, `build-prebuilts.sh`, `manifest.xml`, `update-prebuilts.sh`, `OWNERS`) / 11,921 bytes.
- The historical `manifest.xml` contains **52 projects**, defaults to **`build-tools-2022`**, and references a pinned historical `kernel/prebuilts/build-tools` commit `0fb21fa343b2157c91e21b7ead1e99c1ea82125b`. It also includes obsolete dependencies such as `external/python/cpython2`. **This nested manifest must not be substituted into PE-Reborn's Android 17 ROM graph.**
- The old `build-prebuilts.sh` generates host tools by calling `build/soong/soong_ui.bash`, stages headers and libraries, and packages `build-prebuilts.zip`. Do **not** execute it against the Android17 system tree.
- `update-prebuilts.sh` uses a Google-internal `/google/data/ro/projects/android/fetch_artifact` path and branch `kernel-build-tools-2022`; not a standalone, reproducible modern release mechanism for our builder.

## Upstream split: platform image vs kernel build

The official Android 17 (`android-17.0.0_r1`) platform manifest contains **no** `prebuilts/kernel-build-tools` project. It already owns the separate `prebuilts/build-tools`, `prebuilts/tools`, `prebuilts/clang/host/linux-x86`, `system/tools/mkbootimg` and `kernel/configs` paths. There is no direct proof that the old kernel tool bundle provides a needed missing host package.

There is, separately, the official **kernel** repository [`kernel/prebuilts/build-tools`](https://android.googlesource.com/kernel/prebuilts/build-tools/). Its **`main-kernel` snapshot as observed 2026-11-06** had commit `65847ca9e3668584f4079698b93bb3ff2a60ed8c` / tree `dad875712306868f1623a4e164e1e2e17c86a57c` (commit date 2026-10-08), featuring `bazel/`, `linux_musl-x86/`, `sysroots/` and modern Bazel build rules. This is a **rolling upstream kernel branch**, **not** an AOSP17 ROM tag and **not** an automatically compatible replacement for a Qualcomm 5.10 vendor kernel.

Google's [kernel build documentation](https://source.android.com/docs/setup/build/building-kernels) distinguishes the kernel source/toolchain checkout from the platform ROM checkout. [Kleaf's toolchain guide](https://android.googlesource.com/kernel/build/+/refs/heads/main/kleaf/docs/toolchains.md) describes hermetic/toolchain resolution. Kernel build selection must be made by the actual kernel branch, and **must not be inferred from the Android 17 version number alone**.

## Mondrian-specific constraints, reference-only

The *existing* read-only [`LF52406/mondrian_android_device_xiaomi_sm8450-common` (`lineage-24.0`)](https://github.com/LF52406/mondrian_android_device_xiaomi_sm8450-common/blob/lineage-24.0/BoardConfigCommon.mk) contains:

- `TARGET_KERNEL_SOURCE := kernel/xiaomi/sm8450` and `TARGET_KERNEL_CONFIG` fragments for `waipio_GKI`, `xiaomi_GKI`, and product-specific configs.
- `BOARD_BOOT_HEADER_VERSION := 4`, `BOARD_INCLUDE_DTB_IN_BOOTIMG := true`, `TARGET_NEEDS_DTBOIMAGE := true`.
- Separate vendor kernel modules (`TARGET_KERNEL_EXT_MODULE_ROOT := kernel/xiaomi/sm8450-modules`).
- GKI, AVB, vendor_boot and DTBO-specific requirements; those must be checked together, not through an old host-tool binary pin.
- The archived kernel reference [`Equinox-Kernel-sm8450`](https://github.com/LF52406/Equinox-Kernel-sm8450) is based on 5.10 and contains Waipio build configurations.

**None of those reference trees is a PE-Reborn device implementation.** No LF52406, MistOS or LineageOS files were changed. Do not create a PE-Reborn device lunch product or integrate these old host tools before a separately reviewed independent device, vendor, kernel and module graph is defined.

Additional production security constraint: the existing reference BoardConfig contains AOSP test AVB signing-key paths. **Do not silently reuse test keys for future public/production signing.** Secure release signing requires an explicit separate plan; not part of this row.

## Changes in this audit

- Audit branch has a source-only `audit/check_kernel_build_tools_source.py` that validates exact historical Git tree object, 148 paths / byte counts, selected immutable blob SHA/modes, symlink and test key presence, original 52-project nested manifest and Android17 manifest ownership. It **never executes the legacy prebuilts or old scripts**.
- GitHub Actions fetches only the selected text files and Git tree metadata, not a 130MB executable payload; runs Python regression tests and the official `repo manifest` parser. It also checks the *read-only modern official kernel* upstream layout using a partial metadata Git fetch, without adopting a moving branch.
- The reviewed Android 17 manifest validator and negative test forbid importing the legacy project at `prebuilts/kernel-build-tools`, preserve official `prebuilts/build-tools`, `prebuilts/tools`, `prebuilts/clang/host/linux-x86`, and the system boot-image tool source.
- No new AOSP17 stage, pin, `PRODUCT_PACKAGES`, `TARGET_KERNEL_*`, `BOARD_*` or signing configuration was added.

## Still open — do not equate source checks with successful kernel port

1. Define **only PE-Reborn mondrian** device/common/vendor/kernel/module sources and decide if kernel toolchain is legacy Kbuild or supported Kleaf for the actual 5.10 branch.
2. Reconcile compiler/LLVM version, `pahole`/BTF, ABI/KMI, dtc/dtbo and AVB/boot-image generation with exact kernel source, GKI contract, module outputs, boot header v4, vendor_boot and Qualcomm DTB merge tools.
3. Determine reproducible modern kernel tools with one owner, exact source revision and checksum; no untrusted binary execution.
4. Validate full Android17 `repo sync`, Soong, device tree, vendor extraction, kernel+modules compilation, VINTF/SELinux/CTS/VTS and physical mondrian boot.
5. Validate release signing/test keys independently and do not publish untested signed artifacts.

**Status: historical prebuilt inventory/manifest source-only audit; no kernel build or Android 17 device compatibility claim.**

## References

- [PixelExperience-Reborn archived tools](https://github.com/PixelExperience-Reborn/prebuilts_kernel-build-tools/tree/seventeen)
- [Historical 2023 commit](https://github.com/PixelExperience-Reborn/prebuilts_kernel-build-tools/commit/083e34d8c2c4239be4967172427268c267585951)
- [Active Android17 manifest](https://github.com/PixelExperience-Reborn/manifest/tree/port/a17-aosp17-manifest-20261102)
- [Official upstream kernel tool repository](https://android.googlesource.com/kernel/prebuilts/build-tools/)
