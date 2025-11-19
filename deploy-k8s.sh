#!/bin/bash

# Deploy to Kubernetes script
# Usage: ./deploy-k8s.sh [namespace]

set -e

NAMESPACE=${1:-"essorcloud"}

echo "Deploying LEGO apps to Kubernetes namespace: ${NAMESPACE}"

# Create namespace if it doesn't exist
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Apply configurations
echo "Applying ConfigMap..."
kubectl apply -f k8s/configmap.yaml -n ${NAMESPACE}

echo "Applying Secrets..."
kubectl apply -f k8s/secret.yaml -n ${NAMESPACE}

echo "Applying Deployment..."
kubectl apply -f k8s/deployment.yaml -n ${NAMESPACE}

echo "Applying Services..."
kubectl apply -f k8s/service.yaml -n ${NAMESPACE}

echo "Applying Ingress (if needed)..."
kubectl apply -f k8s/ingress.yaml -n ${NAMESPACE} || echo "Skipping ingress (not critical)"

echo ""
echo "✓ Deployment complete!"
echo ""
echo "Check status with:"
echo "  kubectl get pods -n ${NAMESPACE} -l app=lego-apps"
echo "  kubectl get services -n ${NAMESPACE}"
echo ""
echo "View logs with:"
echo "  kubectl logs -n ${NAMESPACE} -l app=lego-apps --all-containers=true -f"
echo ""
echo "Get service URLs:"
echo "  kubectl get services -n ${NAMESPACE}"

