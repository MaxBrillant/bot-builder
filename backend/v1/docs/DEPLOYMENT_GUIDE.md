# Deployment Guide

This guide covers deploying Bot Builder to a production server with automated CI/CD.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        YOUR SERVER                          │
│                                                             │
│  ┌─────────┐                                                │
│  │  Caddy  │ ← Handles HTTPS, routes traffic                │
│  └────┬────┘                                                │
│       │                                                     │
│       ├── frontend.ndash.my ──→ Frontend (React)            │
│       │                                                     │
│       └── api.frontend.ndash.my ──→ API (FastAPI)           │
│                                      │                      │
│                                      ├── PostgreSQL         │
│                                      ├── Redis              │
│                                      ├── Evolution API      │
│                                      ├── Prometheus         │
│                                      └── Grafana            │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- A VPS (Ubuntu 22.04+ recommended)
- A domain name
- GitHub repository

---

## Step 1: Server Setup

### 1.1 Install Docker

```bash
ssh root@YOUR_SERVER_IP

# Install Docker
curl -fsSL https://get.docker.com | sh

# Verify installation
docker --version
docker compose version
```

### 1.2 Open Firewall Ports

```bash
ufw allow 22    # SSH
ufw allow 80    # HTTP
ufw allow 443   # HTTPS
ufw enable
```

### 1.3 Clone the Repository

```bash
cd /root
git clone https://github.com/YOUR_USERNAME/bot-builder.git
cd bot-builder/backend/v1
```

### 1.4 Set Up Git Deploy Key

This allows the server to pull code from GitHub:

```bash
# Generate deploy key
ssh-keygen -t ed25519 -C "server-deploy" -f ~/.ssh/github_deploy -N ""

# Configure git to use this key
echo -e "Host github.com\n  IdentityFile ~/.ssh/github_deploy" >> ~/.ssh/config

# Add GitHub to known hosts
ssh-keyscan github.com >> ~/.ssh/known_hosts

# Show the public key
cat ~/.ssh/github_deploy.pub
```

Add this key to GitHub:
1. Go to **GitHub → Your repo → Settings → Deploy keys → Add deploy key**
2. Paste the public key
3. Name it "Server Deploy"
4. Click "Add key"

Switch the remote to SSH:

```bash
git remote set-url origin git@github.com:YOUR_USERNAME/bot-builder.git

# Test it works
git pull origin main
```

---

## Step 2: DNS Configuration

Add these DNS records at your domain registrar (e.g., Namecheap → Advanced DNS):

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | frontend | YOUR_SERVER_IP | Automatic |
| A | api.frontend | YOUR_SERVER_IP | Automatic |

DNS propagation can take up to 24 hours, but usually completes within minutes.

---

## Step 3: Environment Configuration

### 3.1 Create Production .env

```bash
cd /root/bot-builder/backend/v1
nano .env
```

Paste your production configuration:

