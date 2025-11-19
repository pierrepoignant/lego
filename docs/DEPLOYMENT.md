# LEGO Apps Deployment Guide

This guide covers building a Docker image containing both the Streamlit and Flask applications, and deploying it to a Kubernetes cluster.

## Architecture

The Docker image contains:
- **Streamlit app** (port 8501) - Financial dashboard
- **Flask app** (port 5003) - Brand management interface

Both applications connect to a MySQL database.

## Prerequisites

- Docker installed locally
- Access to a Docker registry (Docker Hub, GCR, ECR, etc.)
- kubectl configured with access to your Kubernetes cluster
- A MySQL database accessible from your Kubernetes cluster

## Step 1: Build the Docker Image

```bash
# Build the image
docker build -t lego-apps:latest .

# Tag for your registry
docker tag lego-apps:latest your-registry/lego-apps:latest

# Push to registry
docker push your-registry/lego-apps:latest
```

## Step 2: Test Locally (Optional)

Test the Docker image locally before deploying:

```bash
docker run -p 8501:8501 -p 5003:5003 \
  -e DB_HOST=your-db-host \
  -e DB_PORT=3306 \
  -e DB_USER=your-user \
  -e DB_PASSWORD=your-password \
  -e DB_NAME=lego \
  lego-apps:latest
```

Access:
- Streamlit: http://localhost:8501
- Flask: http://localhost:5003

## Step 3: Configure Kubernetes

### Update Configuration Files

1. **Update `k8s/deployment.yaml`**:
   - Replace `your-registry/lego-apps:latest` with your actual image path
   - Adjust resource limits if needed

2. **Update `k8s/configmap.yaml`**:
   - Set `db_host` to your MySQL service name or external IP
   - Update `db_port` and `db_name` if different

3. **Update `k8s/secret.yaml`**:
   - Set your database username and password
   - **Important**: For production, create secrets securely:
   ```bash
   kubectl create secret generic lego-secrets \
     --from-literal=db_user=your-user \
     --from-literal=db_password=your-password \
     -n essorcloud
   ```

4. **Update `k8s/service.yaml`**:
   - Change service type if needed:
     - `LoadBalancer` - for cloud providers (AWS, GCP, Azure)
     - `NodePort` - for bare-metal or local clusters
     - `ClusterIP` - internal access only, use with Ingress

5. **Update `k8s/ingress.yaml`** (optional):
   - Set your domain names
   - Configure ingress controller annotations

## Step 4: Deploy to Kubernetes

```bash
# Create namespace (optional)
kubectl create namespace essorcloud

# Apply configurations
kubectl apply -f k8s/configmap.yaml -n essorcloud
kubectl apply -f k8s/secret.yaml -n essorcloud
kubectl apply -f k8s/deployment.yaml -n essorcloud
kubectl apply -f k8s/service.yaml -n essorcloud

# Optional: Apply ingress
kubectl apply -f k8s/ingress.yaml -n essorcloud
```

## Step 5: Verify Deployment

```bash
# Check pod status
kubectl get pods -l app=lego-apps -n essorcloud

# Check services
kubectl get services -n essorcloud

# View logs
kubectl logs -l app=lego-apps --all-containers=true -n essorcloud

# Check specific app logs
kubectl logs -l app=lego-apps -c lego-apps -n essorcloud
```

## Step 6: Access the Applications

### With LoadBalancer:
```bash
# Get external IPs
kubectl get services lego-streamlit
kubectl get services lego-flask
```

### With NodePort:
```bash
# Get node port
kubectl get services
# Access via: http://<node-ip>:<node-port>
```

### With Ingress:
Access via configured domain names:
- Streamlit: http://lego-dashboard.yourdomain.com
- Flask: http://lego-admin.yourdomain.com

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | MySQL database host | localhost |
| `DB_PORT` | MySQL database port | 3306 |
| `DB_USER` | Database username | root |
| `DB_PASSWORD` | Database password | (empty) |
| `DB_NAME` | Database name | lego |
| `FLASK_PORT` | Flask application port | 5003 |
| `FLASK_SECRET_KEY` | Flask secret key for sessions | (generated) |

## Scaling

Scale the deployment:
```bash
kubectl scale deployment lego-apps --replicas=3 -n essorcloud
```

## Updating

To deploy a new version:
```bash
# Build and push new image
docker build -t your-registry/lego-apps:v2 .
docker push your-registry/lego-apps:v2

# Update deployment
kubectl set image deployment/lego-apps lego-apps=your-registry/lego-apps:v2 -n essorcloud

# Or edit deployment.yaml and apply
kubectl apply -f k8s/deployment.yaml -n essorcloud
```

## Troubleshooting

### Pod not starting
```bash
kubectl describe pod <pod-name> -n essorcloud
kubectl logs <pod-name> -n essorcloud
```

### Database connection issues
```bash
# Check if database is accessible from pod
kubectl exec -it <pod-name> -n essorcloud -- ping <db-host>

# Verify environment variables
kubectl exec -it <pod-name> -n essorcloud -- env | grep DB_
```

### Check app health
```bash
# Streamlit health
kubectl exec -it <pod-name> -n essorcloud -- curl localhost:8501/_stcore/health

# Flask health
kubectl exec -it <pod-name> -n essorcloud -- curl localhost:5003/
```

## Production Considerations

1. **Security**:
   - Use strong database passwords
   - Set a secure `FLASK_SECRET_KEY`
   - Consider using a secrets management solution (Vault, AWS Secrets Manager, etc.)
   - Use TLS/HTTPS with proper certificates

2. **Database**:
   - Consider running MySQL in Kubernetes with StatefulSet
   - Or use a managed database service (RDS, Cloud SQL, etc.)
   - Ensure proper backups

3. **Monitoring**:
   - Add Prometheus metrics
   - Set up logging aggregation (ELK, Loki, etc.)
   - Configure alerts

4. **Resource Limits**:
   - Adjust CPU/memory requests and limits based on usage
   - Enable horizontal pod autoscaling if needed

5. **Storage**:
   - If apps need persistent storage, add PersistentVolumeClaims

## MySQL in Kubernetes (Optional)

If you want to deploy MySQL in the same cluster:

```yaml
# Example mysql-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql-service
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - containerPort: 3306
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secrets
              key: root-password
        - name: MYSQL_DATABASE
          value: lego
        volumeMounts:
        - name: mysql-storage
          mountPath: /var/lib/mysql
  volumeClaimTemplates:
  - metadata:
      name: mysql-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: mysql-service
spec:
  ports:
  - port: 3306
  selector:
    app: mysql
  clusterIP: None
```

## Clean Up

To remove the deployment:
```bash
kubectl delete -f k8s/ -n essorcloud
# Or delete the entire namespace
kubectl delete namespace essorcloud
```

## Support

For issues or questions, refer to:
- Kubernetes documentation: https://kubernetes.io/docs/
- Docker documentation: https://docs.docker.com/
- Streamlit documentation: https://docs.streamlit.io/
- Flask documentation: https://flask.palletsprojects.com/


