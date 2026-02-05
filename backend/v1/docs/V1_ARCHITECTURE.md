# V1 Architecture: Account-Isolated Multi-Tenant Infrastructure

**Status:** Future Implementation (Currently on V0 - Shared Evolution API)
**Date:** January 2025
**Purpose:** Horizontal scalability through account-level infrastructure isolation

---

## Problem Statement

V0 uses a single shared Evolution API container for all accounts. This creates:
- Vertical scaling bottleneck (eventually hits resource ceiling)
- No fault isolation (one account affects others)
- Inability to provide tiered infrastructure guarantees
- Forced rearchitecture when scaling limits reached

**V1 Solution:** Make each account an independent infrastructure unit for horizontal scalability from day one.

---

## Core Architecture Change

### **V0 (Current): Shared Container**
```
All Accounts → Single Evolution API Container
  ├── Account A: Instances (bot_1, bot_2, bot_3)
  ├── Account B: Instances (bot_1, bot_2)
  └── Account C: Instances (bot_1)
```

### **V1 (Future): Container Per Account**
```
Account A → Dedicated Evolution API Container
  └── Instances (bot_1, bot_2, bot_3)

Account B → Dedicated Evolution API Container
  └── Instances (bot_1, bot_2)

Account C → Shared Evolution API Container (Starter tier)
  └── Instances (bot_1)
```

**Key Principle:** Each account's WhatsApp instances live in their own (or shared) Evolution API container. Bot Builder routes messages to the correct container based on account mapping.

---

## Infrastructure Model

### **Tier-Based Container Assignment**

| Tier | Evolution API | Bots | Messages/Month | Price |
|------|--------------|------|----------------|-------|
| **Free** | None (no WhatsApp) | 1 | 0 | $0 |
| **Starter** | Shared container | 3 | 2,000 | $19-29 |
| **Pro** | Dedicated container | Unlimited | 15,000 | $59-79 |

### **Resource Allocation**

**Per Evolution API Container:**
- RAM: 250-400MB
- CPU: 0.1-0.3 cores
- Disk: ~100MB

**Server Capacity:**
- 8GB RAM, 4 CPU → ~25 accounts
- 32GB RAM, 8 CPU → ~75 accounts
- 64GB RAM, 16 CPU → ~150 accounts

**Beyond 150 accounts:** Add additional servers, distribute accounts across hosts.

---

## Database Schema Changes

### **New: Account Entity**
```sql
CREATE TABLE accounts (
    account_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tier VARCHAR(50) NOT NULL DEFAULT 'free',  -- free, starter, pro
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, cancelled

    -- Evolution API Configuration
    evolution_api_url VARCHAR(255),  -- http://evolution-account-abc:8081
    evolution_api_key VARCHAR(255),  -- Unique per account
    evolution_container_name VARCHAR(255),  -- Container ID/name

    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### **Update: User Entity**
```sql
ALTER TABLE users ADD COLUMN account_id UUID REFERENCES accounts(account_id);
```

### **Update: Bot Entity**
```sql
ALTER TABLE bots ADD COLUMN account_id UUID REFERENCES accounts(account_id);
ALTER TABLE bots ADD COLUMN status VARCHAR(50) DEFAULT 'active';  -- active, inactive
ALTER TABLE bots ADD COLUMN inactive_reason VARCHAR(255);
```

### **Session Key Format Change**
- **V0:** `channel:user_id:bot_id`
- **V1:** `channel:user_id:account_id:bot_id` (prevents collision across accounts)

---

## Core Services

### **1. Evolution Provisioner Service**

**Responsibility:** Create/destroy Evolution API containers for accounts.

**Key Methods:**
```python
async def provision_for_account(account: Account) -> dict:
    """
    Creates dedicated Evolution API container via Docker API.
    Returns: {evolution_api_url, evolution_api_key, container_name}
    """

async def deprovision_for_account(account: Account) -> None:
    """Destroys Evolution API container and cleans up resources."""
```

**Provisioning Flow:**
1. User signs up for Starter/Pro tier
2. Background task provisions container (30-60 seconds)
3. Update account record with container details
4. Health check and verify ready
5. User can now connect WhatsApp

### **2. Account-Aware Evolution Service**

**Change:** Evolution API service now requires account-specific URL and API key.

```python
# V0 (global config)
evolution_service = EvolutionAPIService(settings.evolution_api.url, settings.evolution_api.api_key)

# V1 (account-specific)
async def get_evolution_service_for_account(account_id: UUID) -> EvolutionAPIService:
    account = await get_account(account_id)
    return EvolutionAPIService(account.evolution_api_url, account.evolution_api_key)
