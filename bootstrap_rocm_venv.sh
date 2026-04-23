

#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a project-local venv that can import ROCm torch from /opt/venv.
# Installs project deps into .venv while keeping /opt/venv untouched.

ROCM_BASE_PY="${ROCM_BASE_PY:-/opt/venv/bin/python3}"
VENV_DIR="${VENV_DIR:-.venv}"

# Optional: requirements file(s) to install after venv creation
REQ_FILE="${REQ_FILE:-}"
REQ_GLOB="${REQ_GLOB:-requirements*.txt}"

echo "[bootstrap] Using ROCm base Python: ${ROCM_BASE_PY}"
echo "[bootstrap] Project venv dir: ${VENV_DIR}"

if [[ ! -x "${ROCM_BASE_PY}" ]]; then
  echo "[bootstrap] ERROR: ${ROCM_BASE_PY} not found or not executable."
  exit 1
fi

# Create/replace venv
if [[ -d "${VENV_DIR}" ]]; then
  echo "[bootstrap] Removing existing ${VENV_DIR}"
  rm -rf "${VENV_DIR}"
fi

echo "[bootstrap] Creating venv..."
"${ROCM_BASE_PY}" -m venv "${VENV_DIR}"

# Activate venv (shellcheck disable=SC1091)
source "${VENV_DIR}/bin/activate"

echo "[bootstrap] Upgrading pip..."
python -m pip install -U pip setuptools wheel >/dev/null

# Bridge to ROCm base environment site-packages
OPT_SITE="$("${ROCM_BASE_PY}" -c "import site; print(site.getsitepackages()[0])")"
PYVER="$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")"
PTH_DIR="${VENV_DIR}/lib/python${PYVER}/site-packages"
PTH_FILE="${PTH_DIR}/rocm_base.pth"

mkdir -p "${PTH_DIR}"
echo "${OPT_SITE}" > "${PTH_FILE}"

echo "[bootstrap] Created bridge: ${PTH_FILE} -> ${OPT_SITE}"

# Verify torch import works (from /opt/venv)
echo "[bootstrap] Verifying torch import..."
python - <<'PY'
import torch
print("torch:", torch.__version__)
print("torch_file:", torch.__file__)
print("hip:", getattr(torch.version, "hip", None))
print("cuda_available:", torch.cuda.is_available())
PY

# Optional dependency install
install_reqs() {
  local file="$1"
  if [[ ! -f "${file}" ]]; then
    echo "[bootstrap] Skipping missing requirements file: ${file}"
    return 0
  fi

  echo "[bootstrap] Installing deps from ${file} (excluding torch/torchvision/torchaudio)..."
  local filtered="/tmp/req.no-torch.$$.txt"
  grep -viE '^(torch|torchvision|torchaudio)(==|>=|<=|~=|$)' "${file}" > "${filtered}" || true

  if [[ ! -s "${filtered}" ]]; then
    echo "[bootstrap] Note: filtered requirements file is empty; nothing to install."
    rm -f "${filtered}"
    return 0
  fi

  # Use uv if available; fall back to pip.
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "${VENV_DIR}/bin/python" -r "${filtered}"
  else
    python -m pip install -r "${filtered}"
  fi
  rm -f "${filtered}"
}

if [[ -n "${REQ_FILE}" ]]; then
  install_reqs "${REQ_FILE}"
else
  # Install the first matching requirements*.txt in the project root (if any)
  shopt -s nullglob
  files=( ${REQ_GLOB} )
  shopt -u nullglob
  if [[ ${#files[@]} -gt 0 ]]; then
    # Prefer requirements.txt if present
    if [[ -f "requirements.txt" ]]; then
      install_reqs "requirements.txt"
    else
      install_reqs "${files[0]}"
    fi
  else
    echo "[bootstrap] No requirements file found. Skipping dependency install."
    echo "[bootstrap] Tip: set REQ_FILE=path/to/requirements.txt to install automatically."
  fi
fi

echo
echo "[bootstrap] Done."
echo "  Activate with: source ${VENV_DIR}/bin/activate"
echo "  Verify torch:  python -c \"import torch; print(torch.__version__, torch.cuda.is_available())\""
