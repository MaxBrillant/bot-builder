# Security

Comprehensive security implementation for Bot Builder v1. All security measures are enforced at multiple layers with fail-safe defaults.

## Overview

Bot Builder implements defense-in-depth security across 8 domains:

| Domain | Components | Fail Mode |
|--------|-----------|-----------|
| Input Sanitization | 3-layer system (sanitization, escaping, pattern rejection) | Reject on pattern detection |
| SSRF Protection | URL validation, DNS resolution, private IP blocking | Fail closed (block suspicious URLs) |
| Authentication | JWT with JTI, bcrypt password hashing | Token expiration enforced |
| Token Blacklist | Redis-backed JWT revocation | Fail closed (reject if Redis down) |
| Rate Limiting | Channel-user and user-level limits | Fail closed (reject if Redis down) |
| Webhook Security | Secret validation on every request | Reject invalid secrets |
| Audit Logging | Comprehensive security event trail | Database-persisted |
| SSRF Prevention | Private network blocking, hostname validation | Fail closed |

**Critical Constraint**: Redis is mandatory. Rate limiting and token blacklist fail closed when Redis is unavailable (raise `SecurityServiceUnavailableError`).

## Input Sanitization

3-layer sanitization system applied to all user input.

### Layer 1: Baseline Sanitization (Universal)

Applied to all input before storage or processing.

| Operation | Action | Limit |
|-----------|--------|-------|
| Null bytes | Remove `\x00` characters | Track count in metadata |
| Control characters | Remove all except `\n`, `\t`, `\r` | Track count in metadata |
| Whitespace | Trim leading/trailing | - |
| Length limit | Truncate to 4096 characters | Set `was_truncated` flag |

**Implementation**: `app/utils/security/sanitization.py::sanitize_input()`

**Returns**: `(sanitized_text, metadata)` tuple

**Metadata fields**:
- `original_length`: Original text length
- `sanitized_length`: Final text length
- `null_bytes_removed`: Count of null bytes removed
- `control_chars_removed`: Count of control characters removed
- `was_truncated`: Boolean flag

### Layer 2: Context-Aware Escaping

Applied at point of use based on output context.

| Context | Function | Escapes |
|---------|----------|---------|
| HTML rendering | `escape_html()` | `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`, `"` → `&quot;`, `'` → `&#x27;` |

**Implementation**: `app/utils/security/sanitization.py::escape_html()`

### Layer 3: Pattern Rejection (Universal)

Detects and blocks dangerous patterns indicating attack attempts.

