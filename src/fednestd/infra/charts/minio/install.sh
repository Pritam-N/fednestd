#!/bin/bash
set -e

echo "Creating secret..."
kubectl apply -f secrets.yaml

echo "Adding Helm repo..."
helm repo add minio https://charts.min.io/
helm repo update

echo "Installing MinIO with secret-based credentials..."
helm install minio minio/minio \
  -n fednestd-data \
  -f values.yaml

echo "MinIO deployed (production mode with dynamic PVC + secret)!"