```bash
# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
DATABASE__URL=postgresql+asyncpg://botbuilder:YOUR_DB_PASSWORD@db:5432/botbuilder
DATABASE__POOL_SIZE=20
DATABASE__MAX_OVERFLOW=40
DATABASE__ECHO=false

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================
REDIS__URL=redis://redis:6379/0
REDIS__ENABLED=true
REDIS__SOCKET_TIMEOUT=5
REDIS__SOCKET_CONNECT_TIMEOUT=2
REDIS__MAX_RECONNECT_ATTEMPTS=5
REDIS__RECONNECT_BACKOFF_CAP=30

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================
CACHE__FLOW_TTL=3600
CACHE__SESSION_TTL=1800

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
SECURITY__SECRET_KEY=YOUR_SECRET_KEY
SECURITY__ENCRYPTION_KEY=YOUR_ENCRYPTION_KEY
SECURITY__ALGORITHM=HS256
SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES=1440
SECURITY__BCRYPT_ROUNDS=12

# =============================================================================
# GOOGLE OAUTH CONFIGURATION
# =============================================================================
GOOGLE__CLIENT_ID=your-google-client-id
GOOGLE__CLIENT_SECRET=your-google-client-secret
GOOGLE__REDIRECT_URI=https://api.frontend.ndash.my/auth/google/callback

# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================
RATE_LIMIT__WEBHOOK_MAX=30
RATE_LIMIT__WEBHOOK_WINDOW=60
RATE_LIMIT__USER_MAX=100
RATE_LIMIT__USER_WINDOW=60
RATE_LIMIT__REGISTER_MAX=3
RATE_LIMIT__REGISTER_WINDOW=3600
RATE_LIMIT__LOGIN_MAX=5
RATE_LIMIT__LOGIN_WINDOW=900

# =============================================================================
# HTTP CLIENT CONFIGURATION
# =============================================================================
HTTP_CLIENT__TIMEOUT=30.0
HTTP_CLIENT__MAX_CONNECTIONS=100
HTTP_CLIENT__MAX_KEEPALIVE=20

# =============================================================================
# FLOW CONSTRAINTS CONFIGURATION
# =============================================================================
FLOW_CONSTRAINTS__MAX_FLOW_SIZE=1048576
FLOW_CONSTRAINTS__MAX_AUTO_PROGRESSION=10
FLOW_CONSTRAINTS__SESSION_TIMEOUT_MINUTES=30

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================
app_name=Bot Builder
app_version=1.0.0
environment=production
debug=false
base_url=https://api.frontend.ndash.my
frontend_url=https://frontend.ndash.my
allowed_origins=https://frontend.ndash.my

# =============================================================================
# EVOLUTION API CONFIGURATION
# =============================================================================
EVOLUTION_API__ENABLED=true
EVOLUTION_API__URL=http://evolution-api:8080
EVOLUTION_API__API_KEY=YOUR_EVOLUTION_API_KEY
EVOLUTION_API__WEBHOOK_BASE_URL=http://api:8000

# =============================================================================
# OBSERVABILITY CONFIGURATION
# =============================================================================
OBSERVABILITY__SENTRY_DSN=your-sentry-dsn
OBSERVABILITY__SENTRY_TRACES_SAMPLE_RATE=0.1
OBSERVABILITY__PROMETHEUS_ENABLED=true

# =============================================================================
# FRONTEND BUILD CONFIGURATION
# =============================================================================
VITE_API_URL=https://api.frontend.ndash.my

# =============================================================================
# DOCKER COMPOSE VARIABLES
# =============================================================================
DB_PASSWORD=YOUR_DB_PASSWORD
SECRET_KEY=YOUR_SECRET_KEY
ENCRYPTION_KEY=YOUR_ENCRYPTION_KEY
EVOLUTION_API_KEY=YOUR_EVOLUTION_API_KEY
GRAFANA_PASSWORD=YOUR_GRAFANA_PASSWORD
ENVIRONMENT=production
DEBUG=false
```

### 3.2 Generate Secure Keys

Run these locally and paste the values into your .env:

```bash
# SECRET_KEY
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'

# ENCRYPTION_KEY
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

# EVOLUTION_API_KEY
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'

# DB_PASSWORD & GRAFANA_PASSWORD
python3 -c 'import secrets; print(secrets.token_urlsafe(16))'
```

---

## Step 4: Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services → Credentials**
3. Edit your OAuth 2.0 Client
4. Add to **Authorized redirect URIs**:
   ```
   https://api.frontend.ndash.my/auth/google/callback
   ```
5. Add to **Authorized JavaScript origins**:
   ```
   https://frontend.ndash.my
   ```

---

## Step 5: Start the Application

```bash
cd /root/bot-builder/backend/v1

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api
```

Caddy automatically obtains SSL certificates from Let's Encrypt.

---

## Step 6: CI/CD Setup (GitHub Actions)

### 6.1 Generate Deployment SSH Key (Local Machine)

```bash
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy -N ""
```

### 6.2 Add Public Key to Server

```bash
# View the public key
cat ~/.ssh/github_deploy.pub

# Add to server
ssh root@YOUR_SERVER_IP "echo 'PASTE_PUBLIC_KEY_HERE' >> ~/.ssh/authorized_keys"
```

