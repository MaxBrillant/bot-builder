# WhatsApp MVP Implementation - Production Updates Summary

## Overview

This document summarizes the key architectural changes for production-ready WhatsApp integration at **10 req/sec** scale.

---

## Key Decisions

### 1. **Use Celery + Redis**
- Target: 10 req/sec = 864,000 messages/day
- Requires reliable task queue with persistence
- Standard production pattern for distributed processing

### 2. **No Message Storage in Database**
- Don't store message content or stats in PostgreSQL
- Use Prometheus metrics for real-time counters
- Use structured logging (ELK/Datadog) for debugging
- Saves ~5GB/day of database storage

### 3. **Single Table Schema**
- Only `whatsapp_instances` table needed
- Track instance configuration and connection status
- All metrics via Prometheus + logging

---

## Database Schema (Simplified)

```sql
-- Only ONE table needed
CREATE TABLE whatsapp_instances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    bot_id UUID NOT NULL REFERENCES bots(bot_id) ON DELETE CASCADE,
    owner_user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,

    -- Evolution API config
    instance_name VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(50) UNIQUE,

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_primary BOOLEAN NOT NULL DEFAULT true,

    connected_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    disconnected_at TIMESTAMP,
    error_message TEXT,
    error_count INT NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_bot FOREIGN KEY (bot_id) REFERENCES bots(bot_id) ON DELETE CASCADE,
    CONSTRAINT fk_owner FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_whatsapp_instances_bot ON whatsapp_instances(bot_id);
CREATE INDEX idx_whatsapp_instances_owner ON whatsapp_instances(owner_user_id);
CREATE INDEX idx_whatsapp_instances_status ON whatsapp_instances(status);
CREATE INDEX idx_whatsapp_instances_active_primary ON whatsapp_instances(bot_id, is_active, is_primary)
    WHERE is_active = true AND is_primary = true;
```

**Total:** 1 table, no messages table, no stats table.

---

## Celery Task Implementation

### Celery Configuration

```python
# app/tasks/celery_config.py

from celery import Celery
from app.config import settings

celery_app = Celery(
    "bot_builder_whatsapp",
    broker=settings.redis.url,
    backend=settings.redis.url
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30,
    task_soft_time_limit=25,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)
```

### Process Message Task (Synchronous for Celery)

```python
# app/tasks/whatsapp_tasks.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.tasks.celery_config import celery_app
from app.utils.metrics import whatsapp_messages_counter, whatsapp_processing_histogram
import structlog

logger = structlog.get_logger()

# Sync session for Celery workers
sync_engine = create_engine(settings.database.url.replace('+asyncpg', ''))
SyncSession = sessionmaker(bind=sync_engine)


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True)
def process_whatsapp_message(self, instance_id: str, bot_id: str, message_data: dict):
    """
    Process WhatsApp message - NO DATABASE STORAGE

    1. Extract & normalize phone
    2. Process via ConversationOrchestrator (sync version)
    3. Send response via Evolution API
    4. Record Prometheus metrics
    5. Log structured events
    """

    start_time = datetime.utcnow()

    with SyncSession() as db:
        try:
            # Extract phone
            phone = extract_phone_from_jid(message_data["key"]["remoteJid"])
            formatted_phone = normalize_phone_number(phone)
            text = message_data["message"].get("conversation", "")

            # Log inbound
            logger.info(
                "whatsapp_message_received",
                instance_id=instance_id,
                phone=formatted_phone,
                message_length=len(text)
            )

            # Process (sync ConversationOrchestrator)
            from app.core.engine_sync import ConversationOrchestrator
            engine = ConversationOrchestrator(db)
            result = engine.process_message(
                channel="whatsapp",
                channel_user_id=formatted_phone,
                bot_id=UUID(bot_id),
                message=text
            )

            # Send response
            response_text = "\n\n".join(result.get("messages", []))
            if response_text:
                send_whatsapp_message.delay(
                    instance_id=instance_id,
                    instance_name=get_instance_name(db, instance_id),
                    phone_number=formatted_phone,
                    message_text=response_text
                )

            # Record metrics (Prometheus)
            duration = (datetime.utcnow() - start_time).total_seconds()
            whatsapp_processing_histogram.labels(instance_id=instance_id).observe(duration)
            whatsapp_messages_counter.labels(
                instance_id=instance_id,
                direction="inbound",
                status="success"
            ).inc()

            logger.info(
                "whatsapp_message_processed",
                instance_id=instance_id,
                phone=formatted_phone,
                processing_ms=duration * 1000
            )

        except Exception as exc:
            whatsapp_messages_counter.labels(
                instance_id=instance_id,
                direction="inbound",
                status="failed"
            ).inc()
            logger.error("whatsapp_processing_failed", error=str(exc), exc_info=True)
            raise
```

