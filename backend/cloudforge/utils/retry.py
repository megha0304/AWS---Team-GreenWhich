"""
Retry utilities with exponential backoff for error handling.

This module provides retry logic with exponential backoff for handling transient
failures in external API calls and AWS service interactions.

Requirements: 1.6, 11.1
"""

import asyncio
import logging
from typing import Callable, TypeVar, Any, Optional, Type, Tuple, Literal, List, Dict
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TransientError(Exception):
    """Base exception for transient errors that should trigger retries."""
    pass


class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts have been exhausted."""
    
    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Retry exhausted after {attempts} attempts. Last error: {last_error}"
        )


async def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs: Any
) -> T:
    """
    Retry an async function with exponential backoff.
    
    This function implements exponential backoff retry logic for handling transient
    failures. The delay between retries increases exponentially: delay = base_delay^attempt,
    capped at max_delay.
    
    Args:
        func: Async function to retry
        *args: Positional arguments to pass to func
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay multiplier for exponential backoff (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        retryable_exceptions: Tuple of exception types that should trigger retries.
                            If None, all exceptions trigger retries.
        **kwargs: Keyword arguments to pass to func
    
    Returns:
        Result of the function call
    
    Raises:
        RetryExhaustedError: If all retry attempts are exhausted
        Exception: If a non-retryable exception occurs
    
    Example:
        >>> async def fetch_data():
        ...     # API call that might fail transiently
        ...     return await api_client.get("/data")
        >>> 
        >>> result = await retry_with_backoff(
        ...     fetch_data,
        ...     max_retries=3,
        ...     base_delay=2.0
        ... )
    
    Requirements: 1.6, 11.1
    Property 48: Exponential backoff for all APIs
    """
    last_exception: Optional[Exception] = None
    
    if max_retries == 0:
        raise RetryExhaustedError(0, RuntimeError("max_retries is 0, no attempts made"))
    
    for attempt in range(max_retries):
        try:
            # Attempt to call the function
            result = await func(*args, **kwargs)
            
            # Log success if this was a retry
            if attempt > 0:
                func_name = getattr(func, '__name__', repr(func))
                logger.info(
                    f"Retry succeeded on attempt {attempt + 1}/{max_retries}",
                    extra={
                        "function": func_name,
                        "attempt": attempt + 1,
                        "max_retries": max_retries
                    }
                )
            
            return result
        
        except Exception as e:
            last_exception = e
            
            # Check if this exception should trigger a retry
            if retryable_exceptions and not isinstance(e, retryable_exceptions):
                func_name = getattr(func, '__name__', repr(func))
                logger.error(
                    f"Non-retryable exception in {func_name}: {type(e).__name__}",
                    extra={
                        "function": func_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                raise
            
            # If this was the last attempt, raise RetryExhaustedError
            if attempt == max_retries - 1:
                func_name = getattr(func, '__name__', repr(func))
                logger.error(
                    f"Retry exhausted for {func_name} after {max_retries} attempts",
                    extra={
                        "function": func_name,
                        "attempts": max_retries,
                        "last_error_type": type(e).__name__,
                        "last_error_message": str(e)
                    }
                )
                raise RetryExhaustedError(max_retries, e)
            
            # Calculate exponential backoff delay
            delay = min(base_delay ** attempt, max_delay)
            
            func_name = getattr(func, '__name__', repr(func))
            logger.warning(
                f"Retry {attempt + 1}/{max_retries} for {func_name} after {delay:.2f}s",
                extra={
                    "function": func_name,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "delay_seconds": delay,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            # Wait before retrying
            await asyncio.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise RetryExhaustedError(max_retries, last_exception)
    raise RuntimeError("Unexpected state in retry_with_backoff")


def retry_with_backoff_sync(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    **kwargs: Any
) -> T:
    """
    Retry a synchronous function with exponential backoff.
    
    This is the synchronous version of retry_with_backoff for use with
    non-async functions.
    
    Args:
        func: Synchronous function to retry
        *args: Positional arguments to pass to func
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay multiplier for exponential backoff (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        retryable_exceptions: Tuple of exception types that should trigger retries.
                            If None, all exceptions trigger retries.
        **kwargs: Keyword arguments to pass to func
    
    Returns:
        Result of the function call
    
    Raises:
        RetryExhaustedError: If all retry attempts are exhausted
        Exception: If a non-retryable exception occurs
    
    Example:
        >>> def fetch_data():
        ...     # API call that might fail transiently
        ...     return api_client.get("/data")
        >>> 
        >>> result = retry_with_backoff_sync(
        ...     fetch_data,
        ...     max_retries=3,
        ...     base_delay=2.0
        ... )
    
    Requirements: 1.6, 11.1
    """
    import time
    
    last_exception: Optional[Exception] = None
    
    if max_retries == 0:
        raise RetryExhaustedError(0, RuntimeError("max_retries is 0, no attempts made"))
    
    for attempt in range(max_retries):
        try:
            # Attempt to call the function
            result = func(*args, **kwargs)
            
            # Log success if this was a retry
            if attempt > 0:
                func_name = getattr(func, '__name__', repr(func))
                logger.info(
                    f"Retry succeeded on attempt {attempt + 1}/{max_retries}",
                    extra={
                        "function": func_name,
                        "attempt": attempt + 1,
                        "max_retries": max_retries
                    }
                )
            
            return result
        
        except Exception as e:
            last_exception = e
            
            # Check if this exception should trigger a retry
            if retryable_exceptions and not isinstance(e, retryable_exceptions):
                func_name = getattr(func, '__name__', repr(func))
                logger.error(
                    f"Non-retryable exception in {func_name}: {type(e).__name__}",
                    extra={
                        "function": func_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                raise
            
            # If this was the last attempt, raise RetryExhaustedError
            if attempt == max_retries - 1:
                func_name = getattr(func, '__name__', repr(func))
                logger.error(
                    f"Retry exhausted for {func_name} after {max_retries} attempts",
                    extra={
                        "function": func_name,
                        "attempts": max_retries,
                        "last_error_type": type(e).__name__,
                        "last_error_message": str(e)
                    }
                )
                raise RetryExhaustedError(max_retries, e)
            
            # Calculate exponential backoff delay
            delay = min(base_delay ** attempt, max_delay)
            
            func_name = getattr(func, '__name__', repr(func))
            logger.warning(
                f"Retry {attempt + 1}/{max_retries} for {func_name} after {delay:.2f}s",
                extra={
                    "function": func_name,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "delay_seconds": delay,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            # Wait before retrying
            time.sleep(delay)
    
    # This should never be reached, but just in case
    if last_exception:
        raise RetryExhaustedError(max_retries, last_exception)
    raise RuntimeError("Unexpected state in retry_with_backoff_sync")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator for adding retry logic with exponential backoff to async functions.
    
    This decorator wraps an async function with retry_with_backoff logic.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay multiplier for exponential backoff (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        retryable_exceptions: Tuple of exception types that should trigger retries.
                            If None, all exceptions trigger retries.
    
    Returns:
        Decorated function with retry logic
    
    Example:
        >>> @with_retry(max_retries=3, base_delay=2.0)
        ... async def fetch_data():
        ...     return await api_client.get("/data")
        >>> 
        >>> result = await fetch_data()
    
    Requirements: 1.6, 11.1
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_with_backoff(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
        return wrapper
    return decorator


def with_retry_sync(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
):
    """
    Decorator for adding retry logic with exponential backoff to synchronous functions.
    
    This decorator wraps a synchronous function with retry_with_backoff_sync logic.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay multiplier for exponential backoff (default: 2.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        retryable_exceptions: Tuple of exception types that should trigger retries.
                            If None, all exceptions trigger retries.
    
    Returns:
        Decorated function with retry logic
    
    Example:
        >>> @with_retry_sync(max_retries=3, base_delay=2.0)
        ... def fetch_data():
        ...     return api_client.get("/data")
        >>> 
        >>> result = fetch_data()
    
    Requirements: 1.6, 11.1
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return retry_with_backoff_sync(
                func,
                *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
        return wrapper
    return decorator



class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    
    def __init__(self, service_name: str, timeout_remaining: float):
        self.service_name = service_name
        self.timeout_remaining = timeout_remaining
        super().__init__(
            f"Circuit breaker is open for {service_name}. "
            f"Retry in {timeout_remaining:.1f} seconds."
        )


class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered
    
    State transitions:
    - CLOSED -> OPEN: When failure count exceeds threshold within time window
    - OPEN -> HALF_OPEN: After timeout period expires
    - HALF_OPEN -> CLOSED: When a request succeeds
    - HALF_OPEN -> OPEN: When a request fails
    
    Requirements: 11.5
    Property 52: Circuit breaker activation
    """
    
    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        timeout_seconds: int = 30,
        time_window_seconds: int = 60
    ):
        """
        Initialize circuit breaker.
        
        Args:
            service_name: Name of the service being protected
            failure_threshold: Number of failures before opening circuit (default: 5)
            timeout_seconds: Seconds to wait before attempting recovery (default: 30)
            time_window_seconds: Time window for counting failures (default: 60)
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.time_window_seconds = time_window_seconds
        
        self.state: Literal["closed", "open", "half_open"] = "closed"
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.opened_at: Optional[float] = None
        self.failure_timestamps: List[float] = []
        
        self.logger = logging.getLogger(__name__)
    
    def _clean_old_failures(self) -> None:
        """Remove failure timestamps outside the time window."""
        import time
        current_time = time.time()
        cutoff_time = current_time - self.time_window_seconds
        self.failure_timestamps = [
            ts for ts in self.failure_timestamps if ts > cutoff_time
        ]
    
    def _should_open(self) -> bool:
        """Check if circuit should open based on failure count in time window."""
        self._clean_old_failures()
        return len(self.failure_timestamps) >= self.failure_threshold
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        import time
        if self.opened_at is None:
            return False
        return time.time() - self.opened_at >= self.timeout_seconds
    
    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == "half_open":
            self.logger.info(
                f"Circuit breaker for {self.service_name} closing after successful call",
                extra={
                    "service_name": self.service_name,
                    "previous_state": "half_open",
                    "new_state": "closed"
                }
            )
            self.state = "closed"
            self.failure_count = 0
            self.failure_timestamps = []
            self.opened_at = None
    
    def record_failure(self) -> None:
        """Record a failed call."""
        import time
        current_time = time.time()
        
        self.failure_count += 1
        self.last_failure_time = current_time
        self.failure_timestamps.append(current_time)
        
        if self.state == "closed":
            if self._should_open():
                self.state = "open"
                self.opened_at = current_time
                self.logger.error(
                    f"Circuit breaker opened for {self.service_name} "
                    f"after {len(self.failure_timestamps)} failures in {self.time_window_seconds}s",
                    extra={
                        "service_name": self.service_name,
                        "failure_count": len(self.failure_timestamps),
                        "time_window_seconds": self.time_window_seconds,
                        "timeout_seconds": self.timeout_seconds
                    }
                )
                # Publish metric for circuit breaker state
                self._publish_state_metric()
        
        elif self.state == "half_open":
            self.state = "open"
            self.opened_at = current_time
            self.logger.warning(
                f"Circuit breaker reopened for {self.service_name} after failed recovery attempt",
                extra={
                    "service_name": self.service_name,
                    "previous_state": "half_open",
                    "new_state": "open"
                }
            )
            self._publish_state_metric()
    
    def _publish_state_metric(self) -> None:
        """Publish circuit breaker state metric to CloudWatch."""
        # Placeholder for CloudWatch metrics publishing
        # This will be implemented when CloudWatch integration is added
        state_value = {"closed": 0, "half_open": 1, "open": 2}[self.state]
        self.logger.debug(
            f"Publishing circuit breaker state metric",
            extra={
                "service_name": self.service_name,
                "state": self.state,
                "state_value": state_value
            }
        )
    
    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result of the function call
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception raised by func
        
        Example:
            >>> breaker = CircuitBreaker("external-api")
            >>> result = await breaker.call(api_client.fetch_data, "param1")
        
        Requirements: 11.5
        """
        import time
        
        # Check if circuit should transition from open to half-open
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                self.logger.info(
                    f"Circuit breaker for {self.service_name} entering half-open state",
                    extra={
                        "service_name": self.service_name,
                        "previous_state": "open",
                        "new_state": "half_open"
                    }
                )
            else:
                timeout_remaining = self.timeout_seconds - (time.time() - self.opened_at)
                raise CircuitBreakerOpenError(self.service_name, timeout_remaining)
        
        # Attempt to call the function
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def call_sync(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a synchronous function with circuit breaker protection.
        
        Args:
            func: Synchronous function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
        
        Returns:
            Result of the function call
        
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception raised by func
        
        Example:
            >>> breaker = CircuitBreaker("external-api")
            >>> result = breaker.call_sync(api_client.fetch_data, "param1")
        
        Requirements: 11.5
        """
        import time
        
        # Check if circuit should transition from open to half-open
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                self.logger.info(
                    f"Circuit breaker for {self.service_name} entering half-open state",
                    extra={
                        "service_name": self.service_name,
                        "previous_state": "open",
                        "new_state": "half_open"
                    }
                )
            else:
                timeout_remaining = self.timeout_seconds - (time.time() - self.opened_at)
                raise CircuitBreakerOpenError(self.service_name, timeout_remaining)
        
        # Attempt to call the function
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state information.
        
        Returns:
            Dictionary with state information
        """
        import time
        return {
            "service_name": self.service_name,
            "state": self.state,
            "failure_count": len(self.failure_timestamps),
            "failure_threshold": self.failure_threshold,
            "time_window_seconds": self.time_window_seconds,
            "timeout_seconds": self.timeout_seconds,
            "opened_at": self.opened_at,
            "time_until_half_open": (
                self.timeout_seconds - (time.time() - self.opened_at)
                if self.opened_at and self.state == "open"
                else None
            )
        }
