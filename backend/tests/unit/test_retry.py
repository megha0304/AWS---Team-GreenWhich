"""
Unit tests for retry utilities with exponential backoff.

Tests the retry_with_backoff function and related utilities for proper
exponential backoff behavior, logging, and error handling.

Requirements: 1.6, 11.1
"""

import asyncio
import logging
import time
import pytest
from unittest.mock import AsyncMock, Mock, patch, call

from cloudforge.utils.retry import (
    retry_with_backoff,
    retry_with_backoff_sync,
    with_retry,
    with_retry_sync,
    TransientError,
    RetryExhaustedError,
)


class TestRetryWithBackoff:
    """Test suite for async retry_with_backoff function."""
    
    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """Test that successful calls on first attempt don't retry."""
        # Arrange
        mock_func = AsyncMock(return_value="success")
        
        # Act
        result = await retry_with_backoff(mock_func, max_retries=3)
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_successful_after_retries(self):
        """Test that function succeeds after transient failures."""
        # Arrange
        mock_func = AsyncMock(side_effect=[
            Exception("Transient error 1"),
            Exception("Transient error 2"),
            "success"
        ])
        
        # Act
        result = await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test that RetryExhaustedError is raised after max retries."""
        # Arrange
        mock_func = AsyncMock(side_effect=Exception("Persistent error"))
        
        # Act & Assert
        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        assert mock_func.call_count == 3
        assert exc_info.value.attempts == 3
        assert "Persistent error" in str(exc_info.value.last_error)
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self):
        """Test that delays follow exponential backoff pattern."""
        # Arrange
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "success"
        ])
        base_delay = 2.0
        
        # Act
        start_time = time.time()
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(
                mock_func,
                max_retries=3,
                base_delay=base_delay
            )
        
        # Assert
        assert result == "success"
        assert mock_sleep.call_count == 2
        
        # Verify exponential backoff: delay = base_delay^attempt
        # Attempt 0 fails -> delay = 2.0^0 = 1.0
        # Attempt 1 fails -> delay = 2.0^1 = 2.0
        expected_delays = [1.0, 2.0]
        actual_delays = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert actual_delays == expected_delays
    
    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        # Arrange
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "success"
        ])
        
        # Act
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(
                mock_func,
                max_retries=3,
                base_delay=100.0,
                max_delay=5.0
            )
        
        # Assert
        assert result == "success"
        # All delays should be capped at max_delay
        for call_args in mock_sleep.call_args_list:
            assert call_args[0][0] <= 5.0
    
    @pytest.mark.asyncio
    async def test_retryable_exceptions_filter(self):
        """Test that only specified exceptions trigger retries."""
        # Arrange
        class RetryableError(Exception):
            pass
        
        class NonRetryableError(Exception):
            pass
        
        mock_func = AsyncMock(side_effect=NonRetryableError("Should not retry"))
        
        # Act & Assert
        with pytest.raises(NonRetryableError):
            await retry_with_backoff(
                mock_func,
                max_retries=3,
                base_delay=0.01,
                retryable_exceptions=(RetryableError,)
            )
        
        # Should only be called once (no retries)
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retryable_exceptions_allow_retry(self):
        """Test that specified exceptions do trigger retries."""
        # Arrange
        class RetryableError(Exception):
            pass
        
        mock_func = AsyncMock(side_effect=[
            RetryableError("Retry this"),
            "success"
        ])
        
        # Act
        result = await retry_with_backoff(
            mock_func,
            max_retries=3,
            base_delay=0.01,
            retryable_exceptions=(RetryableError,)
        )
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_function_with_args_and_kwargs(self):
        """Test that function arguments are passed correctly."""
        # Arrange
        mock_func = AsyncMock(return_value="success")
        
        # Act
        result = await retry_with_backoff(
            mock_func,
            "arg1",
            "arg2",
            max_retries=3,
            kwarg1="value1",
            kwarg2="value2"
        )
        
        # Assert
        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1", kwarg2="value2")
    
    @pytest.mark.asyncio
    async def test_logging_on_retry(self, caplog):
        """Test that retry attempts are logged with appropriate level."""
        # Arrange
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            "success"
        ])
        
        # Act
        with caplog.at_level(logging.WARNING):
            result = await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        # Assert
        assert result == "success"
        assert any("Retry 1/3" in record.message for record in caplog.records)
    
    @pytest.mark.asyncio
    async def test_logging_on_success_after_retry(self, caplog):
        """Test that successful retry is logged."""
        # Arrange
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            "success"
        ])
        
        # Act
        with caplog.at_level(logging.INFO):
            result = await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        # Assert
        assert result == "success"
        assert any("Retry succeeded" in record.message for record in caplog.records)
    
    @pytest.mark.asyncio
    async def test_logging_on_exhausted(self, caplog):
        """Test that exhausted retries are logged as error."""
        # Arrange
        mock_func = AsyncMock(side_effect=Exception("Persistent error"))
        
        # Act & Assert
        with caplog.at_level(logging.ERROR):
            with pytest.raises(RetryExhaustedError):
                await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        assert any("Retry exhausted" in record.message for record in caplog.records)


class TestRetryWithBackoffSync:
    """Test suite for synchronous retry_with_backoff_sync function."""
    
    def test_successful_first_attempt(self):
        """Test that successful calls on first attempt don't retry."""
        # Arrange
        mock_func = Mock(return_value="success")
        
        # Act
        result = retry_with_backoff_sync(mock_func, max_retries=3)
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_successful_after_retries(self):
        """Test that function succeeds after transient failures."""
        # Arrange
        mock_func = Mock(side_effect=[
            Exception("Transient error 1"),
            Exception("Transient error 2"),
            "success"
        ])
        
        # Act
        result = retry_with_backoff_sync(mock_func, max_retries=3, base_delay=0.01)
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retry_exhausted(self):
        """Test that RetryExhaustedError is raised after max retries."""
        # Arrange
        mock_func = Mock(side_effect=Exception("Persistent error"))
        
        # Act & Assert
        with pytest.raises(RetryExhaustedError) as exc_info:
            retry_with_backoff_sync(mock_func, max_retries=3, base_delay=0.01)
        
        assert mock_func.call_count == 3
        assert exc_info.value.attempts == 3
    
    def test_exponential_backoff_delays(self):
        """Test that delays follow exponential backoff pattern."""
        # Arrange
        mock_func = Mock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "success"
        ])
        base_delay = 2.0
        
        # Act
        with patch("time.sleep") as mock_sleep:
            result = retry_with_backoff_sync(
                mock_func,
                max_retries=3,
                base_delay=base_delay
            )
        
        # Assert
        assert result == "success"
        assert mock_sleep.call_count == 2
        
        # Verify exponential backoff
        expected_delays = [1.0, 2.0]
        actual_delays = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert actual_delays == expected_delays