```

### **3. Tier Enforcement Service**

**Responsibility:** Disable bots when limits exceeded.

**Rules:**
- Free tier: No WhatsApp (no Evolution API)
- Starter tier: 3 bots max → Disable excess
- Pro tier: Unlimited
- Cancellation: Disable all bots

**Bot Status:**
- `active` → Processing messages
- `inactive` → Not processing (exceeds limit, cancelled, user disabled)

---

## Message Routing (V1)

### **Incoming Message Flow**
```
1. WhatsApp user sends message
2. Evolution API (Account A's container) receives webhook
3. Posts to: /webhooks/whatsapp/{bot_id}
4. Bot Builder:
   - Looks up bot → account
   - Checks bot.status == 'active' && account.status == 'active'
   - Processes through conversation engine
5. Bot Builder gets account.evolution_api_url
6. Sends response to Account A's Evolution API container
7. Evolution API delivers via WhatsApp
```

**Key Change:** Bot Builder routes responses to account-specific Evolution API URL instead of global URL.

---

## Tier Transitions

### **Free → Starter**
- Instant (assign shared Evolution API URL)
- User can now connect WhatsApp

### **Starter → Pro**
- Provision dedicated container (30-60s)
- Update account with new Evolution API URL
- **User must reconnect WhatsApp** (QR rescan - acceptable)

### **Pro → Starter (Downgrade)**
- Check bot count ≤3 → Disable excess if needed
- Assign shared Evolution API URL
- Delete dedicated container
- User reconnects WhatsApp

### **Cancellation**
- Set all bots to `inactive`
- Set account.status = 'cancelled'
- Preserve data for 30 days (grace period)
- Delete container after grace period
- Full data deletion after 90 days

---

## Scaling Strategy

### **Phase 1: Single Host** (0-150 accounts)
- All containers on one server (64GB RAM, 16 CPU)
- Docker API for provisioning
- Simple operations

### **Phase 2: Manual Multi-Host** (150-500 accounts)
- 3-5 servers
- Manually assign new accounts to hosts
- Track in database: `account.host_location`

### **Phase 3: Kubernetes** (500+ accounts)
- Automated distribution
- Auto-scaling and self-healing
- Multi-region support

**Start at Phase 1. Migrate when needed.**

---

## Economics

### **Infrastructure Costs**

**100 Paying Customers:**
- 60 Starter (shared) → ~$10/month
- 40 Pro (dedicated) → ~$100/month
- Base (DB, Redis, API) → ~$50/month
- **Total:** ~$160/month
- **Revenue:** ~$2,500/month
- **Margin:** ~93%

**500 Paying Customers:**
- Infrastructure: ~$1,500/month
- Revenue: ~$20,000/month
- **Margin:** ~92%

**Key Point:** Infrastructure costs scale sub-linearly (5-10% of revenue at scale).

---

## Implementation Checklist

### **Database Migration**
- [ ] Create `accounts` table
- [ ] Add `account_id` to `users` and `bots` tables
- [ ] Add `status` to `bots` table
- [ ] Migrate existing users → create accounts
- [ ] Update session key format

### **Backend Services**
- [ ] Build `EvolutionProvisionerService` (Docker API integration)
- [ ] Update `EvolutionAPIService` to accept account-specific URL
- [ ] Build account-aware factory: `get_evolution_service_for_account()`
- [ ] Build tier enforcement logic (disable excess bots)

### **API Endpoints**
- [ ] `POST /accounts/signup` (provision container for paid tiers)
- [ ] `POST /accounts/{account_id}/upgrade` (tier transitions)
- [ ] `POST /accounts/{account_id}/cancel` (disable bots)
- [ ] Update WhatsApp endpoints to use account Evolution API URL

### **Webhook Handlers**
- [ ] Check `bot.status == 'active'` before processing
- [ ] Check `account.status == 'active'` before processing
- [ ] Route responses to account-specific Evolution API container

### **Infrastructure Setup**
- [ ] Docker API access from Bot Builder container
- [ ] Shared Docker network for all containers
- [ ] Port assignment strategy (9000-9999 range)
- [ ] Container health checks

### **Billing Integration**
- [ ] Stripe/Paddle subscription webhooks
- [ ] Usage tracking (messages per account)
- [ ] Tier limit enforcement
- [ ] Automatic bot disabling on downgrade/cancellation

---

## Key Design Decisions

1. **Account = Infrastructure Unit:** Pro accounts get dedicated containers, Starter shares.
2. **Horizontal Scaling:** Growth = add hosts, not upgrade hosts.
3. **Data Preservation:** Never force delete. Disable bots, preserve data, allow reactivation.
4. **Simple Bot States:** `active` or `inactive`. Nothing more complex.
5. **QR Rescan Acceptable:** Industry standard for infrastructure changes (Starter ↔ Pro).
6. **Graceful Degradation:** 30-day grace period on cancellation, 90-day full deletion.

---

## Migration from V0 to V1

### **Backward Compatibility Approach**

1. Add account model and relationships (no breaking changes)
2. Migrate existing users → create accounts with shared Evolution API
3. New paid signups → provision dedicated containers (V1)
4. Existing users stay on V0 (shared container)
5. Gradual migration: Offer V1 upgrade to existing users
6. Eventually deprecate shared container when all migrated

**Key Point:** V0 and V1 can coexist during transition.

---

## Success Metrics

- **Infrastructure cost per account:** <10% of subscription price
- **Container provisioning time:** <60 seconds
- **Account isolation:** Zero cross-account interference
- **Upgrade/downgrade success rate:** >95%
- **Reactivation rate:** >20% within 30 days of cancellation

---

## Future Considerations (Beyond V1)

- **Auto-scaling:** Automatically provision new hosts when capacity threshold reached
- **Geographic distribution:** Place containers near users (latency optimization)
- **Multi-region:** Disaster recovery and compliance (data residency)
- **Resource optimization:** Dynamic resource allocation based on usage patterns
- **Container pooling:** Pre-warm containers for faster provisioning

---

## Reference Documents

- **V0 Specifications:** `BOT_BUILDER_SPECIFICATIONS.md`
- **Evolution API Integration:** `EVOLUTION_API_V2_DOCS.md`
- **Database Schema:** (Alembic migrations in `alembic/versions/`)
- **Architecture Discussion:** (This document originated from strategic planning session, January 2025)