| Pattern | Type | Regex |
|---------|------|-------|
| Script tags | XSS | `<script[^>]*>`, `</script>` |
| JavaScript protocol | XSS | `javascript:` |
| Event handlers | XSS | `on\w+\s*=` (onclick, onerror, etc.) |
| Template injection | Code injection | `{{`, `}}`, `\${[^}]*}` |
| Command injection | OS command | `;`, `\|\|`, `&&`, `\|` |
| Path traversal | Directory traversal | `../`, `..\` |
| SQL comments | SQL injection | `--`, `/*`, `*/` |

**Implementation**: `app/utils/security/sanitization.py::check_suspicious_patterns()`

**Returns**: `(is_safe, pattern_type)` tuple

**Action on detection**: Reject input, raise `SanitizationError`, log security event

### Webhook Input Flow

1. Receive message at `/webhook/{bot_id}`
2. Apply Layer 1 sanitization (`sanitize_input()`)
3. Check Layer 3 patterns (`check_suspicious_patterns()`)
4. If pattern detected: log audit event, return error in SSE stream
5. If safe: replace original input with sanitized version, continue processing

**Implementation**: `app/api/webhooks/sanitization.py::sanitize_and_audit_webhook_input()`

## SSRF Protection

Prevents Server-Side Request Forgery attacks when bot flows make HTTP requests to user-controlled URLs.

### Blocked IP Ranges

| Range | Purpose | Notes |
|-------|---------|-------|
| `10.0.0.0/8` | Private Class A | RFC 1918 |
| `172.16.0.0/12` | Private Class B | RFC 1918 |
| `192.168.0.0/16` | Private Class C | RFC 1918 |
| `169.254.0.0/16` | Link-local | AWS/GCP metadata endpoints |
| `127.0.0.0/8` | Loopback | Localhost |
| `0.0.0.0/8` | Current network | Invalid source |
| `100.64.0.0/10` | Carrier-grade NAT | RFC 6598 |
| `192.0.0.0/24` | IETF Protocol Assignments | Reserved |
| `192.0.2.0/24` | TEST-NET-1 | Documentation |
| `198.51.100.0/24` | TEST-NET-2 | Documentation |
| `203.0.113.0/24` | TEST-NET-3 | Documentation |
| `224.0.0.0/4` | Multicast | Class D |
| `240.0.0.0/4` | Reserved | Future use |
| `255.255.255.255/32` | Broadcast | - |
| `::1/128` | IPv6 loopback | - |
| `fc00::/7` | IPv6 unique local | RFC 4193 |
| `fe80::/10` | IPv6 link-local | - |
| `::ffff:0:0/96` | IPv4-mapped IPv6 | Prevents bypass via `::ffff:127.0.0.1` |

### Validation Rules

1. **Scheme validation**: Only `http` and `https` allowed
2. **Hostname validation**: Block `localhost`, `metadata`, `metadata.google.internal`
3. **DNS resolution**: Resolve hostname to all IPs (IPv4 and IPv6)
4. **IP range check**: Block if any resolved IP matches blocked networks
5. **Global IP check**: Reject non-global IPs (`.is_global` check)

**Implementation**: `app/utils/security/ssrf.py::is_safe_url_for_ssrf()`

**Returns**: `(is_safe, error_message)` tuple

**Usage**: Call before making HTTP requests in `API_ACTION` nodes

### Bypass Prevention

- DNS rebinding: Re-resolve on each request (don't cache resolution)
- IPv6 bypass: Check IPv6 equivalents of private ranges
- IPv4-mapped IPv6: Block `::ffff:127.0.0.1` format
- Integer IP: `urlparse()` handles this automatically
- TOCTOU: Validate immediately before request

## Authentication

JWT-based authentication with token revocation support.

### Password Hashing

| Algorithm | Rounds | Max Length | Encoding |
|-----------|--------|------------|----------|
| bcrypt | 12 (configurable) | 72 characters / 72 bytes | UTF-8 |

**Validation**:
- Character count ≤ 72
- Byte count ≤ 72 (multi-byte characters may exceed character limit)
- Reject with clear error if exceeded

**Implementation**:
- `app/utils/security/password.py::get_password_hash()` - Hash on registration
- `app/utils/security/password.py::verify_password()` - Verify on login

**Note**: bcrypt silently truncates at 72 bytes. We validate and reject to prevent user confusion.

### JWT Token Structure

| Claim | Description | Required |
|-------|-------------|----------|
| `sub` | User ID (UUID as string) | Yes |
| `exp` | Expiration timestamp | Yes |
| `jti` | JWT ID (UUID) for blacklisting | Yes (access tokens) |
| `type` | Token type (`"refresh"` for refresh tokens) | Refresh tokens only |

**Access Token**:
- Default expiration: Configurable via `settings.security.access_token_expire_minutes`
- Includes `jti` claim for revocation support

**Refresh Token**:
- Default expiration: 7 days
- Includes `type: "refresh"` claim
- Used to issue new access tokens

**Implementation**:
- `app/utils/security/__init__.py::create_access_token()`
- `app/utils/security/__init__.py::create_refresh_token()`
- `app/utils/security/__init__.py::decode_access_token()`
- `app/utils/security/__init__.py::extract_user_id_from_token()`

### Token Security

1. Algorithm: Configurable via `settings.security.algorithm` (default: HS256)
2. Secret key: `settings.security.secret_key` (must be strong, random)
3. Token validation: Verify signature, expiration, and blacklist status
4. Token revocation: Blacklist by `jti` claim (see Token Blacklist section)

## Token Blacklist

JWT revocation via Redis-backed blacklist.

### Implementation

| Operation | Redis Key | TTL | Fail Mode |
|-----------|-----------|-----|-----------|
| Blacklist token | `blacklist:token:{jti}` | Time until token expires | Fail closed (raise error) |
| Check blacklist | `blacklist:token:{jti}` | - | Fail closed (raise error) |

**Functions**:
- `redis_manager.blacklist_token(jti, ttl)` - Add token to blacklist (called during logout in `app/api/auth.py:293`)
- `redis_manager.is_token_blacklisted(jti)` - Check if token is blacklisted

**Blacklist Check Location**: Token blacklist is checked in the authentication dependency (`app/dependencies.py:61-73`). On every authenticated request, after JWT decoding, the `jti` claim is checked against the Redis blacklist. If blacklisted, raises `AuthenticationError("Token has been revoked")`.

**Security Policy**: If Redis is unavailable, raise `SecurityServiceUnavailableError`. Never allow authentication bypass.

**TTL Strategy**: Set TTL to remaining time until token naturally expires. No need to store blacklist entries indefinitely.

**Use Cases**:
- User logout
- Password change (blacklist all user tokens)
- Security incident response (revoke compromised tokens)

**Implementation**: `app/core/redis_manager.py` (lines 609-659)

## Rate Limiting

Two-tier rate limiting: channel-user level (webhook) and user level (API).

### Channel-User Rate Limiting

Applied to webhook endpoints (incoming messages).

| Parameter | Default | Scope | Redis Key |
|-----------|---------|-------|-----------|
| Max requests | 10 | Per user per channel | `ratelimit:channel:{channel}:{channel_user_id}` |
| Window | 60 seconds | Sliding | TTL on key |

**Purpose**: Prevent abuse from external users sending messages to bots.

**Scope**: Platform-agnostic (works across WhatsApp, SMS, Telegram, etc.)

**Implementation**: `redis_manager.check_rate_limit_channel_user()` (lines 343-391)

**Usage**: Called in `/webhook/{bot_id}` before processing message (line 122-143)

**On limit exceeded**:
1. Log warning with masked user ID
2. Log security audit event (type: `security`, action: `rate_limit_exceeded`, result: `blocked`)
3. Return 429 Too Many Requests

### User Rate Limiting

Applied to authenticated API endpoints.

| Parameter | Default | Scope | Redis Key |
|-----------|---------|-------|-----------|
| Max requests | 100 | Per authenticated user | `ratelimit:user:{user_id}` |
| Window | 60 seconds | Sliding | TTL on key |

**Purpose**: Prevent abuse from authenticated users making excessive API calls.

**Implementation**: `redis_manager.check_rate_limit_user()` (lines 393-436)

**Usage**: Apply to API endpoints via middleware or dependency injection

**On limit exceeded**:
1. Log warning with user ID
2. Return 429 Too Many Requests

### Rate Limit Failure Policy

**Critical**: Both rate limit functions raise `SecurityServiceUnavailableError` if Redis is unavailable. Never allow bypass when rate limiting fails.

## Webhook Security

Webhook secret validation on every inbound message.

### Validation Flow

1. Extract `X-Webhook-Secret` header
2. Reject if header missing (401 Unauthorized)
3. Call `bot_service.verify_webhook_secret(bot_id, secret)`
4. Compare provided secret with bot's stored `webhook_secret` (constant-time comparison)
5. Reject if invalid (401 Unauthorized)
6. Log warning on failed validation

**Implementation**: `app/api/webhooks/core.py` (lines 86-98)

**Storage**: `webhook_secret` stored in `bots` table, generated on bot creation

**Rotation**: Regenerate webhook secret via bot update endpoint (invalidates old webhooks)

### Security Properties

- **Authentication**: Verifies request originates from authorized source
- **Constant-time comparison**: Uses `hmac.compare_digest()` to prevent timing attacks (`app/services/bot_service.py:254`)
- **Bot-not-found protection**: If bot doesn't exist, compares against a dummy secret to prevent timing-based bot enumeration (`bot_service.py:250-251`)

## Audit Logging

Comprehensive security audit trail for compliance and monitoring.

### Schema

| Field | Type | Indexed | Nullable | Description |
|-------|------|---------|----------|-------------|
| `id` | UUID | PK | No | Unique audit log entry identifier |
| `timestamp` | DateTime | Yes | No | When event occurred (UTC) |
| `event_type` | String(64) | Yes | No | Category of event |
| `user_id` | String(255) | Yes | Yes | Masked channel_user_id or authenticated user_id |
| `resource_type` | String(64) | No | Yes | Type of resource (bot, flow, session, etc.) |
| `resource_id` | String(255) | No | Yes | ID of the resource |
| `action` | String(128) | Yes | No | Specific action taken |
| `result` | String(32) | No | No | Outcome (success, error, blocked, rejected, failed) |
| `event_metadata` | JSONB | No | Yes | Additional context as JSON |

**Table**: `audit_logs`

**Implementation**: `app/models/audit_log.py`

### Event Types

| Type | Purpose | Examples |
|------|---------|----------|
| `user_action` | User interactions | Message received, input validation |
| `session_event` | Session lifecycle | Created, completed, expired, error |
| `api_call` | External API calls | HTTP requests (no sensitive data) |
| `validation_failure` | Input validation failures | Pattern rejection, format errors |
| `authentication` | Auth attempts | Login, logout, token refresh |
| `security` | Security events | Sanitization, pattern rejection, rate limiting |
| `flow_execution` | Flow state changes | Node transitions, flow completion |

**Constants**: `app/models/audit_log.py::AuditEventType`

### Result Types

| Result | Meaning |
|--------|---------|
| `success` | Operation completed successfully |
| `error` | Operation failed due to error |
| `blocked` | Operation blocked by security control |
| `rejected` | Operation rejected by validation |
| `failed` | Operation attempted but failed |

**Constants**: `app/models/audit_log.py::AuditResult`

### Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_audit_event_timestamp` | `(event_type, timestamp)` | Filter by event type and time range |
| `idx_audit_user_timestamp` | `(user_id, timestamp)` | User audit trail |
| `idx_audit_resource` | `(resource_type, resource_id)` | Resource-specific audit trail |
| Individual indexes | `timestamp`, `event_type`, `user_id`, `action` | Single-column queries |

