#!/usr/bin/env bash
set -euo pipefail

# Configuration
RELEASE_NAME="kafka"
NAMESPACE="fednestd-system"
VALUES_FILE="values.yaml" # Ensure this matches your filename
REPLICAS=3
CLUSTER_ISSUER="internal-ca" 
CHART_URL="oci://registry-1.docker.io/bitnamicharts/kafka"

# ------------------------------------------------------------------
# Pre-flight Checks
# ------------------------------------------------------------------
if [[ ! -f "$VALUES_FILE" ]]; then
  echo "Error: '$VALUES_FILE' not found. Please create it first."
  exit 1
fi

echo "[1/4] Ensuring Namespace '$NAMESPACE'..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# ------------------------------------------------------------------
# Step 1: Configure Cert-Manager Certificate (KRaft compatible)
# ------------------------------------------------------------------
echo "[2/4] Applying Certificate for Kafka Brokers..."

DNS_NAMES=""
DNS_NAMES+="    - ${RELEASE_NAME}.${NAMESPACE}.svc.cluster.local"$'\n'
DNS_NAMES+="    - ${RELEASE_NAME}-controller-headless.${NAMESPACE}.svc.cluster.local"$'\n'

for (( i=0; i<${REPLICAS}; i++ )); do
  DNS_NAMES+="    - ${RELEASE_NAME}-controller-${i}.${RELEASE_NAME}-controller-headless.${NAMESPACE}.svc.cluster.local"$'\n'
done

cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: kafka-brokers
  namespace: ${NAMESPACE}
spec:
  secretName: kafka-tls
  duration: 2160h
  renewBefore: 360h
  commonName: ${RELEASE_NAME}.${NAMESPACE}.svc.cluster.local
  dnsNames:
${DNS_NAMES}  issuerRef:
    name: ${CLUSTER_ISSUER}
    kind: ClusterIssuer
EOF

# Wait for secret
echo "      Waiting for TLS secret 'kafka-tls' to be ready..."
timeout=60
while ! kubectl get secret kafka-tls -n "$NAMESPACE" >/dev/null 2>&1; do
  sleep 2
  ((timeout--))
  if [[ $timeout -eq 0 ]]; then echo "Timed out waiting for secret."; exit 1; fi
done

# ------------------------------------------------------------------
# Step 2: Handle Existing Credentials & Cluster ID
# ------------------------------------------------------------------
echo "[3/4] Checking for existing credentials to allow upgrade..."

HELM_EXTRA_ARGS=()
TLS_PASS_SECRET="${RELEASE_NAME}-tls-passwords"
KRAFT_SECRET="${RELEASE_NAME}-kraft"

# 1. Handle TLS Passwords
if kubectl get secret "$TLS_PASS_SECRET" -n "$NAMESPACE" >/dev/null 2>&1; then
  echo "      [+] Found existing TLS passwords. Extracting..."
  KS_PASS=$(kubectl get secret "$TLS_PASS_SECRET" -n "$NAMESPACE" -o jsonpath="{.data.keystore-password}" | base64 -d)
  TS_PASS=$(kubectl get secret "$TLS_PASS_SECRET" -n "$NAMESPACE" -o jsonpath="{.data.truststore-password}" | base64 -d)
  KEY_PASS=$(kubectl get secret "$TLS_PASS_SECRET" -n "$NAMESPACE" -o jsonpath="{.data.key-password}" | base64 -d)

  HELM_EXTRA_ARGS+=(--set "tls.keystorePassword=$KS_PASS")
  HELM_EXTRA_ARGS+=(--set "tls.truststorePassword=$TS_PASS")
  HELM_EXTRA_ARGS+=(--set "tls.keyPassword=$KEY_PASS")
fi

# 2. Handle KRaft Cluster ID
if kubectl get secret "$KRAFT_SECRET" -n "$NAMESPACE" >/dev/null 2>&1; then
  echo "      [+] Found existing KRaft Cluster ID. Extracting..."
  CLUSTER_ID=$(kubectl get secret "$KRAFT_SECRET" -n "$NAMESPACE" -o jsonpath="{.data.cluster-id}" | base64 -d)
  
  if [[ -n "$CLUSTER_ID" ]]; then
    HELM_EXTRA_ARGS+=(--set "clusterId=$CLUSTER_ID")
  fi
fi

# ------------------------------------------------------------------
# Step 3: Install/Upgrade Helm Chart
# ------------------------------------------------------------------
echo "[4/4] Installing Kafka from OCI Registry..."

# TLS password secret key fields are disabled in values.yaml since we use PEM certs
helm upgrade --install "$RELEASE_NAME" "$CHART_URL" \
  --namespace "$NAMESPACE" \
  --values "$VALUES_FILE" \
  --set controller.replicaCount="$REPLICAS" \
  --set listeners.client.protocol=SSL \
  --set listeners.controller.protocol=SSL \
  --set listeners.interbroker.protocol=SSL \
  --set tls.type=PEM \
  --set tls.existingSecret=kafka-tls \
  --set tls.pemChainIncluded=true \
  "${HELM_EXTRA_ARGS[@]}"

echo "==========================================================="
echo "Deployment initiated."
echo "Monitor status with:"
echo "  kubectl rollout status statefulset/${RELEASE_NAME}-controller -n ${NAMESPACE}"
echo "==========================================================="