class TestWithRetryDecorator:
    """Test suite for @with_retry decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_successful(self):
        """Test that decorator works for successful calls."""
        # Arrange
        @with_retry(max_retries=3, base_delay=0.01)
        async def test_func():
            return "success"
        
        # Act
        result = await test_func()
        
        # Assert
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_decorator_with_retries(self):
        """Test that decorator retries on failure."""
        # Arrange
        call_count = 0
        
        @with_retry(max_retries=3, base_delay=0.01)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return "success"
        
        # Act
        result = await test_func()
        
        # Assert
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_decorator_exhausted(self):
        """Test that decorator raises RetryExhaustedError."""
        # Arrange
        @with_retry(max_retries=3, base_delay=0.01)
        async def test_func():
            raise Exception("Persistent error")
        
        # Act & Assert
        with pytest.raises(RetryExhaustedError):
            await test_func()


class TestWithRetrySyncDecorator:
    """Test suite for @with_retry_sync decorator."""
    
    def test_decorator_successful(self):
        """Test that decorator works for successful calls."""
        # Arrange
        @with_retry_sync(max_retries=3, base_delay=0.01)
        def test_func():
            return "success"
        
        # Act
        result = test_func()
        
        # Assert
        assert result == "success"
    
    def test_decorator_with_retries(self):
        """Test that decorator retries on failure."""
        # Arrange
        call_count = 0
        
        @with_retry_sync(max_retries=3, base_delay=0.01)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Transient error")
            return "success"
        
        # Act
        result = test_func()
        
        # Assert
        assert result == "success"
        assert call_count == 3


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_zero_retries(self):
        """Test behavior with max_retries=0."""
        # Arrange
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act & Assert
        with pytest.raises(RetryExhaustedError) as exc_info:
            await retry_with_backoff(mock_func, max_retries=0, base_delay=0.01)
        
        # Should fail immediately without retries
        assert mock_func.call_count == 0
        assert exc_info.value.attempts == 0
    
    @pytest.mark.asyncio
    async def test_one_retry(self):
        """Test behavior with max_retries=1."""
        # Arrange
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act & Assert
        with pytest.raises(RetryExhaustedError):
            await retry_with_backoff(mock_func, max_retries=1, base_delay=0.01)
        
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_very_large_base_delay(self):
        """Test that very large base_delay is capped by max_delay."""
        # Arrange
        mock_func = AsyncMock(side_effect=[Exception("Error"), "success"])
        
        # Act
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(
                mock_func,
                max_retries=2,
                base_delay=1000.0,
                max_delay=1.0
            )
        
        # Assert
        assert result == "success"
        # Delay should be capped at max_delay
        assert mock_sleep.call_args[0][0] == 1.0
    
    @pytest.mark.asyncio
    async def test_function_name_in_logs(self, caplog):
        """Test that function name appears in log messages."""
        # Arrange
        async def my_test_function():
            raise Exception("Error")
        
        # Act & Assert
        with caplog.at_level(logging.WARNING):
            with pytest.raises(RetryExhaustedError):
                await retry_with_backoff(my_test_function, max_retries=2, base_delay=0.01)
        
        assert any("my_test_function" in record.message for record in caplog.records)


class TestRequirementValidation:
    """Test that implementation meets specific requirements."""
    
    @pytest.mark.asyncio
    async def test_requirement_1_6_exponential_backoff(self):
        """
        Requirement 1.6: WHEN API calls fail, THE Bug_Detective_Agent SHALL 
        implement exponential backoff retry logic with maximum 3 attempts.
        """
        # Arrange
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "success"
        ])
        
        # Act
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await retry_with_backoff(
                mock_func,
                max_retries=3,
                base_delay=2.0
            )
        
        # Assert
        assert result == "success"
        assert mock_func.call_count == 3
        
        # Verify exponential backoff with base 2.0
        delays = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0]  # 2.0^0=1.0, 2.0^1=2.0
    
    @pytest.mark.asyncio
    async def test_requirement_11_1_exponential_backoff_all_apis(self):
        """
        Requirement 11.1: THE System SHALL implement exponential backoff 
        for all external API calls.
        
        Property 48: For any external API call, failures should trigger 
        exponential backoff retries with base 2.0 and max 3 attempts.
        """
        # Arrange
        mock_api_call = AsyncMock(side_effect=[
            Exception("Network timeout"),
            Exception("Service unavailable"),
            {"status": "success"}
        ])
        
        # Act
        result = await retry_with_backoff(
            mock_api_call,
            max_retries=3,
            base_delay=2.0
        )
        
        # Assert
        assert result == {"status": "success"}
        assert mock_api_call.call_count == 3
    
    @pytest.mark.asyncio
    async def test_configurable_max_retries(self):
        """Test that max_retries is configurable as per task requirements."""
        # Arrange
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act & Assert - Test with different max_retries values
        for max_retries in [1, 2, 3, 5]:
            mock_func.reset_mock()
            with pytest.raises(RetryExhaustedError):
                await retry_with_backoff(mock_func, max_retries=max_retries, base_delay=0.01)
            assert mock_func.call_count == max_retries
    
    @pytest.mark.asyncio
    async def test_configurable_base_delay(self):
        """Test that base_delay is configurable as per task requirements."""
        # Act & Assert - Test with different base_delay values
        for base_delay in [1.5, 2.0, 3.0]:
            mock_func = AsyncMock(side_effect=[Exception("Error"), "success"])
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await retry_with_backoff(
                    mock_func,
                    max_retries=2,
                    base_delay=base_delay
                )
            
            assert result == "success"
            # First delay should be base_delay^0 = 1.0
            assert mock_sleep.call_args[0][0] == 1.0
    
    @pytest.mark.asyncio
    async def test_logging_for_retry_attempts(self, caplog):
        """Test that retry attempts are logged as per task requirements."""
        # Arrange
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "success"
        ])
        
        # Act
        with caplog.at_level(logging.WARNING):
            result = await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        # Assert
        assert result == "success"
        
        # Verify logging contains retry information
        log_messages = [record.message for record in caplog.records]
        assert any("Retry 1/3" in msg for msg in log_messages)
        assert any("Retry 2/3" in msg for msg in log_messages)
        
        # Verify log extra fields contain structured data
        for record in caplog.records:
            if "Retry" in record.message:
                assert hasattr(record, "attempt")
                assert hasattr(record, "max_retries")
                assert hasattr(record, "delay_seconds")