### Security Considerations

**PII Masking**: User IDs are masked before storage using `logger.mask_pii()`. Raw PII never stored.

**Sensitive Data**: Never log passwords, API keys, credit cards, or raw PII in `event_metadata`.

**Retention**: Audit logs should be retained per compliance requirements. Consider separate retention policy from application data.

**Repository**: `app/repositories/audit_log_repository.py` provides helper methods for logging security events.

### Example Usage

```python
await audit_log.log_security_event(
    action="rate_limit_exceeded",
    user_id=masked_user,
    result=AuditResult.BLOCKED,
    event_metadata={
        "bot_id": str(bot_id),
        "channel": "whatsapp"
    }
)
```

## Additional Security Utilities

### Node ID Validation

Validates node IDs to prevent injection attacks in flow processing.

**Rules**:
- Alphanumeric and underscores only (`[A-Za-z0-9_]+`)
- No spaces
- Length ≤ 96 characters

**Implementation**: `app/utils/security/ssrf.py::validate_node_id_format()`

### Session ID Generation

Generates cryptographically secure session IDs.

**Format**: UUID v4 (122 bits of entropy)

**Implementation**: `app/utils/security/ssrf.py::generate_session_id()`

## Constraints

### Redis Dependency

Redis is **mandatory** for the following security features:

