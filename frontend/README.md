# ⚛️ Zestora — Frontend

> React + TypeScript single-page application for the Zestora food ordering platform.

![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=flat-square&logo=vite&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-1.27-009639?style=flat-square&logo=nginx&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Multi--stage-2496ED?style=flat-square&logo=docker&logoColor=white)

---

## 🌟 Features

| Feature | Description |
|---|---|
| **Instant Search** | Real-time food item search with debounced filtering |
| **Cart Management** | Add/remove items, quantity controls, persistent cart state |
| **Promo Codes** | Discount code support (`AWS20` → 20% off) |
| **Order Tracking** | 4-step real-time order status tracker |
| **Revenue Dashboard** | Live order and revenue metrics display |
| **Responsive Design** | Mobile-first layout with TailwindCSS |

---

## 🛠️ Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| **React** | 18 | UI component framework |
| **TypeScript** | 5 | Type-safe JavaScript |
| **Vite** | 5 | Build tool and dev server |
| **React Router DOM** | v6 | Client-side routing |
| **TailwindCSS** | 3 | Utility-first CSS framework |
| **Nginx** | 1.27-alpine | Production static file serving |

---

## 🏗️ Docker — Multi-Stage Build

The frontend uses a **two-stage Docker build** to keep the final image minimal:

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build          # → produces /app/dist

# Stage 2: Serve
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**Final image size:** ~25 MB (alpine-based, no Node.js runtime in production)

---

## 🌐 Nginx Configuration

`nginx.conf` handles two key responsibilities:

1. **SPA Routing** — All routes fall back to `index.html` so React Router handles navigation:
   ```nginx
   try_files $uri $uri/ /index.html;
   ```

2. **API Reverse Proxy** — Forwards `/api` requests to the backend container:
   ```nginx
   location /api/ {
       proxy_pass http://backend:5000/api/;
   }
   ```

3. **Monitoring Subpath Proxies** — Routes `/prometheus/` and `/grafana/` to their respective containers.

---

## 🚀 Getting Started

### Local Development

```bash
# Install dependencies
npm ci

# Start development server (hot reload)
npm run dev
# → http://localhost:5173

# Type check
npm run type-check

# Lint
npm run lint
```

### Production Build

```bash
# Build for production
npm run build
# → outputs to dist/

# Preview production build locally
npm run preview
```

### Docker Build

```bash
# Build the Docker image
docker build -t zestora-frontend:latest .

# Run the container
docker run -p 80:80 zestora-frontend:latest
# → http://localhost
```

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── Cart/
│   │   ├── FoodCard/
│   │   ├── OrderTracker/
│   │   └── SearchBar/
│   ├── pages/             # Route-level page components
│   ├── types/             # TypeScript type definitions
│   ├── utils/             # Helper functions
│   ├── App.tsx            # Root component + routing
│   └── main.tsx           # Entry point
├── public/
│   └── images/            # Static assets
├── nginx.conf             # Nginx reverse proxy config
├── Dockerfile             # Multi-stage Docker build
├── vite.config.ts         # Vite configuration
├── tsconfig.json          # TypeScript configuration
└── package.json
```

---

## 🔗 API Integration

The frontend communicates with the Flask backend through the Nginx reverse proxy:

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Service health check |
| `/api/menu` | GET | Fetch all menu items |
| `/api/orders` | POST | Place a new order |
| `/api/orders/:id` | GET | Get order status |

---

## 🔧 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `/api` | Backend API base URL |

In production, the Nginx proxy handles all `/api` routing, so no explicit base URL is needed.

---

## 📦 Part of the Zestora DevOps Stack

This frontend is one part of a full DevOps ecosystem:

```
GitHub Push → GitHub Actions → Trivy Scan → SSH Deploy to EC2
                ↓
            Jenkins CI/CD (8 stages) → Docker Build → ECR Push → EC2 Deploy
                ↓
         Prometheus + Grafana monitoring all containers on EC2
```

> See the [root README](../README.md) for the full architecture and all live links.
