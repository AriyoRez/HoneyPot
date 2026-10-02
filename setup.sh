#!/usr/bin/env bash
# =============================================================================
# setup.sh — local dev environment bootstrap for the HoneyPot project.
#
# Cross-platform (macOS / Linux / Windows Git Bash). Safe to re-run.
# Creates a project-local .venv, installs dependencies, pins them to
# requirements.lock.txt, and prepares a local .env.
#
# It does NOT install anything system-wide and does NOT install Python itself.
# =============================================================================
set -euo pipefail

# --- Resolve project root (dir containing this script) -----------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
MIN_PY_MAJOR=3
MIN_PY_MINOR=10

echo "==> HoneyPot dev environment setup"
echo "    Project root: $SCRIPT_DIR"

# --- 1. Find a suitable Python (>= 3.10) -------------------------------------
PYTHON=""
for candidate in python3 python "py -3"; do
    # shellcheck disable=SC2086
    if $candidate --version >/dev/null 2>&1; then
        ver="$($candidate -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "")"
        if [ -n "$ver" ]; then
            maj="${ver%%.*}"
            min="${ver##*.}"
            if [ "$maj" -gt "$MIN_PY_MAJOR" ] || { [ "$maj" -eq "$MIN_PY_MAJOR" ] && [ "$min" -ge "$MIN_PY_MINOR" ]; }; then
                PYTHON="$candidate"
                echo "==> Using Python: $candidate (version $ver)"
                break
            fi
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}+ is required but was not found." >&2
    echo "       Install Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR} or newer and re-run ./setup.sh." >&2
    echo "       (This script does not install Python for you.)" >&2
    exit 1
fi

# --- 2. Create .venv (skip if it already exists) -----------------------------
if [ -d "$VENV_DIR" ]; then
    echo "==> Reusing existing virtual environment ($VENV_DIR)"
else
    echo "==> Creating virtual environment ($VENV_DIR)"
    # shellcheck disable=SC2086
    $PYTHON -m venv "$VENV_DIR"
fi

# --- 3. Activate venv (OS-aware) + upgrade pip -------------------------------
if [ -f "$VENV_DIR/Scripts/activate" ]; then
    # Windows layout (Git Bash)
    # shellcheck disable=SC1091
    source "$VENV_DIR/Scripts/activate"
elif [ -f "$VENV_DIR/bin/activate" ]; then
    # macOS / Linux layout
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
else
    echo "ERROR: could not find an activate script under $VENV_DIR." >&2
    exit 1
fi

echo "==> Upgrading pip"
python -m pip install --upgrade pip

# --- 4. Install dependencies -------------------------------------------------
# Dev deps are mandatory.
echo "==> Installing dev dependencies (requirements-dev.txt)"
python -m pip install -r requirements-dev.txt

# Core runtime deps are mandatory. OpenCanary is installed separately and is
# treated as non-fatal (it has known install friction on macOS/Windows).
echo "==> Installing core runtime dependencies"
python -m pip install pyyaml requests python-dotenv jsonschema

echo "==> Attempting to install opencanary (best-effort)"
if python -m pip install opencanary; then
    echo "==> opencanary installed successfully."
    OPENCANARY_OK=1
else
    OPENCANARY_OK=0
    echo "WARNING: opencanary failed to install in this environment." >&2
    echo "         This is expected on some macOS/Windows setups (dependency friction)." >&2
    echo "         The authoritative install target for opencanary is the Linux VM." >&2
    echo "         Continuing — this is NOT a fatal error for local dev." >&2
fi

# --- 5. Pin resolved versions ------------------------------------------------
echo "==> Writing requirements.lock.txt (pip freeze)"
python -m pip freeze > requirements.lock.txt

# --- 6. Prepare .env ---------------------------------------------------------
if [ -f ".env" ]; then
    echo "==> .env already exists — leaving it untouched."
else
    echo "==> Creating .env from .env.example"
    cp .env.example .env
fi

# --- 7. Next steps -----------------------------------------------------------
echo ""
echo "============================================================"
echo " Setup complete."
echo "------------------------------------------------------------"
echo " Next steps:"
echo "   1. Activate the venv:"
if [ -f "$VENV_DIR/Scripts/activate" ]; then
    echo "        source .venv/Scripts/activate   (Windows Git Bash)"
else
    echo "        source .venv/bin/activate        (macOS / Linux)"
fi
echo "   2. Fill in real values in .env (it is gitignored)."
if [ "$OPENCANARY_OK" -eq 0 ]; then
    echo "   3. opencanary did NOT install locally — use the Linux VM for the decoy."
else
    echo "   3. opencanary is installed locally for sandboxed dev iteration."
fi
echo "   4. Pinned versions are in requirements.lock.txt (commit for teammates)."
echo "============================================================"
