"""Redis Manager for Bot Builder v1.

Handles Redis operations for:
- Flow caching with automatic invalidation
- Rate limiting (per channel+user, per user)
- Trigger keyword lookup
- Active session caching
- JWT token blacklist
"""

import json
from typing import Optional, List, Dict, Any
from datetime import timedelta
import asyncio
import redis.asyncio as redis
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisManager:
    """Manages all Redis operations for the Bot Builder system."""

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self._connected = False
        self._reconnect_lock = asyncio.Lock()
        self._reconnect_attempts = 0

    async def connect(self):
        """Establish Redis connection."""
        try:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_keepalive=True,
            )
            # Test connection
            await self.redis.ping()
            self._connected = True
            self._reconnect_attempts = 0
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            # Don't raise - system should work without Redis (degraded performance)

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
            
            if self._reconnect_attempts >= settings.REDIS_MAX_RECONNECT_ATTEMPTS:
                logger.error(f"Max reconnection attempts ({settings.REDIS_MAX_RECONNECT_ATTEMPTS}) reached")
                return False
            
            # Clean up old connection before reconnecting to prevent leaks
            if self.redis:
                try:
                    await self.redis.close()
                    await self.redis.connection_pool.disconnect()
                except Exception as e:
                    logger.warning(f"Error cleaning up old connection: {e}")
            
            self._reconnect_attempts += 1
            backoff = min(2 ** self._reconnect_attempts, settings.REDIS_RECONNECT_BACKOFF_CAP)
            
            logger.info(f"Attempting Redis reconnection (attempt {self._reconnect_attempts}/{settings.REDIS_MAX_RECONNECT_ATTEMPTS})")
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
            required_keys = {'name', 'start_node_id', 'nodes'}
            if not all(key in flow_data for key in required_keys):
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
        """
        if not self.is_connected():
            return True  # Allow if Redis unavailable

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
        except Exception as e:
            logger.error(f"Failed to check rate limit for {channel} user {channel_user_id}: {e}")
            return True  # Allow on error

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
        """
        if not self.is_connected():
            return True

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
        except Exception as e:
            logger.error(f"Failed to check rate limit for user {user_id}: {e}")
            return True

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

    # ==================== JWT Token Blacklist ====================

    async def blacklist_token(self, jti: str, ttl: int):
        """
        Add JWT token to blacklist.
        
        Args:
            jti: JWT ID (unique token identifier)
            ttl: Time until token naturally expires
        """
        if not self.is_connected():
            return

        try:
            key = f"blacklist:token:{jti}"
            await self.redis.setex(key, ttl, "1")
            logger.debug(f"Blacklisted token: {jti}")
        except Exception as e:
            logger.error(f"Failed to blacklist token {jti}: {e}")

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if JWT token is blacklisted.
        
        Args:
            jti: JWT ID
            
        Returns:
            True if blacklisted, False otherwise
        """
        if not self.is_connected():
            return False  # Allow if Redis unavailable

        try:
            key = f"blacklist:token:{jti}"
            exists = await self.redis.exists(key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Failed to check token blacklist {jti}: {e}")
            return False

    # ==================== Health Check ====================

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform Redis health check.
        
        Returns:
            Health status dict
        """
        if not self.is_connected():
            return {
                "status": "unhealthy",
                "connected": False,
                "error": "Not connected"
            }

        try:
            await self.redis.ping()
            info = await self.redis.info("server")
            return {
                "status": "healthy",
                "connected": True,
                "redis_version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds")
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }


# Global Redis manager instance
redis_manager = RedisManager()