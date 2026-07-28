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


def test_no_duplicate_nvidia_vulkan_icds():
    report_path = _log_dir() / "vulkan_icd_report.txt"
    found = {}
    with open(report_path, "w") as report:
        # Loader override env vars: VK_ICD_FILENAMES is the legacy name honored
        # by old loaders (e.g. 1.3.204 on Ubuntu 22.04); VK_DRIVER_FILES needs >= 1.3.207.
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

    dirs_with_nvidia = [str(d) for d, icds in found.items() if icds]
    print(f"NVIDIA ICDs found in: {dirs_with_nvidia or 'none'} (see {report_path.name})")

    assert len(dirs_with_nvidia) <= 1, (
        "Duplicate NVIDIA Vulkan ICDs found in "
        f"{dirs_with_nvidia}. The same GPU will be enumerated once per ICD, which "
        "crashes Kit in multi-GPU mode. Remove the /usr/share/vulkan/icd.d copy "
        f"(see {report_path.name} for the full listing)."
    )
