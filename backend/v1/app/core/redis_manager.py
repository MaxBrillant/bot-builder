"""Redis Manager for Bot Builder v1.

Handles Redis operations for:
- Flow caching with automatic invalidation
- Rate limiting (per channel+user, per user)
- Trigger keyword lookup
- Active session caching
- JWT token blacklist

Features circuit breaker pattern to prevent cascading failures.
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import redis.asyncio as redis
from app.config import settings
from app.utils.logger import get_logger
from app.utils.exceptions import SecurityServiceUnavailableError
from app.core.circuit_breaker import CircuitState, DistributedCircuitBreaker, CircuitBreaker

# Health check timeout in seconds
HEALTH_CHECK_TIMEOUT_SECONDS = 5

logger = get_logger(__name__)


class RedisManager:
    """
    Manages all Redis operations for the Bot Builder system.

    Features:
    - Automatic reconnection with exponential backoff
    - Distributed circuit breaker to prevent cascading failures (shared across instances)
    - Graceful degradation when Redis unavailable

    Failure Policy:
    - Security operations (rate limiting, token blacklist): FAIL-CLOSED
      When Redis is unavailable, these operations raise SecurityServiceUnavailableError
      to prevent bypassing security controls. Better to fail safe than allow abuse.

    - Caching operations (flow cache, session cache, trigger cache): FAIL-OPEN
      When Redis is unavailable, these operations return None/empty and log warnings.
      Allows system to continue operating (fetches from DB instead) with degraded performance.
    """

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connected = False
        self._reconnect_lock = asyncio.Lock()
        self._reconnect_attempts = 0

        # Distributed circuit breaker to prevent cascading failures
        # State is shared across all API instances via Redis
        self.circuit_breaker = DistributedCircuitBreaker(
            failure_threshold=5,      # Open after 5 failures
            timeout_seconds=60,       # Wait 60s before testing recovery
            success_threshold=2       # Need 2 successes to close circuit
        )

    async def connect(self):
        """
        Establish Redis connection.

        Raises:
            RuntimeError: If Redis connection fails (Redis is mandatory for security)
        """
        try:
            self.redis = redis.from_url(
                settings.redis.url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=settings.redis.socket_connect_timeout,
                socket_keepalive=True,
            )
            # Test connection
            await self.redis.ping()
            self._connected = True
            self._reconnect_attempts = 0

            # Set Redis client on circuit breaker for distributed state
            self.circuit_breaker.set_redis(self.redis)

            await self.circuit_breaker.record_success()  # Record successful connection
            logger.info("Redis connection established (circuit breaker state now distributed)")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            await self.circuit_breaker.record_failure()  # Record connection failure
            # SECURITY: Redis is mandatory for rate limiting and token blacklisting
            raise RuntimeError(
                f"Redis connection required but failed: {e}. "
                "Redis is mandatory for rate limiting and token blacklisting security features."
            )

    async def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect to Redis with exponential backoff.
        Uses async lock to prevent concurrent reconnection attempts.
        
        Returns:
            True if reconnection successful, False otherwise
        """
        async with self._reconnect_lock:
            # Check if another task already reconnected
            if self._connected:
                return True

            if self._reconnect_attempts >= settings.redis.max_reconnect_attempts:
                logger.error(f"Max reconnection attempts ({settings.redis.max_reconnect_attempts}) reached")
                return False

            # Clean up old connection before reconnecting to prevent leaks
            if self.redis:
                try:
                    await self.redis.close()
                    await self.redis.connection_pool.disconnect()
                except Exception as e:
                    logger.warning(f"Error cleaning up old connection: {e}")

            self._reconnect_attempts += 1
            backoff = min(2 ** self._reconnect_attempts, settings.redis.reconnect_backoff_cap)

            logger.info(f"Attempting Redis reconnection (attempt {self._reconnect_attempts}/{settings.redis.max_reconnect_attempts})")
            await asyncio.sleep(backoff)
            
            try:
                await self.connect()
                return self._connected
            except Exception as e:
                logger.error(f"Reconnection attempt {self._reconnect_attempts} failed: {e}")
                return False

    async def disconnect(self):
        """Close Redis connection with complete cleanup."""
        if self.redis:
            await self.redis.close()
            # Also disconnect the connection pool for complete cleanup
            await self.redis.connection_pool.disconnect()
            self._connected = False
            logger.info("Redis connection and pool closed")

    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._connected

    # ==================== Flow Caching ====================

    async def cache_flow(self, flow_id: str, flow_data: Dict[str, Any], ttl: int = 3600):
        """
        Cache a flow definition with validation.
        
        Args:
            flow_id: Unique flow identifier
            flow_data: Complete flow definition
            ttl: Time to live in seconds (default: 1 hour)
        """
        if not self.is_connected():
            return

        try:
            # Validate structure before caching
            # flow_data is a wrapper with: id, name, bot_id, flow_definition, trigger_keywords, etc.
            # The actual flow structure (start_node_id, nodes) is inside flow_definition
            flow_definition = flow_data.get('flow_definition', {})
            required_keys = {'name', 'start_node_id', 'nodes'}
            if not all(key in flow_definition for key in required_keys):
                logger.error(f"Invalid flow structure for caching: {flow_id}")
                return
            
            key = f"flow:{flow_id}"
            # Use explicit error handling instead of default=str
            try:
                serialized = json.dumps(flow_data)
            except (TypeError, ValueError) as e:
                logger.error(f"Failed to serialize flow {flow_id}: {e}")
                return
            
            await self.redis.setex(key, ttl, serialized)
            logger.debug(f"Cached flow: {flow_id}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection error, attempting reconnect: {e}")
            if await self._attempt_reconnect():
                # Retry operation after successful reconnection
                try:
                    serialized = json.dumps(flow_data)
                    await self.redis.setex(key, ttl, serialized)
                except Exception as retry_e:
                    logger.error(f"Retry failed for cache_flow {flow_id}: {retry_e}")
        except Exception as e:
            logger.error(f"Failed to cache flow {flow_id}: {e}")

    async def get_cached_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached flow definition.
        
        Args:
            flow_id: Unique flow identifier
            
        Returns:
            Flow definition or None if not cached
        """
        if not self.is_connected():
            return None

        try:
            key = f"flow:{flow_id}"
            data = await self.redis.get(key)
            if data:
                logger.debug(f"Cache hit for flow: {flow_id}")
                return json.loads(data)
            logger.debug(f"Cache miss for flow: {flow_id}")
            return None
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection error during get_cached_flow: {e}")
            self._connected = False
            return None
        except Exception as e:
            logger.error(f"Failed to get cached flow {flow_id}: {e}")
            return None

    async def invalidate_flow_cache(self, flow_id: str):
        """
        Invalidate cached flow definition.
        
        Args:
            flow_id: Unique flow identifier
        """
        if not self.is_connected():
            return

        try:
            key = f"flow:{flow_id}"
            await self.redis.delete(key)
            logger.debug(f"Invalidated flow cache: {flow_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate flow cache {flow_id}: {e}")

    # ==================== Trigger Keyword Lookup ====================

    async def cache_trigger_keyword(self, keyword: str, flow_id: str, bot_id: str):
        """
        Cache trigger keyword to flow mapping (bot-scoped).
        
        Args:
            keyword: Trigger keyword (normalized to UPPERCASE)
            flow_id: Flow that responds to this keyword
            bot_id: Bot ID for isolation
        """
        if not self.is_connected():
            return

        try:
            key = f"trigger:{bot_id}:{keyword.upper()}"
            # Use a set to support multiple flows per keyword per bot
            await self.redis.sadd(key, flow_id)
            logger.debug(f"Cached trigger keyword: {keyword} -> {flow_id} (bot: {bot_id})")
        except Exception as e:
            logger.error(f"Failed to cache trigger keyword {keyword}: {e}")

    async def get_flows_by_keyword(self, keyword: str, bot_id: str) -> List[str]:
        """
        Get flow IDs that respond to a trigger keyword within a specific bot.
        
        Args:
            keyword: Trigger keyword (will be normalized to UPPERCASE)
            bot_id: Bot ID for isolation
            
        Returns:
            List of flow IDs (empty if not found)
        """
        if not self.is_connected():
            return []

        try:
            key = f"trigger:{bot_id}:{keyword.upper()}"
            flow_ids = await self.redis.smembers(key)
            if flow_ids:
                logger.debug(f"Cache hit for trigger: {keyword} (bot: {bot_id})")
                return sorted(list(flow_ids))  # Sort for deterministic results
            return []
        except Exception as e:
            logger.error(f"Failed to get flows for keyword {keyword}: {e}")
            return []

    async def remove_trigger_keyword(self, keyword: str, flow_id: str, bot_id: str):
        """
        Remove a trigger keyword mapping (bot-scoped).
        
        Args:
            keyword: Trigger keyword (will be normalized to UPPERCASE)
            flow_id: Flow ID to remove
            bot_id: Bot ID for isolation
        """
        if not self.is_connected():
            return

        try:
            key = f"trigger:{bot_id}:{keyword.upper()}"
            await self.redis.srem(key, flow_id)
            # Clean up empty sets
            if await self.redis.scard(key) == 0:
                await self.redis.delete(key)
            logger.debug(f"Removed trigger keyword: {keyword} -> {flow_id} (bot: {bot_id})")
        except Exception as e:
            logger.error(f"Failed to remove trigger keyword {keyword}: {e}")

    async def invalidate_all_triggers_for_flow(self, flow_id: str, keywords: List[str], bot_id: str):
        """
        Remove all trigger keywords for a flow (bot-scoped).
        
        Args:
            flow_id: Flow ID
            keywords: List of keywords to remove
            bot_id: Bot ID for isolation
        """
        if not self.is_connected():
            return

        for keyword in keywords:
            await self.remove_trigger_keyword(keyword, flow_id, bot_id)

    # ==================== Rate Limiting ====================

    async def check_rate_limit_channel_user(
        self,
        channel: str,
        channel_user_id: str,
        max_requests: int = 10,
        window_seconds: int = 60
    ) -> bool:
        """
        Check if channel user is within rate limit (platform-agnostic).

        Args:
            channel: Communication channel (whatsapp, sms, telegram, etc.)
            channel_user_id: User identifier in the channel
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if within limit, False if exceeded

        Raises:
            SecurityServiceUnavailableError: If Redis is not connected (security requirement)
        """
        if not self.is_connected():
            # SECURITY: Don't allow bypass when Redis is down
            raise SecurityServiceUnavailableError("rate_limiting")

        try:
            key = f"ratelimit:channel:{channel}:{channel_user_id}"
            current = await self.redis.get(key)

            if current is None:
                # First request in window
                await self.redis.setex(key, window_seconds, 1)
                return True

            count = int(current)
            if count >= max_requests:
                logger.warning(f"Rate limit exceeded for {channel} user: {channel_user_id}")
                return False

            # Increment counter
            await self.redis.incr(key)
            return True
        except SecurityServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Rate limit check failed for {channel} user {channel_user_id}: {e}")
            raise SecurityServiceUnavailableError("rate_limiting")

    async def check_rate_limit_user(
        self,
        user_id: str,
        max_requests: int = 100,
        window_seconds: int = 60
    ) -> bool:
        """
        Check if user is within API rate limit.

        Args:
            user_id: User ID
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if within limit, False if exceeded

        Raises:
            SecurityServiceUnavailableError: If Redis is not connected (security requirement)
        """
        if not self.is_connected():
            # SECURITY: Don't allow bypass when Redis is down
            raise SecurityServiceUnavailableError("rate_limiting")

        try:
            key = f"ratelimit:user:{user_id}"
            current = await self.redis.get(key)

            if current is None:
                await self.redis.setex(key, window_seconds, 1)
                return True

            count = int(current)
            if count >= max_requests:
                logger.warning(f"Rate limit exceeded for user: {user_id}")
                return False

            await self.redis.incr(key)
            return True
        except SecurityServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Rate limit check failed for user {user_id}: {e}")
            raise SecurityServiceUnavailableError("rate_limiting")

    # ==================== Session Caching ====================

    async def cache_session(
        self,
        channel: str,
        channel_user_id: str,
        bot_id: str,
        session_data: Dict[str, Any],
        ttl: int = 1800
    ):
        """
        Cache active session data using composite key.
        
        Args:
            channel: Communication channel
            channel_user_id: User identifier in channel
            bot_id: Bot ID
            session_data: Session data
            ttl: Time to live in seconds (default: 30 minutes)
        """
        if not self.is_connected():
            return

        try:
            key = f"session:active:{channel}:{channel_user_id}:{bot_id}"
            await self.redis.setex(
                key,
                ttl,
                json.dumps(session_data, default=str)
            )
            logger.debug(f"Cached session for: {channel}:{channel_user_id}:{bot_id}")
        except Exception as e:
            logger.error(f"Failed to cache session: {e}")

    async def get_cached_session(
        self,
        channel: str,
        channel_user_id: str,
        bot_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached session data using composite key.
        
        Args:
            channel: Communication channel
            channel_user_id: User identifier in channel
            bot_id: Bot ID
            
        Returns:
            Session data or None if not cached
        """
        if not self.is_connected():
            return None

        try:
            key = f"session:active:{channel}:{channel_user_id}:{bot_id}"
            data = await self.redis.get(key)
            if data:
                logger.debug(f"Cache hit for session: {channel}:{channel_user_id}:{bot_id}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get cached session: {e}")
            return None

    async def invalidate_session_cache(
        self,
        channel: str,
        channel_user_id: str,
        bot_id: str
    ):
        """
        Invalidate cached session data using composite key.
        
        Args:
            channel: Communication channel
            channel_user_id: User identifier in channel
            bot_id: Bot ID
        """
        if not self.is_connected():
            return

        try:
            key = f"session:active:{channel}:{channel_user_id}:{bot_id}"
            await self.redis.delete(key)
            logger.debug(f"Invalidated session cache: {channel}:{channel_user_id}:{bot_id}")
        except Exception as e:
            logger.error(f"Failed to invalidate session cache: {e}")

    # ==================== QR Code Storage (Evolution API) ====================

    async def store_qr_code(
        self,
        bot_id: str,
        qr_code: str,
        instance_name: str,
        ttl: int = 60
    ):
        """
        Store QR code from Evolution API webhook

        QR codes have a short TTL (60 seconds default) since they expire quickly.

        Args:
            bot_id: Bot ID (UUID as string)
            qr_code: Base64-encoded QR code image
            instance_name: Evolution API instance name
            ttl: Time to live in seconds (default: 60)
        """
        if not self.is_connected():
            logger.warning("Redis not connected - QR code storage unavailable")
            return

        try:
            key = f"evolution:qr:{bot_id}"
            data = {
                "qr_code": qr_code,
                "instance_name": instance_name,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.redis.setex(
                key,
                ttl,
                json.dumps(data)
            )
            logger.info(f"Stored QR code for bot {bot_id} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Failed to store QR code for bot {bot_id}: {e}")

    async def get_qr_code(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve QR code for a bot

        Args:
            bot_id: Bot ID (UUID as string)

        Returns:
            Dict with qr_code, instance_name, timestamp, or None if not found
        """
        if not self.is_connected():
            return None

        try:
            key = f"evolution:qr:{bot_id}"
            data = await self.redis.get(key)
            if data:
                logger.debug(f"QR code cache hit for bot {bot_id}")
                return json.loads(data)
            logger.debug(f"QR code cache miss for bot {bot_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to get QR code for bot {bot_id}: {e}")
            return None

    async def delete_qr_code(self, bot_id: str):
        """
        Delete QR code for a bot

        Args:
            bot_id: Bot ID (UUID as string)
        """
        if not self.is_connected():
            return

        try:
            key = f"evolution:qr:{bot_id}"
            await self.redis.delete(key)
            logger.debug(f"Deleted QR code for bot {bot_id}")
        except Exception as e:
            logger.error(f"Failed to delete QR code for bot {bot_id}: {e}")

    # ==================== JWT Token Blacklist ====================

    async def blacklist_token(self, jti: str, ttl: int):
        """
        Add JWT token to blacklist.

        Args:
            jti: JWT ID (unique token identifier)
            ttl: Time until token naturally expires

        Raises:
            SecurityServiceUnavailableError: If Redis is not connected (security requirement)
        """
        if not self.is_connected():
            raise SecurityServiceUnavailableError("token_blacklist")

        try:
            key = f"blacklist:token:{jti}"
            await self.redis.setex(key, ttl, "1")
            logger.debug(f"Blacklisted token: {jti}")
        except SecurityServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Failed to blacklist token {jti}: {e}")
            raise SecurityServiceUnavailableError("token_blacklist")

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if JWT token is blacklisted.

        Args:
            jti: JWT ID

        Returns:
            True if blacklisted, False otherwise

        Raises:
            SecurityServiceUnavailableError: If Redis is not connected (security requirement)
        """
        if not self.is_connected():
            raise SecurityServiceUnavailableError("token_blacklist")

        try:
            key = f"blacklist:token:{jti}"
            exists = await self.redis.exists(key)
            return bool(exists)
        except SecurityServiceUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Failed to check token blacklist {jti}: {e}")
            raise SecurityServiceUnavailableError("token_blacklist")

    # ==================== Health Check ====================

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform Redis health check with timeout.

        Returns:
            Health status dict with circuit breaker state
        """
        circuit_state = await self.circuit_breaker.get_state()

        if not self.is_connected():
            return {
                "status": "unhealthy",
                "connected": False,
                "circuit_breaker": circuit_state,
                "distributed_circuit_breaker": True,
                "error": "Not connected"
            }

        try:
            # Wrap Redis operations with timeout to prevent hanging
            async with asyncio.timeout(HEALTH_CHECK_TIMEOUT_SECONDS):
                await self.redis.ping()
                info = await self.redis.info("server")

            return {
                "status": "healthy",
                "connected": True,
                "circuit_breaker": circuit_state,
                "distributed_circuit_breaker": True,
                "redis_version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds")
            }
        except asyncio.TimeoutError:
            logger.error(f"Redis health check timed out after {HEALTH_CHECK_TIMEOUT_SECONDS}s")
            await self.circuit_breaker.record_failure()
            return {
                "status": "unhealthy",
                "connected": False,
                "circuit_breaker": circuit_state,
                "distributed_circuit_breaker": True,
                "error": f"Health check timed out after {HEALTH_CHECK_TIMEOUT_SECONDS}s"
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            await self.circuit_breaker.record_failure()
            return {
                "status": "unhealthy",
                "connected": False,
                "circuit_breaker": circuit_state,
                "distributed_circuit_breaker": True,
                "error": str(e)
            }


# Global Redis manager instance
redis_manager = RedisManager()


def get_redis_manager() -> RedisManager:
    """
    Get the global Redis manager instance.

    Returns:
        RedisManager instance
    """
    return redis_manager