### 6.3 Test SSH Connection

```bash
ssh -i ~/.ssh/github_deploy root@YOUR_SERVER_IP "echo 'Connection works!'"
```

### 6.4 Add GitHub Secrets

Go to **GitHub → Your repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|-------|
| `SERVER_HOST` | Your server IP (e.g., `143.198.123.45`) |
| `SERVER_USER` | `root` |
| `SERVER_SSH_KEY` | Contents of `~/.ssh/github_deploy` (private key) |
| `APP_PATH` | `/root/bot-builder/backend/v1` |

### 6.5 Workflow File

The workflow is at `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          port: 22
          script: |
            cd ${{ secrets.APP_PATH }}

            # Pull latest code
            git pull origin main

            # Build and restart containers
            docker compose pull
            docker compose build --no-cache api frontend
            docker compose up -d

            # Clean up old images
            docker image prune -f

            # Health check
            sleep 15
            curl -f http://localhost:8000/health || exit 1

            echo "Deployment complete!"
```

Now every push to `main` automatically deploys to production.

---

## Step 7: Verify Deployment

### Check Services

```bash
# All containers running
docker compose ps

# API health
curl https://api.frontend.ndash.my/health

# View logs
docker compose logs -f api
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend | https://frontend.ndash.my |
| API | https://api.frontend.ndash.my |
| API Docs | https://api.frontend.ndash.my/docs |
| Grafana | http://YOUR_SERVER_IP:3001 |
| Prometheus | http://YOUR_SERVER_IP:9090 |

---

## Troubleshooting

### Git Pull Fails with "could not read Username"

The server is using HTTPS instead of SSH for git:

```bash
cd /root/bot-builder
git remote set-url origin git@github.com:YOUR_USERNAME/bot-builder.git
```

Make sure the deploy key is set up (see Step 1.4).

### "no such service: frontend"

The server has old code. Fix git pull first, then:

```bash
git pull origin main
docker compose up -d
```

### Caddy Not Getting SSL Certificate

- Verify DNS is pointing to your server: `dig frontend.ndash.my`
- Check Caddy logs: `docker compose logs caddy`
- Ensure ports 80 and 443 are open

### Container Keeps Restarting

Check logs for the specific container:

```bash
docker compose logs api
docker compose logs frontend
```

### Health Check Fails

```bash
# Check if API is running
docker compose ps

# Check API logs
docker compose logs api

# Test health endpoint directly
curl http://localhost:8000/health
```

### Database Connection Issues

```bash
# Check if database is healthy
docker compose ps db

# View database logs
docker compose logs db

# Test connection
docker compose exec db psql -U botbuilder -d botbuilder -c "SELECT 1"
```

---

## Maintenance

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
```

### Restart Services

```bash
# Restart everything
docker compose restart

# Restart specific service
docker compose restart api
```

### Update Manually

```bash
cd /root/bot-builder/backend/v1
git pull origin main
docker compose build --no-cache api frontend
docker compose up -d
```

### Backup Database

```bash
docker compose exec db pg_dump -U botbuilder botbuilder > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
cat backup_20240101.sql | docker compose exec -T db psql -U botbuilder botbuilder
```

---

## Security Checklist

- [ ] Strong passwords in .env (use generated keys)
- [ ] .env file is gitignored
- [ ] Firewall configured (only 22, 80, 443 open)
- [ ] `debug=false` in production
- [ ] `environment=production` set
- [ ] Google OAuth redirect URIs updated
- [ ] Grafana password changed from default
- [ ] SSH key authentication (no password login)

---

## Monitoring

### Grafana Dashboard

Access Grafana at `http://YOUR_SERVER_IP:3001`

Default credentials:
- Username: `admin`
- Password: Value of `GRAFANA_PASSWORD` in .env

Pre-configured dashboard: **Bot Builder API**

### Metrics Available

- Request rate (req/sec)
- Request latency (p50, p95, p99)
- Requests by endpoint
- Response status codes
- Success rate
- Requests in progress

### Sentry Error Tracking

Errors are automatically reported to Sentry. View them at [sentry.io](https://sentry.io).
