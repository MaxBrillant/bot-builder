"""
Distributed Circuit Breaker
Prevents cascading Redis failures. State stored in Redis so all API instances share it.
Accepts a redis client via set_redis() — no dependency on RedisManager or app config.
"""
import asyncio
from typing import Optional
from datetime import datetime
from enum import Enum
import redis.asyncio as redis
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ===== Circuit Breaker Pattern (Distributed via Redis) =====
class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class DistributedCircuitBreaker:
    """
    Distributed circuit breaker for Redis operations using Redis for state coordination.

    SECURITY: State is stored in Redis so all API instances share the same circuit state.
    This ensures consistent behavior across horizontally scaled deployments.

    Prevents cascading failures by:
    - Opening circuit after failure threshold (shared across all instances)
    - Rejecting requests while OPEN (fast fail)
    - Periodically testing recovery (HALF_OPEN)
    - Closing circuit when successful again

    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Too many failures, reject all requests immediately
    - HALF_OPEN: Testing if service recovered, allow one test request

    Fallback: If Redis is unavailable for state storage, falls back to local state.
    """

    # Redis keys for distributed state
    STATE_KEY = "circuit_breaker:state"
    FAILURES_KEY = "circuit_breaker:failures"
    SUCCESSES_KEY = "circuit_breaker:successes"
    LAST_FAILURE_KEY = "circuit_breaker:last_failure"

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2
    ):
        """
        Initialize distributed circuit breaker

        Args:
            failure_threshold: Failures before opening circuit
            timeout_seconds: Seconds to wait before attempting recovery
            success_threshold: Successes needed to close circuit from HALF_OPEN
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold

        # Local fallback state (used when Redis unavailable for state storage)
        self._local_state = CircuitState.CLOSED
        self._local_failures = 0
        self._local_successes = 0
        self._local_last_failure: Optional[datetime] = None

        # Reference to Redis client (set by RedisManager after connection)
        self._redis: Optional[redis.Redis] = None

    def set_redis(self, redis_client: redis.Redis):
        """Set Redis client for distributed state storage"""
        self._redis = redis_client

    async def _get_state_from_redis(self) -> Optional[dict]:
        """Get circuit breaker state from Redis"""
        if not self._redis:
            return None

        try:
            pipe = self._redis.pipeline()
            pipe.get(self.STATE_KEY)
            pipe.get(self.FAILURES_KEY)
            pipe.get(self.SUCCESSES_KEY)
            pipe.get(self.LAST_FAILURE_KEY)
            results = await pipe.execute()

            return {
                "state": results[0] or CircuitState.CLOSED.value,
                "failures": int(results[1] or 0),
                "successes": int(results[2] or 0),
                "last_failure": float(results[3]) if results[3] else None
            }
        except Exception as e:
            logger.warning(f"Failed to get circuit breaker state from Redis: {e}")
            return None

    async def _set_state_in_redis(self, state: str, failures: int, successes: int, last_failure: Optional[float]):
        """Set circuit breaker state in Redis"""
        if not self._redis:
            return

        try:
            pipe = self._redis.pipeline()
            # State expires after 5 minutes (self-healing if Redis state gets stuck)
            pipe.setex(self.STATE_KEY, 300, state)
            pipe.setex(self.FAILURES_KEY, 300, str(failures))
            pipe.setex(self.SUCCESSES_KEY, 300, str(successes))
            if last_failure:
                pipe.setex(self.LAST_FAILURE_KEY, 300, str(last_failure))
            else:
                pipe.delete(self.LAST_FAILURE_KEY)
            await pipe.execute()
        except Exception as e:
            logger.warning(f"Failed to set circuit breaker state in Redis: {e}")

    async def record_success(self):
        """Record successful operation (distributed)"""
        state_data = await self._get_state_from_redis()

        if state_data:
            # Use Redis state
            current_state = CircuitState(state_data["state"])
            successes = state_data["successes"]
            failures = state_data["failures"]

            if current_state == CircuitState.HALF_OPEN:
                successes += 1
                logger.debug(
                    f"Circuit breaker: Success in HALF_OPEN ({successes}/{self.success_threshold})"
                )

                if successes >= self.success_threshold:
                    # Close circuit - service recovered
                    await self._set_state_in_redis(CircuitState.CLOSED.value, 0, 0, None)
                    logger.info("Circuit breaker: CLOSED (service recovered)")
                else:
                    await self._set_state_in_redis(current_state.value, failures, successes, state_data["last_failure"])

            elif current_state == CircuitState.CLOSED and failures > 0:
                # Reset failure counter on success
                await self._set_state_in_redis(CircuitState.CLOSED.value, 0, 0, None)
        else:
            # Fallback to local state
            if self._local_state == CircuitState.HALF_OPEN:
                self._local_successes += 1
                if self._local_successes >= self.success_threshold:
                    self._local_state = CircuitState.CLOSED
                    self._local_failures = 0
                    self._local_successes = 0
                    logger.info("Circuit breaker (local): CLOSED (service recovered)")
            elif self._local_state == CircuitState.CLOSED and self._local_failures > 0:
                self._local_failures = 0

    async def record_failure(self):
        """Record failed operation (distributed)"""
        now = datetime.utcnow().timestamp()
        state_data = await self._get_state_from_redis()

        if state_data:
            # Use Redis state
            current_state = CircuitState(state_data["state"])
            failures = state_data["failures"]

            if current_state == CircuitState.HALF_OPEN:
                # Failed during recovery test - reopen circuit
                await self._set_state_in_redis(CircuitState.OPEN.value, failures, 0, now)
                logger.warning("Circuit breaker: OPEN (recovery test failed)")

            elif current_state == CircuitState.CLOSED:
                failures += 1
                logger.debug(
                    f"Circuit breaker: Failure recorded ({failures}/{self.failure_threshold})"
                )

                if failures >= self.failure_threshold:
                    # Too many failures - open circuit
                    await self._set_state_in_redis(CircuitState.OPEN.value, failures, 0, now)
                    logger.warning(
                        f"Circuit breaker: OPEN (threshold reached: {failures} failures)"
                    )
                else:
                    await self._set_state_in_redis(current_state.value, failures, 0, now)
        else:
            # Fallback to local state
            self._local_last_failure = datetime.utcnow()
            if self._local_state == CircuitState.HALF_OPEN:
                self._local_state = CircuitState.OPEN
                self._local_successes = 0
                logger.warning("Circuit breaker (local): OPEN (recovery test failed)")
            elif self._local_state == CircuitState.CLOSED:
                self._local_failures += 1
                if self._local_failures >= self.failure_threshold:
                    self._local_state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker (local): OPEN (threshold reached)")

    async def can_attempt(self) -> bool:
        """
        Check if operation should be attempted (distributed)

        Returns:
            True if operation should proceed, False if circuit is OPEN
        """
        state_data = await self._get_state_from_redis()

        if state_data:
            # Use Redis state
            current_state = CircuitState(state_data["state"])
            last_failure = state_data["last_failure"]

            if current_state == CircuitState.CLOSED:
                return True

            if current_state == CircuitState.OPEN:
                # Check if timeout expired - try half-open
                if last_failure:
                    elapsed = datetime.utcnow().timestamp() - last_failure
                    if elapsed >= self.timeout_seconds:
                        await self._set_state_in_redis(
                            CircuitState.HALF_OPEN.value,
                            state_data["failures"],
                            0,
                            last_failure
                        )
                        logger.info("Circuit breaker: HALF_OPEN (attempting recovery)")
                        return True
                # Still in timeout period - reject request
                return False

            # HALF_OPEN state - allow attempt
            return True
        else:
            # Fallback to local state
            if self._local_state == CircuitState.CLOSED:
                return True

            if self._local_state == CircuitState.OPEN:
                if self._local_last_failure:
                    elapsed = (datetime.utcnow() - self._local_last_failure).total_seconds()
                    if elapsed >= self.timeout_seconds:
                        self._local_state = CircuitState.HALF_OPEN
                        self._local_successes = 0
                        logger.info("Circuit breaker (local): HALF_OPEN (attempting recovery)")
                        return True
                return False

            return True

    async def get_state(self) -> str:
        """Get current circuit state"""
        state_data = await self._get_state_from_redis()
        if state_data:
            return state_data["state"]
        return self._local_state.value

    async def reset(self):
        """Manually reset circuit breaker"""
        await self._set_state_in_redis(CircuitState.CLOSED.value, 0, 0, None)
        self._local_state = CircuitState.CLOSED
        self._local_failures = 0
        self._local_successes = 0
        self._local_last_failure = None
        logger.info("Circuit breaker: Manually reset to CLOSED")


# Backward compatibility alias
CircuitBreaker = DistributedCircuitBreaker
