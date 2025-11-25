#!/usr/bin/env bash
set -euo pipefail

# Simple installer for NVIDIA GPU Operator on Kubernetes
# Usage:
#   ./install_gpu_operator.sh                  # default install
#   ./install_gpu_operator.sh --no-driver      # if nodes already have NVIDIA driver installed
#
# Requirements:
#   - kubectl configured to point at your cluster
#   - helm installed and on PATH

NAMESPACE="gpu-operator"
RELEASE_NAME="gpu-operator"
INSTALL_DRIVER=true

for arg in "$@"; do
  case "$arg" in
    --no-driver)
      INSTALL_DRIVER=false
      shift
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [--no-driver]"
      exit 1
      ;;
  esac
done

echo "[+] Creating namespace '${NAMESPACE}' (if not exists)..."
kubectl get ns "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"

echo "[+] Adding NVIDIA Helm repo..."
helm repo add nvidia https://nvidia.github.io/gpu-operator >/dev/null 2>&1 || true

echo "[+] Updating Helm repos..."
helm repo update >/dev/null

echo "[+] Installing/Upgrading NVIDIA GPU Operator..."

if [ "${INSTALL_DRIVER}" = true ]; then
  echo "    - GPU driver installation: ENABLED"
  helm upgrade --install "${RELEASE_NAME}" nvidia/gpu-operator \
    -n "${NAMESPACE}"
else
  echo "    - GPU driver installation: DISABLED (assuming pre-installed drivers)"
  helm upgrade --install "${RELEASE_NAME}" nvidia/gpu-operator \
    -n "${NAMESPACE}" \
    --set driver.enabled=false
fi

echo "[+] Waiting for GPU Operator pods to be ready..."
kubectl rollout status -n "${NAMESPACE}" deployment/gpu-operator --timeout=300s || true

echo "[+] Current pods in namespace '${NAMESPACE}':"
kubectl get pods -n "${NAMESPACE}"

echo
echo "[+] If everything is Running, check that nodes report GPU resources via:"
echo "    kubectl describe node <gpu-node> | grep -i nvidia.com/gpu"
echo
echo "[✓] GPU Operator installation script finished."