---

## Prometheus Metrics

```python
# app/utils/metrics.py

from prometheus_client import Counter, Histogram

whatsapp_messages_counter = Counter(
    'whatsapp_messages_total',
    'Total WhatsApp messages',
    ['instance_id', 'direction', 'status']
)

whatsapp_processing_histogram = Histogram(
    'whatsapp_processing_seconds',
    'Message processing time',
    ['instance_id'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)
```

**Metrics exposed at:** `GET /metrics`

**Grafana Queries:**
```promql
# Messages per second
rate(whatsapp_messages_total[5m])

# Success rate
rate(whatsapp_messages_total{status="success"}[5m])
/
rate(whatsapp_messages_total[5m])

# P95 processing time
histogram_quantile(0.95, whatsapp_processing_seconds_bucket)
```

---

## Docker Compose (Complete Production Setup)

```yaml
services:
  # Existing services (api, db, redis)...

  evolution-api:
    image: atendai/evolution-api:latest
    ports:
      - "8080:8080"
    environment:
      - SERVER_URL=${BASE_URL}
      - AUTHENTICATION_API_KEY=${WHATSAPP__EVOLUTION_API_KEY}
      - DATABASE_ENABLED=true
      - DATABASE_CONNECTION_URI=postgresql://botbuilder:${DB_PASSWORD}@db:5432/evolution
      - CACHE_REDIS_ENABLED=true
      - CACHE_REDIS_URI=redis://redis:6379/1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - botbuilder-network
    restart: unless-stopped

  celery-worker:
    build: .
    command: celery -A app.tasks.celery_config worker -l info --concurrency=4
    environment:
      - DATABASE__URL=postgresql://botbuilder:${DB_PASSWORD}@db:5432/botbuilder
      - REDIS__URL=redis://redis:6379/0
      - WHATSAPP__EVOLUTION_API_URL=http://evolution-api:8080
      - WHATSAPP__EVOLUTION_API_KEY=${WHATSAPP__EVOLUTION_API_KEY}
    depends_on:
      - db
      - redis
      - evolution-api
    deploy:
      replicas: 2  # Multiple workers for 10 req/sec
    networks:
      - botbuilder-network
    restart: unless-stopped

  flower:  # Celery monitoring UI
    build: .
    command: celery -A app.tasks.celery_config flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - REDIS__URL=redis://redis:6379/0
    depends_on:
      - redis
      - celery-worker
    networks:
      - botbuilder-network
    restart: unless-stopped

  prometheus:  # Metrics storage with persistence
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus  # ✅ PERSISTENT VOLUME
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'  # Keep 15 days
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - botbuilder-network
    restart: unless-stopped

  grafana:  # Dashboards and visualization
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana_data:/var/lib/grafana  # ✅ PERSISTENT DASHBOARDS
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_USERS_ALLOW_SIGN_UP=false
    depends_on:
      - prometheus
    networks:
      - botbuilder-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  prometheus_data:  # ✅ Metrics persist across restarts
  grafana_data:     # ✅ Dashboards persist across restarts

networks:
  botbuilder-network:
    driver: bridge
```

### Prometheus Configuration

Create `prometheus.yml`:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s      # Scrape every 15 seconds
  evaluation_interval: 15s  # Evaluate rules every 15 seconds
  external_labels:
    cluster: 'bot-builder-production'
    environment: 'production'

# Scrape configurations
scrape_configs:
  # Bot Builder API metrics
  - job_name: 'bot-builder-api'
    static_configs:
      - targets: ['api:8000']
        labels:
          service: 'api'

  # Celery worker metrics (if exposed)
  - job_name: 'celery-workers'
    static_configs:
      - targets: ['celery-worker:9999']  # If you expose metrics
        labels:
          service: 'celery'

  # Evolution API metrics (if available)
  - job_name: 'evolution-api'
    static_configs:
      - targets: ['evolution-api:8080']
        labels:
          service: 'evolution'

# Alerting rules (optional)
rule_files:
  - '/etc/prometheus/alerts.yml'
```

### Exposing Metrics Endpoint

```python
# app/main.py

from prometheus_client import make_asgi_app

# Create FastAPI app
app = FastAPI(...)

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Your existing routes...
```

Now metrics are available at: `http://localhost:8000/metrics`

### Grafana Datasource Configuration

