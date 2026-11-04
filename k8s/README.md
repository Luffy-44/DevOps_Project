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
| **`ingress.yaml`** | `Ingress` | NGINX Ingress Controller routing `/api` traffic to backend and `/` to frontend. |
| **`hpa.yaml`** | `HorizontalPodAutoscaler` (v2) | Automatically scales backend and frontend pods from **2 to 10 replicas** based on 70% CPU and 80% Memory thresholds. |

---

## 🚀 Deployment Instructions

### 1. Deploy All Resources to Cluster
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/
```

### 2. Verify Pods & Services
```bash
kubectl get pods -n zestora -o wide
kubectl get svc -n zestora
kubectl get hpa -n zestora
```

### 3. Check Autoscaling Status
```bash
kubectl describe hpa zestora-backend-hpa -n zestora
```
