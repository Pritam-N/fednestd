#!/usr/bin/env bash
set -euo pipefail

# Install Jetstack cert-manager via Helm with CRDs.

NAMESPACE="fednestd-system"
RELEASE_NAME="fednestd-system"
CHART_VERSION="v1.19.1"  # adjust to latest if needed

while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace|-n)
      NAMESPACE="$2"
      shift 2
      ;;
    --release|-r)
      RELEASE_NAME="$2"
      shift 2
      ;;
    --version|-v)
      CHART_VERSION="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--namespace <ns>] [--release <name>] [--version <chart-version>]"
      exit 1
      ;;
  esac
done

echo "[+] Ensuring namespace '${NAMESPACE}' exists..."
kubectl get ns "${NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${NAMESPACE}"

echo "[+] Adding Jetstack Helm repo..."
helm repo add jetstack https://charts.jetstack.io >/dev/null 2>&1 || true

echo "[+] Updating Helm repos..."
helm repo update >/dev/null

echo "[+] Installing/Upgrading cert-manager (${CHART_VERSION}) in namespace '${NAMESPACE}'..."

helm upgrade --install "${RELEASE_NAME}" jetstack/cert-manager \
  --namespace "${NAMESPACE}" \
  --version "${CHART_VERSION}" \
  --set crds.enabled=true

echo "[+] Waiting for cert-manager pods to be ready..."
kubectl rollout status deployment/"${RELEASE_NAME}" -n "${NAMESPACE}" --timeout=300s || true
kubectl rollout status deployment/"${RELEASE_NAME}"-webhook -n "${NAMESPACE}" --timeout=300s || true
kubectl rollout status deployment/"${RELEASE_NAME}"-cainjector -n "${NAMESPACE}" --timeout=300s || true

echo
echo "[+] Current pods in '${NAMESPACE}':"
kubectl get pods -n "${NAMESPACE}"

echo
echo "[✓] cert-manager installation complete."