| Feature | Fail Mode | Exception |
|---------|-----------|-----------|
| Rate limiting | Fail closed | `SecurityServiceUnavailableError` |
| Token blacklist | Fail closed | `SecurityServiceUnavailableError` |
| Flow caching | Fail open | Return None (fetch from DB) |
| Session caching | Fail open | Return None (fetch from DB) |

**Critical**: App startup fails if Redis is unavailable. Never run without Redis.

### Input Length Limits

| Input Type | Limit | Enforcement |
|-----------|-------|-------------|
| User message | 4096 characters | Layer 1 sanitization (truncate) |
| Password | 72 characters / 72 bytes | Registration validation (reject) |
| Node ID | 96 characters | Format validation (reject) |

### Token Expiration

| Token Type | Default Expiration | Configurable |
|-----------|-------------------|--------------|
| Access token | Configurable minutes | Yes (`settings.security.access_token_expire_minutes`) |
| Refresh token | 7 days | Yes (modify `create_refresh_token()`) |
| Session | 30 minutes (absolute) | No (hardcoded in spec) |

### Rate Limit Windows

| Limit Type | Window | Configurable |
|-----------|--------|--------------|
| Channel-user | 60 seconds | Yes (`settings.rate_limit.webhook_window`) |
| User | 60 seconds | Yes (pass `window_seconds` parameter) |

