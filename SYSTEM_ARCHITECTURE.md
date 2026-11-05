# 🏛️ Zestora — System Architecture

> A structured, visual breakdown of every layer of the Zestora food ordering platform — from the browser to the database, and from local Docker to AWS cloud.

---

## 📐 Table of Contents

1. [Architecture at a Glance](#1-architecture-at-a-glance)
2. [The 4 Tiers Explained](#2-the-4-tiers-explained)
   - [Client Tier — React SPA](#21-client-tier--react-spa)
   - [Edge Tier — Nginx](#22-edge-tier--nginx)
   - [Application Tier — Flask API](#23-application-tier--flask-api)
   - [Persistence Tier — MongoDB](#24-persistence-tier--mongodb)
3. [Request Flow — Step by Step](#3-request-flow--step-by-step)
4. [Database Schema](#4-database-schema)
5. [Security Architecture](#5-security-architecture)
6. [Container Network Map](#6-container-network-map)
7. [Scalability Roadmap](#7-scalability-roadmap)

---

## 1. Architecture at a Glance

Zestora is a **4-tier containerized web application** running on AWS EC2. Each tier lives in its own Docker container, communicating over a private internal Docker network (`zestora_net`). Only Nginx is exposed to the public internet.

```mermaid
flowchart TD
    USER(["👤 Customer\n(Browser)"])
    ADMIN(["👨‍🍳 Kitchen Staff\n(Browser)"])

    subgraph EDGE["🌐 Edge Tier — Public (Port 80)"]
        NGINX["Nginx 1.27\nReverse Proxy + Static Server"]
    end

    subgraph APP["⚙️ Application Tier — Private Docker Network"]
        GUNICORN["Gunicorn\nWSGI Server"]
        FLASK["Flask REST API\n(Port 5000)"]
        COUPON["🎟️ Coupon Engine\nAWS20 / CLOUD50"]
        TRACKER["📍 Order Tracker\n4-step live status"]
        REVIEWS["⭐ Reviews Module\n1–5 star ratings"]
    end

    subgraph DB["🗄️ Persistence Tier — Private Docker Network"]
        MONGO["MongoDB 7.0\n(Port 27017)"]
        VOL[("💾 Docker Volume\nmongo_data")]
    end

    subgraph MON["📊 Monitoring Tier"]
        PROM["Prometheus\n(:9090)"]
        GRAF["Grafana\n(:3002)"]
    end

    USER -->|"HTTP requests"| NGINX
    ADMIN -->|"KDS Dashboard"| NGINX
    NGINX -->|"Static files (JS/CSS)"| NGINX
    NGINX -->|"Proxy /api/*"| GUNICORN
    GUNICORN --> FLASK
    FLASK --> COUPON
    FLASK --> TRACKER
    FLASK --> REVIEWS
    FLASK -->|"PyMongo"| MONGO
    MONGO --- VOL
    PROM -->|"scrape metrics"| FLASK
    GRAF -->|"query"| PROM
```

---

## 2. The 4 Tiers Explained

---

### 2.1 Client Tier — React SPA

> What the user sees and interacts with in their browser.

| Property | Detail |
|---|---|
| **Framework** | React 18 + TypeScript |
| **Build Tool** | Vite 5 (outputs optimized `dist/` bundle) |
| **Routing** | React Router DOM v6 (client-side, no page reloads) |
| **Styling** | TailwindCSS + custom CSS |
| **State** | React hooks — `useState`, `useEffect`, `useMemo`, `useCallback` |

**Key Features:**

| Feature | How it works |
|---|---|
| 🔍 **Instant Search** | Debounced input filters dishes by name, category, description, and tag in real-time |
| 🛒 **Cart Management** | Optimistic UI updates — no page reload needed when adding/removing items |
| 🎟️ **Promo Codes** | Enter `AWS20` → 20% off applied instantly with real-time subtotal recalculation |
| 📍 **Order Tracker** | 4-step progress bar: `Confirmed → Kitchen Preparing → Out for Delivery → Delivered` |
| 👨‍🍳 **Kitchen Dashboard (KDS)** | Staff view: incoming tickets, revenue metrics, fulfillment state updates |
| ⭐ **Reviews** | 1–5 star rating modal per dish, submitted to the backend API |

---

### 2.2 Edge Tier — Nginx

> The gatekeeper. All public internet traffic hits Nginx first.

| Property | Detail |
|---|---|
| **Image** | `nginx:1.27-alpine` (~25 MB) |
| **Port** | `80` (public) |
| **Config file** | `frontend/nginx.conf` |

**Responsibilities:**

```
┌─────────────────────────────────────────────────────────┐
│                       NGINX ROUTER                       │
│                                                         │
│   GET /               → serve dist/index.html           │
│   GET /assets/*       → serve JS/CSS (1-year cache)     │
│   GET /api/*          → proxy → backend:5000            │
│   GET /prometheus/*   → proxy → prometheus:9090         │
│   GET /grafana/*      → proxy → grafana:3002            │
│   Any unknown route   → fallback to index.html (SPA)    │
└─────────────────────────────────────────────────────────┘
```

**Security headers Nginx adds to every response:**
```nginx
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Cache-Control: no-cache (for index.html only)
```

---

### 2.3 Application Tier — Flask API

> The brain. Handles all business logic, validation, and database operations.

| Property | Detail |
|---|---|
| **Language** | Python 3.11 |
| **Framework** | Flask |
| **WSGI Server** | Gunicorn (multi-threaded workers) |
| **Port** | `5000` (internal only — never exposed publicly) |
| **Auth** | Stateless JWT (HMAC-SHA256), passwords hashed with `scrypt` |

**API Endpoints:**

| Method | Endpoint | Description | Response |
|---|---|---|---|
| `GET` | `/api/health` | Service health check | `{"status":"ok","db":"ok"}` |
| `GET` | `/api/foods` | Fetch all menu items | `200 OK` — JSON array |
| `POST` | `/api/orders` | Place a new order | `201 Created` — order ID + status |
| `GET` | `/api/orders/:id/track` | Live order status | `200 OK` — steps + ETA |
| `POST` | `/api/coupons/validate` | Validate promo code | `200 OK` — discount amount |
| `POST` | `/api/reviews` | Submit a food review | `201 Created` |

**HTTP Status Code Convention:**

| Code | Meaning |
|---|---|
| `200` | Successful retrieval or update |
| `201` | Resource created (order, review) |
| `400` | Bad request — validation failure or invalid coupon |
| `401` | Unauthorized — missing or invalid JWT |
| `404` | Not found — unknown order ID or food item |

---

### 2.4 Persistence Tier — MongoDB

> The data store. Completely hidden from the public internet.

| Property | Detail |
|---|---|
| **Engine** | MongoDB 7.0 Community |
| **Port** | `27017` (internal Docker network only) |
| **Storage** | Docker named volume `mongo_data` (backed by EBS gp3 on EC2) |
| **Access** | Only reachable by the Flask backend within `zestora_net` |
| **Collections** | `users`, `foods`, `orders`, `reviews` |

> ⚠️ Port 27017 is **never** exposed to the host or the public internet. It is bound strictly to the internal Docker bridge network.

---

## 3. Request Flow — Step by Step

The following sequence covers the full customer journey from landing on the site to tracking their order.

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Customer (Browser)
    participant Nginx as 🌐 Nginx (Port 80)
    participant Flask as ⚙️ Flask (Port 5000)
    participant Mongo as 🗄️ MongoDB (Port 27017)

    Note over User,Nginx: Step 1 — Page Load
    User->>Nginx: GET /
    Nginx-->>User: 200 OK (index.html + JS bundle)

    Note over User,Mongo: Step 2 — Browse Menu
    User->>Nginx: GET /api/foods
    Nginx->>Flask: Proxy GET /api/foods
    Flask->>Mongo: foods_col.find({})
    Mongo-->>Flask: Array of dishes (Tamil & International)
    Flask-->>Nginx: 200 OK (JSON)
    Nginx-->>User: Render food catalog + search bar

    Note over User,Flask: Step 3 — Apply Promo Code
    User->>Nginx: POST /api/coupons/validate { code: "AWS20", subtotal: 500 }
    Nginx->>Flask: Proxy POST
    Flask-->>Nginx: 200 OK { valid: true, discount: 100, final_total: 400 }
    Nginx-->>User: Cart updates — ₹100 discount applied ✅

    Note over User,Mongo: Step 4 — Place Order
    User->>Nginx: POST /api/orders { items, address, payment_method }
    Nginx->>Flask: Proxy POST
    Flask->>Mongo: orders_col.insert_one(order_doc)
    Mongo-->>Flask: ObjectId assigned
    Flask-->>Nginx: 201 Created { order_id, status: "confirmed", eta: 35 }
    Nginx-->>User: 4-step order tracker appears 📍

    Note over User,Mongo: Step 5 — Track Order
    User->>Nginx: GET /api/orders/:id/track
    Nginx->>Flask: Proxy GET
    Flask->>Mongo: orders_col.find_one({ _id })
    Mongo-->>Flask: Current order state
    Flask-->>Nginx: 200 OK { step: "preparing", eta_minutes: 20 }
    Nginx-->>User: Progress bar advances to Step 2 🍳
```

---

## 4. Database Schema

```mermaid
erDiagram
    USERS ||--o{ ORDERS : places
    FOODS  ||--o{ REVIEWS : receives
    ORDERS ||--|{ ORDER_ITEMS : contains

    USERS {
        string _id        PK  "MongoDB ObjectId"
        string name           "Full name"
        string email          "Unique email"
        string password       "Hashed (scrypt)"
        date   created_at     "Registration time"
    }

    FOODS {
        string _id        PK  "MongoDB ObjectId"
        string name           "e.g. Ambur Dum Biryani"
        string category       "South Indian / Burgers / etc."
        float  price          "Price in INR"
        string image          "CDN URL with local fallback"
        string description    "Culinary description"
        string rating         "Display rating"
        string tag            "Badge e.g. Tamil Bestseller"
        string color          "Hex tint for card"
    }

    ORDERS {
        string _id          PK  "MongoDB ObjectId"
        string user_id      FK  "→ USERS._id"
        string user_name        "Customer name"
        string address          "Delivery address"
        string payment_method   "UPI / Cash / Card"
        string coupon_code      "Applied code or null"
        float  discount         "Amount deducted"
        float  total            "Final payable amount"
        string status           "confirmed | preparing | out_for_delivery | delivered"
        int    eta_minutes      "Estimated delivery time"
        date   created_at       "Order timestamp"
        date   updated_at       "Last status change"
    }

    ORDER_ITEMS {
        string name       "Food item name"
        float  price      "Unit price"
        int    quantity   "Count ordered"
    }

    REVIEWS {
        string _id       PK  "MongoDB ObjectId"
        string food_id   FK  "→ FOODS._id"
        string user_name     "Reviewer name"
        int    rating        "1 to 5 stars"
        string comment       "Text feedback"
        date   created_at    "Timestamp"
    }
```

---

## 5. Security Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                               │
│                                                                      │
│  🌐 NETWORK LAYER                                                    │
│     ✅ MongoDB port 27017 — internal Docker network ONLY             │
│     ✅ Backend port 5000  — internal Docker network ONLY             │
│     ✅ Only Nginx port 80 is publicly reachable                      │
│                                                                      │
│  🛡️ DEVSECOPS — TRIVY                                               │
│     ✅ Filesystem scan (source code + dependencies) — 0 Critical     │
│     ✅ Container image scan (OS packages) — 0 Critical               │
│     📄 Full report: reports/trivy-security-audit.md                  │
│                                                                      │
│  🔐 AUTHENTICATION                                                   │
│     ✅ Stateless JWT tokens (HMAC-SHA256 signed)                     │
│     ✅ Passwords hashed with scrypt + random salt                    │
│     ✅ Backend Gunicorn runs as non-root user (appuser)              │
│                                                                      │
│  🌍 HTTP HEADERS (Nginx)                                             │
│     ✅ X-Frame-Options: SAMEORIGIN                                   │
│     ✅ X-Content-Type-Options: nosniff                               │
│     ✅ X-XSS-Protection: 1; mode=block                              │
│     ✅ Referrer-Policy: strict-origin-when-cross-origin              │
│                                                                      │
│  ☁️ AWS IAM                                                          │
│     ✅ EC2 instance profile with least-privilege ECR access          │
│     ✅ No hardcoded AWS credentials in source code                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 6. Container Network Map

All 5 production containers run on the same Docker bridge network `zestora_net`. Only Nginx has an external port binding.

```
Internet
   │
   │ Port 80 (public)
   ▼
┌─────────────────────────────────────────────────────────┐
│               Docker Network: zestora_net                │
│                                                         │
│  ┌────────────────┐    ┌────────────────────────────┐   │
│  │   nginx:1.27   │───▶│   backend:python:3.11-slim │   │
│  │   Port 80 ✅   │    │   Port 5000 (internal)     │   │
│  │   (public)     │    └────────────┬───────────────┘   │
│  └────────────────┘                 │ PyMongo            │
│                                     ▼                   │
│                         ┌───────────────────────┐       │
│                         │   mongo:7.0           │       │
│                         │   Port 27017 (internal│       │
│                         │   + volume: mongo_data│       │
│                         └───────────────────────┘       │
│                                                         │
│  ┌────────────────┐    ┌────────────────────────────┐   │
│  │  prometheus    │───▶│   grafana                  │   │
│  │  Port 9090     │    │   Port 3002                │   │
│  │  (via /prom..) │    │   (via /grafana/)          │   │
│  └───────┬────────┘    └────────────────────────────┘   │
│          │ scrape                                        │
│          └──────▶ backend + nginx metrics               │
└─────────────────────────────────────────────────────────┘
```

**Docker Compose files:**
| File | Purpose |
|---|---|
| `docker-compose.yml` | Local development (with hot reload) |
| `docker-compose.prod.yml` | Production deployment on EC2 |
| `jenkins/docker-compose.jenkins.yml` | Jenkins container (port 8080) |

---

## 7. Scalability Roadmap

The current single-EC2 architecture can grow into a full AWS production setup:

```mermaid
flowchart LR
    NOW["🟢 Current\nSingle EC2 t3.micro\n5 Docker containers"] -->|Scale out| NEXT

    subgraph NEXT["⚡ Next: AWS Managed Services"]
        ALB["Application Load Balancer\n(multi-EC2 auto scaling)"]
        EKS["AWS EKS\n(Kubernetes HPA ready\n— k8s/ manifests exist)"]
        DOCDB["Amazon DocumentDB\n(MongoDB-compatible, multi-AZ)"]
        CF["CloudFront CDN\n(static assets globally cached)"]
        ECR2["AWS ECR\n(versioned container images)"]
    end
```

| Current | Future Upgrade |
|---|---|
| Single EC2 | EC2 Auto Scaling Group behind ALB |
| Docker Compose | AWS EKS (Kubernetes manifests are **already written** in `k8s/`) |
| Local MongoDB container | Amazon DocumentDB or MongoDB Atlas (multi-AZ) |
| Nginx static serving | Amazon CloudFront CDN + S3 |
| Local Docker builds | AWS ECR + GitHub Actions push on merge |

---

> 📌 **Related docs:**
> [`README.md`](./README.md) · [`DEVOPS_ARCHITECTURE.md`](./DEVOPS_ARCHITECTURE.md) · [`JENKINS_WORKFLOW.md`](./JENKINS_WORKFLOW.md) · [`k8s/README.md`](./k8s/README.md)