Create `grafana/datasources/prometheus.yml`:

```yaml
# grafana/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### Grafana Dashboard Configuration

Create `grafana/dashboards/dashboard.yml`:

```yaml
# grafana/dashboards/dashboard.yml
apiVersion: 1

providers:
  - name: 'WhatsApp Metrics'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
      foldersFromFilesStructure: true
```

### Example Grafana Dashboard JSON

Create `grafana/dashboards/whatsapp.json`:

```json
{
  "dashboard": {
    "title": "WhatsApp Metrics",
    "panels": [
      {
        "title": "Messages per Second",
        "targets": [
          {
            "expr": "rate(whatsapp_messages_total[5m])",
            "legendFormat": "{{instance_id}} - {{direction}}"
          }
        ]
      },
      {
        "title": "Success Rate",
        "targets": [
          {
            "expr": "rate(whatsapp_messages_total{status=\"success\"}[5m]) / rate(whatsapp_messages_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "Processing Time (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(whatsapp_processing_seconds_bucket[5m]))",
            "legendFormat": "P95"
          }
        ]
      },
      {
        "title": "Total Messages (24h)",
        "targets": [
          {
            "expr": "increase(whatsapp_messages_total[24h])",
            "legendFormat": "{{direction}}"
          }
        ]
      }
    ]
  }
}
```

### Useful Prometheus Queries

```promql
# Current message rate (messages/sec)
rate(whatsapp_messages_total[5m])

# Success rate percentage
100 * (
  rate(whatsapp_messages_total{status="success"}[5m])
  /
  rate(whatsapp_messages_total[5m])
)

# Failed messages in last hour
increase(whatsapp_messages_total{status="failed"}[1h])

# P50, P95, P99 processing times
histogram_quantile(0.50, rate(whatsapp_processing_seconds_bucket[5m]))
histogram_quantile(0.95, rate(whatsapp_processing_seconds_bucket[5m]))
histogram_quantile(0.99, rate(whatsapp_processing_seconds_bucket[5m]))

# Total messages processed today
increase(whatsapp_messages_total[24h])

# Messages per instance
sum by (instance_id) (rate(whatsapp_messages_total[5m]))

