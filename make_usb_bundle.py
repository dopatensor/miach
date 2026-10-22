"""Build a self-contained Windows folder for running the Miach demo from a pen drive.

    python3 make_usb_bundle.py            # -> miach-usb/  (needs internet; run on any OS)
    python3 make_usb_bundle.py --zip      # also writes miach-usb.zip

The folder needs nothing installed on the demo laptop (no Python, no Node, no internet):
  python/     portable CPython 3.12 for Windows x64 (official build, from the NuGet "python" package)
              with the backend's packages in python/Lib/site-packages (prebuilt win_amd64 wheels)
  app/        backend/app, artifacts/, ml/miach_panel.py, ml/results_multi/, frontend/dist/
  run-demo.bat   double-click: starts http://localhost:8000 and opens the Designer
"""
from __future__ import annotations

import argparse
import io
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY_VERSION = "3.12.10"   # last 3.12 release with official Windows binaries
NUGET = f"https://api.nuget.org/v3-flatcontainer/python/{PY_VERSION}/python.{PY_VERSION}.nupkg"
# Pinned to versions the backend test suite passes with (model.joblib is a scikit-learn pickle, so the
# scikit-learn version must match). numpy 2.1.x: newer numpy calls ucrtbase crealf, which Wine 9 lacks,
# so 2.1 is the newest numpy the bundle can be tested with under Wine (real Windows has it either way). uvicorn without [standard]: no compiled extras needed. colorama is
# listed explicitly because pip skips click's Windows-only dependency when run on another OS.
PACKAGES = ["fastapi==0.159.1", "uvicorn==0.54.0", "pydantic==2.14.1", "numpy==2.1.3", "pandas==3.0.6",
            "scikit-learn==1.9.1", "scipy==1.18.1", "joblib==1.6.0", "python-multipart==0.0.32",
            "colorama==0.4.6"]
APP_FILES = ["backend/app", "artifacts", "ml/miach_panel.py", "ml/results_multi", "frontend/dist"]

START_BAT = r"""@echo off
setlocal
title Miach demo - keep this window open
set PORT=8000
cd /d "%~dp0app\backend"
echo.
echo   Miach is starting on http://localhost:%PORT%  (the browser opens when it is ready)
echo   Keep this window open during the demo. Close it, or press Ctrl+C, to stop.
echo.
start "" /b "%~dp0python\python.exe" "%~dp0open_browser.py" %PORT%
"%~dp0python\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT% --log-level warning
echo.
echo   Miach stopped. If an error is shown above, "address already in use" means another copy is
echo   running: close the other window, or edit PORT in this file.
pause
"""

OPEN_BROWSER = '''"""Wait until the local server answers, then open the Designer in the default browser."""
import sys, time, urllib.request, webbrowser

port = sys.argv[1] if len(sys.argv) > 1 else "8000"
base = f"http://localhost:{port}"
for _ in range(90):
    try:
        urllib.request.urlopen(base + "/api/health", timeout=1)
        webbrowser.open(base + "/designer")
        print(f"  Ready: {base}/designer")
        break
    except Exception:
        time.sleep(1)
else:
    print("  The server did not start within 90 s; see the messages in this window.")
'''

README = """MIACH - LOCAL DEMO FROM A PEN DRIVE (Windows 10/11, 64-bit)
Research use only. Candidate biomarker panels; not for diagnosis or treatment decisions.

1. Copy the whole miach-usb folder to the laptop's Desktop (faster than running from the stick;
   running directly from the pen drive also works, just starts slower).
2. Double-click run-demo.bat. A black window opens; the browser opens at
   http://localhost:8000/designer after about 10-30 seconds (first start from a USB stick is slowest).
3. Keep the black window open during the demo. Close it to stop.

No internet, Python or Node needed. If Windows shows "Windows protected your PC", click
"More info" -> "Run anyway" (the .bat file is not signed).
If the browser does not open by itself, open http://localhost:8000/designer manually.
"""


def run(cmd, **kw):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kw)


def main(out: Path, make_zip: bool) -> None:
    if not (ROOT / "frontend/dist/index.html").exists():
        run(["npm", "ci", "--no-audit", "--no-fund"], cwd=ROOT / "frontend")
        run(["npm", "run", "build"], cwd=ROOT / "frontend")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    print(f"downloading portable Python {PY_VERSION} (Windows x64) from NuGet", flush=True)
    with urllib.request.urlopen(NUGET) as r, zipfile.ZipFile(io.BytesIO(r.read())) as z:
        for m in z.namelist():
            if m.startswith("tools/") and not m.endswith("/"):
                dest = out / "python" / m[len("tools/"):]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(m))
    assert (out / "python/python.exe").exists(), "python.exe missing from the NuGet package"

    run([sys.executable, "-m", "pip", "install", "--quiet", "--no-compile", "--only-binary=:all:",
         "--platform", "win_amd64", "--python-version", PY_VERSION.rsplit(".", 1)[0],
         "--implementation", "cp", "--target", str(out / "python/Lib/site-packages"), *PACKAGES])
    for stray in (out / "python/Lib/site-packages").glob("*.whl"):   # empty leftovers some pip setups write
        stray.unlink()

    for rel in APP_FILES:
        src, dest = ROOT / rel, out / "app" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, dest)

    (out / "run-demo.bat").write_text(START_BAT.replace("\n", "\r\n"))
    (out / "open_browser.py").write_text(OPEN_BROWSER)
    (out / "README.txt").write_text(README.replace("\n", "\r\n"))

    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 1e6
    print(f"done: {out} ({size:.0f} MB)")
    if make_zip:
        archive = shutil.make_archive(str(out), "zip", out.parent, out.name)
        print(f"zip: {archive} ({Path(archive).stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--out", type=Path, default=ROOT / "miach-usb")
    a.add_argument("--zip", action="store_true")
    args = a.parse_args()
    main(args.out, args.zip)
