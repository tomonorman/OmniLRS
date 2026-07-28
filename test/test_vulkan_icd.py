"""Diagnostic for duplicate Vulkan ICD manifests.

Per NVIDIA Omniverse Linux troubleshooting (Q4), a single GPU is enumerated
multiple times when NVIDIA ICD json files exist in BOTH of these locations:

  /etc/vulkan/icd.d       : ICDs from non-distribution packages (.run installs,
                            or injected by the NVIDIA container toolkit)
  /usr/share/vulkan/icd.d : ICDs from Linux-distribution packages

This crashes Isaac Sim / Kit when multi-GPU mode is enabled. The full listing
is written to the artefacts upload dir so it is visible in the dashboard.
"""

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

ICD_DIRS = [
    Path("/etc/vulkan/icd.d"),
    Path("/usr/share/vulkan/icd.d"),
]


def _log_dir():
    # Artefacts upload dir if available, otherwise a local test dir.
    upload_dir = os.environ.get("ARTEFACTS_SCENARIO_UPLOAD_DIR")
    log_dir = Path(upload_dir) if upload_dir else REPO_ROOT / "test"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _nvidia_icds(directory):
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.json") if "nvidia" in p.name.lower())


def test_this_just_passes():
    assert 1 + 1 == 2, "This test is just a placeholder to make pytest happy."

def test_no_duplicate_nvidia_vulkan_icds():
    report_path = _log_dir() / "vulkan_icd_report.txt"
    found = {}
    with open(report_path, "w") as report:
        for var in ("VK_DRIVER_FILES", "VK_ICD_FILENAMES", "VK_ADD_DRIVER_FILES"):
            report.write(f"{var}={os.environ.get(var, '(unset)')}\n")
        loader = subprocess.run(
            ["dpkg-query", "-W", "libvulkan1"], capture_output=True, text=True
        )
        report.write(f"vulkan loader: {loader.stdout.strip() or loader.stderr.strip()}\n\n")
        for directory in ICD_DIRS:
            icds = _nvidia_icds(directory)
            found[directory] = icds
            report.write(f"{directory}: {'(missing)' if not directory.is_dir() else ''}\n")
            for path in sorted(directory.glob("*")) if directory.is_dir() else []:
                report.write(f"  {path.name}\n")
                if path in icds:
                    try:
                        report.write(f"    contents: {path.read_text().strip()}\n")
                    except OSError as exc:
                        report.write(f"    (unreadable: {exc})\n")

    all_icds = [str(p) for icds in found.values() for p in icds]
    print(f"NVIDIA ICDs found: {all_icds or 'none'} (see {report_path.name})")

    # A VK_DRIVER_FILES / VK_ICD_FILENAMES override pins the loader to a single
    # manifest, making extra manifests on disk harmless.
    override = os.environ.get("VK_ICD_FILENAMES") or os.environ.get("VK_DRIVER_FILES")
    if override:
        assert Path(override).is_file(), (
            f"Vulkan ICD override points to a missing file: {override}. The loader "
            "will find no NVIDIA driver at all. Check which manifest names the "
            f"runner injects (see {report_path.name})."
        )
        return

    assert len(all_icds) <= 1, (
        f"Duplicate NVIDIA Vulkan ICDs found: {all_icds}. The same GPU will be "
        "enumerated once per manifest, which crashes Kit in multi-GPU mode. Pin "
        "one manifest via VK_ICD_FILENAMES/VK_DRIVER_FILES or remove the extras "
        f"(see {report_path.name} for the full listing)."
    )