# Error rate by instance
rate(whatsapp_messages_total{status="failed"}[5m]) by (instance_id)
```

### Alerting Rules (Optional)

Create `prometheus/alerts.yml`:

```yaml
# prometheus/alerts.yml
groups:
  - name: whatsapp_alerts
    interval: 30s
    rules:
      # Alert if message processing takes >5 seconds (P95)
      - alert: HighProcessingLatency
        expr: histogram_quantile(0.95, rate(whatsapp_processing_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High WhatsApp message processing latency"
          description: "P95 latency is {{ $value }}s (threshold: 5s)"

      # Alert if error rate >5%
      - alert: HighErrorRate
        expr: |
          100 * (
            rate(whatsapp_messages_total{status="failed"}[5m])
            /
            rate(whatsapp_messages_total[5m])
          ) > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High WhatsApp message error rate"
          description: "Error rate is {{ $value }}% (threshold: 5%)"

      # Alert if no messages processed in 10 minutes
      - alert: NoMessagesProcessed
        expr: rate(whatsapp_messages_total[10m]) == 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "No WhatsApp messages processed"
          description: "No messages in last 10 minutes for instance {{ $labels.instance_id }}"
```

---

## Data Persistence Explained

### What Persists Across Restarts

| Component | Data | Storage | Survives Restart? |
|-----------|------|---------|-------------------|
| **Your App** | Counter values | Memory | ❌ No (resets to 0) |
| **Prometheus** | Historical metrics | Volume | ✅ Yes (15 days) |
| **Grafana** | Dashboards | Volume | ✅ Yes |
| **PostgreSQL** | Instance configs | Volume | ✅ Yes |

### How Prometheus Handles Counter Resets

```
Timeline:
10:00:00 - App counter: 1,000,000 messages
10:00:30 - App crashes
10:01:00 - App restarts (counter resets to 0)
10:01:15 - Prometheus scrapes: sees 0

Prometheus Query: rate(whatsapp_messages_total[5m])
Result: Prometheus detects the reset and adjusts calculation
        No manual intervention needed! ✅
```

**Key Point:** Use `rate()` or `increase()` functions - they handle resets automatically.

### Backup Strategy

```bash
# Backup Prometheus data
docker run --rm -v bot-builder_prometheus_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/prometheus-backup-$(date +%Y%m%d).tar.gz /data

# Restore Prometheus data
docker run --rm -v bot-builder_prometheus_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/prometheus-backup-20241217.tar.gz -C /

# Backup Grafana dashboards
docker run --rm -v bot-builder_grafana_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/grafana-backup-$(date +%Y%m%d).tar.gz /data
```

---

## Dependencies

Add to `requirements.txt`:
```
celery[redis]==5.3.4
flower==2.0.1
phonenumbers==8.13.26
prometheus-client==0.19.0
structlog==23.2.0
```

---

## Configuration

```python
# app/config.py

class WhatsAppConfig(BaseSettings):
    enabled: bool = False
    evolution_api_url: str = "http://evolution-api:8080"
    evolution_api_key: str = Field(..., min_length=32)
    webhook_secret: str = Field(..., min_length=32)

    model_config = SettingsConfigDict(env_prefix="WHATSAPP__")

class Settings(BaseSettings):
    # ... existing ...
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
```

**Environment variables:**
```bash
WHATSAPP__ENABLED=true
WHATSAPP__EVOLUTION_API_URL=http://evolution-api:8080
WHATSAPP__EVOLUTION_API_KEY=your-32-char-key
WHATSAPP__WEBHOOK_SECRET=your-32-char-secret
```

---

## What Gets Stored Where

| Data | Storage | Retention | Why |
|------|---------|-----------|-----|
| Instance config | PostgreSQL | Permanent | Needed for API operations |
| Message content | **Nowhere** | N/A | Not needed, reduces costs |
| Message counts | Prometheus | 15 days | Real-time metrics |
| Errors/events | Structured logs | 30 days | Debugging |
| Connection state | Evolution API | Permanent | Already tracked there |

---

## Benefits of This Approach

### 1. Cost Savings
- **Before:** 5GB/day database growth = 150GB/month
- **After:** Zero message storage = minimal growth

### 2. Performance
- No DB writes on every message
- Faster Celery tasks
- Better query performance

### 3. Scalability
- Horizontal scaling via Celery workers
- No message table cleanup needed
- Standard Prometheus aggregation

### 4. Observability
- Grafana dashboards for real-time metrics
- ELK/Datadog for debugging
- Flower for Celery monitoring

---

## Migration from Current Document

### Sections to Update:

1. ✅ **Architecture section**: Keep Celery, remove "AsyncIO over Celery"
2. ✅ **Database schema**: Remove `whatsapp_messages` table entirely
3. ✅ **Background tasks**: Replace with Celery implementation above
4. ✅ **Docker compose**: Add Celery workers + Flower
5. ✅ **Configuration**: Add Celery broker settings
6. ✅ **Add new section**: "Prometheus Metrics & Monitoring"
7. ✅ **Add new section**: "Structured Logging Best Practices"
8. ✅ **Implementation checklist**: Remove message table tasks, add Celery setup

### Files to Create:

- `app/tasks/celery_config.py` - Celery app configuration
- `app/tasks/whatsapp_tasks.py` - Celery tasks
- `app/core/engine_sync.py` - Synchronous ConversationOrchestrator for Celery
- `app/utils/metrics.py` - Prometheus metrics
- `app/services/evolution_api_sync.py` - Sync Evolution API client for Celery

### Files to Modify:

- `app/config.py` - Add WhatsAppConfig
- `app/main.py` - Add /metrics endpoint
- `docker-compose.yml` - Add Celery worker + Flower
- `requirements.txt` - Add Celery, Prometheus, structlog

---

## Timeline

**Total: 2-3 weeks**

- Week 1: Database, models, Evolution API, basic endpoints
- Week 2: Celery tasks, metrics, monitoring setup
- Week 3: Testing, deployment, documentation

---

## Production Readiness Checklist

- [ ] Celery workers deployed (2+ instances)
- [ ] Flower monitoring accessible
- [ ] Prometheus metrics exposed
- [ ] Grafana dashboards created
- [ ] Structured logging configured
- [ ] Evolution API health checks
- [ ] Phone normalization tested
- [ ] Error alerting setup (PagerDuty/Slack)
- [ ] Load testing (simulate 10 req/sec)
- [ ] Disaster recovery plan

---

## Quick Start Guide

### 1. Directory Structure

```bash
backend/v1/
├── prometheus.yml                    # NEW
├── prometheus/
│   └── alerts.yml                    # NEW
├── grafana/
│   ├── datasources/
│   │   └── prometheus.yml            # NEW
│   └── dashboards/
│       ├── dashboard.yml             # NEW
│       └── whatsapp.json             # NEW
├── app/
│   ├── tasks/
│   │   ├── celery_config.py          # NEW
│   │   └── whatsapp_tasks.py         # NEW
│   ├── utils/
│   │   ├── metrics.py                # NEW
│   │   └── phone_utils.py            # NEW
│   └── ...
├── docker-compose.yml                # UPDATED
└── requirements.txt                  # UPDATED
```

### 2. Setup Steps

```bash
# 1. Create Prometheus config
cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'bot-builder-api'
    static_configs:
      - targets: ['api:8000']
EOF

# 2. Create Grafana directories
mkdir -p grafana/datasources grafana/dashboards

# 3. Create Grafana datasource
cat > grafana/datasources/prometheus.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

# 4. Update requirements.txt
cat >> requirements.txt << 'EOF'
celery[redis]==5.3.4
flower==2.0.1
phonenumbers==8.13.26
prometheus-client==0.19.0
structlog==23.2.0
EOF

# 5. Start services
docker-compose up -d

# 6. Verify
curl http://localhost:8000/metrics  # Should show Prometheus metrics
curl http://localhost:9090           # Prometheus UI
open http://localhost:3001           # Grafana (admin/admin)
open http://localhost:5555           # Flower (Celery monitoring)
```

### 3. Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Bot Builder API | http://localhost:8000 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3001 | admin / admin |
| Flower (Celery) | http://localhost:5555 | - |
| Evolution API | http://localhost:8080 | API key |

### 4. Verify Metrics

```bash
# Check if metrics are being collected
curl http://localhost:8000/metrics | grep whatsapp

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=rate(whatsapp_messages_total[5m])'

# Check Celery workers
docker-compose logs celery-worker

# Check Prometheus targets
open http://localhost:9090/targets
```

---

## Monitoring Dashboard Access

1. **Open Grafana:** http://localhost:3001
2. **Login:** admin / admin (change on first login)
3. **Add Prometheus datasource** (if not auto-configured):
   - Go to Configuration → Data Sources
   - Add Prometheus
   - URL: `http://prometheus:9090`
   - Save & Test

4. **Import WhatsApp dashboard:**
   - Go to Dashboards → Import
   - Upload `grafana/dashboards/whatsapp.json`
   - Select Prometheus datasource

5. **View metrics:**
   - Messages per second graph
   - Success rate
   - Processing latency
   - Error counts

---

## Questions Answered

**Q: Why Celery instead of FastAPI BackgroundTasks?**
A: 10 req/sec requires task persistence, retries, and horizontal scaling. BackgroundTasks loses messages on restart and can't scale horizontally.

**Q: Why no message storage?**
A: At 10 req/sec, you'd store 5GB/day. Prometheus + logs provide better observability without the storage cost or retention complexity.

**Q: Do Prometheus stats persist across restarts?**
A: Yes! Prometheus stores data in a persistent volume with 15-day retention. Your app's counters reset, but Prometheus keeps historical data and `rate()` queries handle resets automatically.

**Q: What about message history for users?**
A: Query Evolution API for basic stats. For detailed analytics, use Prometheus historical data (15 days) or log aggregation (ELK/Datadog, 30+ days).

**Q: How to debug failed messages?**
A: Structured logs with 30-day retention in ELK/Datadog. Celery task retries handle transient failures automatically. Check Flower UI for task status.

**Q: How much disk space does Prometheus need?**
A: Approximately 1-2GB for 15 days at 10 req/sec. Much less than storing messages in PostgreSQL (5GB/day).

---

## Production Checklist ✅

Before going live:

### Infrastructure
- [ ] Prometheus volume mounted (`prometheus_data`)
- [ ] Grafana volume mounted (`grafana_data`)
- [ ] Celery workers running (2+ replicas)
- [ ] Redis accessible and persistent
- [ ] Evolution API healthy

### Monitoring
- [ ] Grafana dashboards created
- [ ] Prometheus scraping targets (check `/targets`)
- [ ] Alerts configured (optional but recommended)
- [ ] Flower UI accessible for Celery monitoring
- [ ] `/metrics` endpoint exposed

### Security
- [ ] Grafana admin password changed
- [ ] Prometheus not exposed publicly
- [ ] Evolution API key secured
- [ ] Webhook secret configured

### Testing
- [ ] Send test WhatsApp message
- [ ] Verify metrics appear in Prometheus
- [ ] Check Celery task in Flower
- [ ] Confirm message processed in logs
- [ ] Test failover (restart worker, check recovery)

### Backup
- [ ] Prometheus volume backup scheduled
- [ ] Grafana dashboard exported
- [ ] Database backups configured

