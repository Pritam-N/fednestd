#!/usr/bin/env bash
set -euo pipefail

# Install Kafka (Bitnami) with TLS managed by cert-manager.
# Assumes cert-manager + ClusterIssuer "internal-ca" already exist.
#
# Usage:
#   ./install_kafka_with_tls.sh
#
# With options:
#   ./install_kafka_with_tls.sh \
#     --namespace fednestd-system \
#     --release kafka \
#     --values values-kafka-prod.yaml \
#     --replicas 3
#
# Requirements:
#   - kubectl
#   - helm

KAFKA_NAMESPACE="fednestd-system"
KAFKA_RELEASE="kafka"
KAFKA_VALUES_FILE="values.yaml"
KAFKA_REPLICAS=3   # must match replicaCount in your values file

###############################################################################
# Arg parsing
###############################################################################
while [[ $# -gt 0 ]]; do
  case "$1" in
    --namespace|-n)
      KAFKA_NAMESPACE="$2"
      shift 2
      ;;
    --release|-r)
      KAFKA_RELEASE="$2"
      shift 2
      ;;
    --values|-f)
      KAFKA_VALUES_FILE="$2"
      shift 2
      ;;
    --replicas)
      KAFKA_REPLICAS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--namespace <ns>] [--release <name>] [--values <file>] [--replicas <n>]"
      exit 1
      ;;
  esac
done

###############################################################################
# Helpers
###############################################################################
check_binary() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[!] '$1' is required but not found on PATH."
    exit 1
  fi
}

ensure_namespace() {
  local ns="$1"
  if ! kubectl get ns "$ns" >/dev/null 2>&1; then
    echo "[+] Creating namespace '${ns}'..."
    kubectl create namespace "$ns"
  else
    echo "[i] Namespace '${ns}' already exists."
  fi
}

###############################################################################
# Pre-flight
###############################################################################
echo "[*] Pre-flight checks..."
check_binary kubectl
check_binary helm

if [[ ! -f "${KAFKA_VALUES_FILE}" ]]; then
  echo "[!] Kafka values file '${KAFKA_VALUES_FILE}' not found."
  echo "    Please create it (e.g. values.yaml) and rerun this script."
  exit 1
fi

# Check cert-manager CRDs exist
if ! kubectl get crd certificates.cert-manager.io >/dev/null 2>&1; then
  echo "[!] cert-manager CRDs not found (certificates.cert-manager.io missing)."
  echo "    Make sure cert-manager is installed and CRDs are applied."
  exit 1
fi

###############################################################################
# Step 1: Namespace & Kafka TLS Certificate (kafka-tls)
###############################################################################
echo
echo "========================================="
echo " Step 1: Create Kafka namespace & TLS cert"
echo "========================================="

ensure_namespace "${KAFKA_NAMESPACE}"

# Build DNS list for pods: <release>-0.<release>-headless.<ns>.svc.cluster.local, etc.
DNS_NAMES_YAML=""
for (( i=0; i<${KAFKA_REPLICAS}; i++ )); do
  DNS_NAMES_YAML+="    - ${KAFKA_RELEASE}-${i}.${KAFKA_RELEASE}-headless.${KAFKA_NAMESPACE}.svc.cluster.local"$'\n'
done

echo "[+] Applying Certificate 'kafka-brokers' (secret: kafka-tls) in namespace '${KAFKA_NAMESPACE}'..."
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: kafka-brokers
  namespace: ${KAFKA_NAMESPACE}
spec:
  secretName: kafka-tls
  duration: 2160h          # 90 days
  renewBefore: 360h        # 15 days before expiry
  commonName: ${KAFKA_RELEASE}.${KAFKA_NAMESPACE}.svc.cluster.local
  dnsNames:
    - ${KAFKA_RELEASE}.${KAFKA_NAMESPACE}.svc.cluster.local
${DNS_NAMES_YAML}  issuerRef:
    name: internal-ca
    kind: ClusterIssuer
EOF

echo "[+] Waiting for 'kafka-brokers' certificate to be issued..."
# Simple wait loop for the secret
for i in {1..30}; do
  if kubectl get secret kafka-tls -n "${KAFKA_NAMESPACE}" >/dev/null 2>&1; then
    echo "[✓] Secret 'kafka-tls' is present."
    break
  fi
  echo "    ...waiting for kafka-tls (attempt $i/30)"
  sleep 5
done

if ! kubectl get secret kafka-tls -n "${KAFKA_NAMESPACE}" >/dev/null 2>&1; then
  echo "[!] Secret 'kafka-tls' was not created in time. Check:"
  echo "    kubectl describe certificate kafka-brokers -n ${KAFKA_NAMESPACE}"
  exit 1
fi

###############################################################################
# Step 2: Install Kafka (Bitnami) with TLS
###############################################################################
echo
echo "================================="
echo " Step 2: Install Kafka (Bitnami)"
echo "================================="

echo "[+] Adding Bitnami Helm repo..."
helm repo add bitnami https://charts.bitnami.com/bitnami >/dev/null 2>&1 || true

echo "[+] Updating Helm repos..."
helm repo update >/dev/null

# Check if ServiceMonitor CRD exists; if not, disable it to avoid the error you saw
SM_SET_ARGS=()
if kubectl get crd servicemonitors.monitoring.coreos.com >/dev/null 2>&1; then
  echo "[i] ServiceMonitor CRD found. metrics.serviceMonitor will be left as-is from values."
else
  echo "[i] ServiceMonitor CRD NOT found. Disabling metrics.serviceMonitor.enabled to avoid CRD errors."
  SM_SET_ARGS+=(--set metrics.serviceMonitor.enabled=false)
fi

echo "[+] Installing/Upgrading Kafka release '${KAFKA_RELEASE}' in namespace '${KAFKA_NAMESPACE}'..."
helm upgrade --install "${KAFKA_RELEASE}" bitnami/kafka \
  -n "${KAFKA_NAMESPACE}" \
  -f "${KAFKA_VALUES_FILE}" \
  "${SM_SET_ARGS[@]}"

echo "[+] Waiting for Kafka StatefulSet to be ready..."
kubectl rollout status statefulset/"${KAFKA_RELEASE}" -n "${KAFKA_NAMESPACE}" --timeout=900s || true

echo
echo "[+] Kafka pods in '${KAFKA_NAMESPACE}':"
kubectl get pods -n "${KAFKA_NAMESPACE}" | grep "${KAFKA_RELEASE}" || true

echo "[+] Kafka services in '${KAFKA_NAMESPACE}':"
kubectl get svc -n "${KAFKA_NAMESPACE}" | grep "${KAFKA_RELEASE}" || true

echo
echo "[✓] Kafka installation complete."
echo
echo "Use this in your fednestd Tier-1 config:"
echo "  kafka:"
echo "    bootstrap_servers: \"${KAFKA_RELEASE}.${KAFKA_NAMESPACE}.svc.cluster.local:9092\""
echo "    security_protocol: \"SSL\""
echo "    ssl_ca_location: \"/etc/kafka-tls/ca.crt\""
echo
echo "Remember to mount the 'kafka-tls' secret into your fednestd pods at /etc/kafka-tls."
