# ☸️ Zestora — Kubernetes (K8s) Production Architecture

This directory contains enterprise-grade Kubernetes manifests for orchestrating the Zestora food delivery platform on **AWS EKS (Elastic Kubernetes Service)** or local Kubernetes clusters (Minikube / Kind).

---

## 📂 Manifest Inventory

| File | Resource Kind | Purpose |
| :--- | :--- | :--- |
| **`namespace.yaml`** | `Namespace` | Creates isolated `zestora` namespace with environment metadata. |
| **`configmap-secrets.yaml`** | `ConfigMap`, `Secret` | Injects environment configurations and encoded JWT / MongoDB credentials. |
| **`mongo-statefulset.yaml`** | `StatefulSet`, `Headless Service` | Stateful database storage using `PersistentVolumeClaim` (5Gi) ensuring data persistence across pod restarts. |
| **`backend-deployment.yaml`** | `Deployment` (3 Replicas), `Service` | Python Flask API with non-root security context (`UID 10001`), `livenessProbe`, and `readinessProbe`. |
| **`frontend-deployment.yaml`** | `Deployment` (2 Replicas), `Service` | Nginx + React SPA with zero-downtime RollingUpdate strategy. |
| **`services-upstream.yaml`** | `Service` (ClusterIP) | Internal DNS mappings for Nginx reverse proxy upstream routing. |
| **`ingress.yaml`** | `Ingress` | NGINX Ingress Controller routing `/api` traffic to backend and `/` to frontend. |
| **`hpa.yaml`** | `HorizontalPodAutoscaler` (v2) | Automatically scales backend and frontend pods from **2 to 10 replicas** based on 70% CPU and 80% Memory thresholds. |

---

## 🚀 Deployment Instructions

### 1. Start Minikube (D: Drive Optimized)
```bash
# Sets Minikube home to D: drive (0 bytes on C:)
set MINIKUBE_HOME=D:\minikube
minikube start --driver=docker --memory=2048m --cpus=2

# Enable metrics-server for HPA autoscaling
minikube addons enable metrics-server
```

### 2. Deploy All Resources to Cluster
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
```

### 3. Verify Pods & Services
```bash
kubectl get pods,deployments,statefulset,svc,pvc,hpa -n zestora -o wide
```

### 4. Access Frontend via Minikube
```bash
# Open frontend directly in browser
minikube service zestora-frontend -n zestora

# Or open official visual Kubernetes Web Dashboard
minikube dashboard
```

---

## 🟢 Live Deployment Verification (Minikube v1.39.0 / v1.37.0 Control Plane)

All 6 pods running 100% healthy inside the `zestora` namespace:

```text
NAME                                READY   STATUS    RESTARTS   AGE
zestora-backend-66544c5d4b-82kbh    1/1     Running   0          3m
zestora-backend-66544c5d4b-mcb8x    1/1     Running   0          3m
zestora-backend-66544c5d4b-r9f2n    1/1     Running   0          3m
zestora-frontend-588fdf6f6b-b9gk4   1/1     Running   0          3m
zestora-frontend-588fdf6f6b-jjp2d   1/1     Running   0          3m
zestora-mongo-0                     1/1     Running   0          3m
```

Persistent Volume Claims:
```text
NAME                               STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
mongo-data-zestora-mongo-0         Bound    pvc-466da5b2-c6ad-4b13-9117-5adcbe43ee18   5Gi        RWO            standard
```

Horizontal Pod Autoscaler (HPA):
```text
NAME                   REFERENCE                     TARGETS                  MINPODS   MAXPODS   REPLICAS
zestora-backend-hpa    Deployment/zestora-backend    cpu: 70%, memory: 80%    2         10        3
zestora-frontend-hpa   Deployment/zestora-frontend   cpu: 70%                 2         10        2
```