**Note**: Windows are sliding (per-request tracking with TTL).

## Code Paths

| Security Feature | Primary Implementation |
|-----------------|----------------------|
| Input sanitization | `backend/v1/app/utils/security/sanitization.py` |
| SSRF protection | `backend/v1/app/utils/security/ssrf.py` |
| Password hashing | `backend/v1/app/utils/security/password.py` |
| JWT tokens | `backend/v1/app/utils/security/__init__.py` |
| Token blacklist | `backend/v1/app/core/redis_manager.py` (lines 609-659) |
| Rate limiting | `backend/v1/app/core/redis_manager.py` (lines 343-436) |
| Webhook validation | `backend/v1/app/api/webhooks/core.py` (lines 86-98) |
| Audit logging | `backend/v1/app/models/audit_log.py` |
| Webhook sanitization | `backend/v1/app/api/webhooks/sanitization.py` |

## Testing Security Features

### Input Sanitization Testing

```python
# Test Layer 1
text, metadata = sanitize_input("Hello\x00World\x01!")
assert text == "Hello World!"
assert metadata['null_bytes_removed'] == 1
assert metadata['control_chars_removed'] == 1

# Test Layer 3
is_safe, pattern = check_suspicious_patterns("<script>alert('xss')</script>")
assert not is_safe
assert pattern == "script_tag"
```

### SSRF Testing

```python
# Test private IP blocking
is_safe, error = is_safe_url_for_ssrf("http://192.168.1.1/admin")
assert not is_safe
assert "blocked IP range" in error

# Test metadata endpoint blocking
is_safe, error = is_safe_url_for_ssrf("http://169.254.169.254/latest/meta-data/")
assert not is_safe
```

### Rate Limit Testing

```python
# Test rate limit enforcement
for i in range(10):
    allowed = await redis_manager.check_rate_limit_channel_user(
        "whatsapp", "user123", max_requests=10, window_seconds=60
    )
    assert allowed

# 11th request should be blocked
allowed = await redis_manager.check_rate_limit_channel_user(
    "whatsapp", "user123", max_requests=10, window_seconds=60
)
assert not allowed
```

### Token Blacklist Testing

```python
# Test token revocation
jti = "unique-token-id"
await redis_manager.blacklist_token(jti, ttl=3600)
is_blacklisted = await redis_manager.is_token_blacklisted(jti)
assert is_blacklisted
```
