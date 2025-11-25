#!/usr/bin/env bash
set -euo pipefail

# Configuration
NAMESPACE="fednestd-system"
KAFKA_CLUSTER_NAME="kafka"
REPLICAS=3

echo "==========================================="
echo " Installing Strimzi Kafka (KRaft Mode)"
echo "==========================================="

# Step 1: Install Strimzi Operator
echo "[1/4] Installing Strimzi Operator..."
kubectl create namespace strimzi-system --dry-run=client -o yaml | kubectl apply -f -

helm repo add strimzi https://strimzi.io/charts/ 2>/dev/null || true
helm repo update strimzi

helm upgrade --install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
  --namespace strimzi-system \
  --set watchNamespaces="{${NAMESPACE}}" \
  --wait --timeout 5m

echo "[2/4] Waiting for Strimzi Operator to be ready..."
kubectl rollout status deployment/strimzi-cluster-operator -n strimzi-system --timeout=120s

# Step 2: Ensure namespace exists
echo "[3/4] Ensuring namespace '$NAMESPACE'..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Step 3: Create Kafka cluster with KRaft mode (no ZooKeeper)
echo "[4/4] Deploying Kafka cluster (KRaft mode)..."

# First, create the KafkaNodePool for combined controller+broker nodes
cat <<EOF | kubectl apply -f -
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaNodePool
metadata:
  name: combined
  namespace: ${NAMESPACE}
  labels:
    strimzi.io/cluster: ${KAFKA_CLUSTER_NAME}
spec:
  replicas: ${REPLICAS}
  roles:
    - controller
    - broker
  storage:
    type: persistent-claim
    size: 5Gi
    deleteClaim: false
  resources:
    requests:
      memory: 2Gi
      cpu: 500m
    limits:
      memory: 4Gi
      cpu: 2
EOF

# Then create the Kafka cluster
cat <<EOF | kubectl apply -f -
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: ${KAFKA_CLUSTER_NAME}
  namespace: ${NAMESPACE}
  annotations:
    strimzi.io/node-pools: enabled
    strimzi.io/kraft: enabled
spec:
  kafka:
    version: 4.0.0
    metadataVersion: "4.0"
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: tls
        port: 9093
        type: internal
        tls: true
        authentication:
          type: tls
    config:
      offsets.topic.replication.factor: ${REPLICAS}
      transaction.state.log.replication.factor: ${REPLICAS}
      transaction.state.log.min.isr: 2
      default.replication.factor: ${REPLICAS}
      min.insync.replicas: 2
      log.retention.hours: 168
      log.retention.bytes: 53687091200
  entityOperator:
    topicOperator: {}
    userOperator: {}
EOF

echo "==========================================="
echo " Kafka cluster deployment initiated!"
echo "==========================================="
echo ""
echo "Monitor status with:"
echo "  kubectl get kafka ${KAFKA_CLUSTER_NAME} -n ${NAMESPACE} -w"
echo ""
echo "Check pods:"
echo "  kubectl get pods -n ${NAMESPACE} -l strimzi.io/cluster=${KAFKA_CLUSTER_NAME}"
echo ""
echo "Bootstrap servers (internal):"
echo "  Plain:  ${KAFKA_CLUSTER_NAME}-kafka-bootstrap.${NAMESPACE}.svc:9092"
echo "  TLS:    ${KAFKA_CLUSTER_NAME}-kafka-bootstrap.${NAMESPACE}.svc:9093"
echo "==========================================="

