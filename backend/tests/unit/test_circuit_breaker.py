"""
Unit tests for CircuitBreaker class.

Tests the circuit breaker pattern implementation for preventing cascading
failures by opening the circuit after repeated failures.

Requirements: 11.5
"""

import asyncio
import logging
import time
import pytest
from unittest.mock import AsyncMock, Mock, patch

from cloudforge.utils.retry import CircuitBreaker, CircuitBreakerOpenError


class TestCircuitBreakerBasics:
    """Test basic circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_successful_call_in_closed_state(self):
        """Test that successful calls pass through when circuit is closed."""
        # Arrange
        breaker = CircuitBreaker("test-service")
        mock_func = AsyncMock(return_value="success")
        
        # Act
        result = await breaker.call(mock_func)
        
        # Assert
        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
        mock_func.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_single_failure_keeps_circuit_closed(self):
        """Test that a single failure doesn't open the circuit."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=5)
        mock_func = AsyncMock(side_effect=Exception("Transient error"))
        
        # Act & Assert
        with pytest.raises(Exception):
            await breaker.call(mock_func)
        
        assert breaker.state == "closed"
        assert breaker.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_failures(self):
        """Test that circuit opens after reaching failure threshold."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=5, time_window_seconds=60)
        mock_func = AsyncMock(side_effect=Exception("Service unavailable"))
        
        # Act - Trigger 5 failures
        for _ in range(5):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Assert
        assert breaker.state == "open"
        assert breaker.failure_count == 5
        assert breaker.opened_at is not None
    
    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self):
        """Test that open circuit rejects calls immediately."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=3)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        assert breaker.state == "open"
        
        # Act & Assert - Next call should be rejected
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await breaker.call(mock_func)
        
        assert "Circuit breaker is open" in str(exc_info.value)
        assert exc_info.value.service_name == "test-service"
    
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(self):
        """Test that circuit transitions to half-open after timeout."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=3, timeout_seconds=1)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        assert breaker.state == "open"
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Act - Next call should transition to half-open
        mock_func.side_effect = None
        mock_func.return_value = "success"
        result = await breaker.call(mock_func)
        
        # Assert
        assert result == "success"
        assert breaker.state == "closed"
    
    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self):
        """Test that successful call in half-open state closes circuit."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=2, timeout_seconds=0.5)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Wait for timeout to enter half-open
        await asyncio.sleep(0.6)
        
        # Act - Successful call in half-open
        mock_func.side_effect = None
        mock_func.return_value = "recovered"
        result = await breaker.call(mock_func)
        
        # Assert
        assert result == "recovered"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self):
        """Test that failed call in half-open state reopens circuit."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=2, timeout_seconds=0.5)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Wait for timeout to enter half-open
        await asyncio.sleep(0.6)
        
        # Act - Failed call in half-open
        with pytest.raises(Exception):
            await breaker.call(mock_func)
        
        # Assert
        assert breaker.state == "open"


class TestCircuitBreakerSync:
    """Test synchronous circuit breaker functionality."""
    
    def test_sync_successful_call(self):
        """Test that synchronous successful calls work."""
        # Arrange
        breaker = CircuitBreaker("test-service")
        mock_func = Mock(return_value="success")
        
        # Act
        result = breaker.call_sync(mock_func)
        
        # Assert
        assert result == "success"
        assert breaker.state == "closed"
    
    def test_sync_circuit_opens_after_failures(self):
        """Test that synchronous circuit opens after failures."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=3)
        mock_func = Mock(side_effect=Exception("Error"))
        
        # Act
        for _ in range(3):
            with pytest.raises(Exception):
                breaker.call_sync(mock_func)
        
        # Assert
        assert breaker.state == "open"
    
    def test_sync_open_circuit_rejects_calls(self):
        """Test that synchronous open circuit rejects calls."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=2)
        mock_func = Mock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call_sync(mock_func)
        
        # Act & Assert
        with pytest.raises(CircuitBreakerOpenError):
            breaker.call_sync(mock_func)


class TestCircuitBreakerTimeWindow:
    """Test time window functionality for failure counting."""
    
    @pytest.mark.asyncio
    async def test_old_failures_are_cleaned(self):
        """Test that failures outside time window are not counted."""
        # Arrange
        breaker = CircuitBreaker(
            "test-service",
            failure_threshold=5,
            time_window_seconds=2
        )
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act - Trigger 3 failures
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        assert breaker.state == "closed"
        assert len(breaker.failure_timestamps) == 3
        
        # Wait for time window to expire
        await asyncio.sleep(2.1)
        
        # Trigger 2 more failures (should not open circuit)
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Assert - Circuit should still be closed because old failures expired
        assert breaker.state == "closed"
        assert len(breaker.failure_timestamps) == 2
    
    @pytest.mark.asyncio
    async def test_failures_within_window_open_circuit(self):
        """Test that failures within time window open circuit."""
        # Arrange
        breaker = CircuitBreaker(
            "test-service",
            failure_threshold=5,
            time_window_seconds=10
        )
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act - Trigger 5 failures quickly
        for _ in range(5):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
            await asyncio.sleep(0.1)  # Small delay but within window
        
        # Assert
        assert breaker.state == "open"


class TestCircuitBreakerConfiguration:
    """Test circuit breaker configuration options."""
    
    def test_custom_failure_threshold(self):
        """Test that custom failure threshold is respected."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=10)
        
        # Assert
        assert breaker.failure_threshold == 10
    
    def test_custom_timeout(self):
        """Test that custom timeout is respected."""
        # Arrange
        breaker = CircuitBreaker("test-service", timeout_seconds=60)
        
        # Assert
        assert breaker.timeout_seconds == 60
    
    def test_custom_time_window(self):
        """Test that custom time window is respected."""
        # Arrange
        breaker = CircuitBreaker("test-service", time_window_seconds=120)
        
        # Assert
        assert breaker.time_window_seconds == 120
    
    def test_service_name_stored(self):
        """Test that service name is stored correctly."""
        # Arrange
        breaker = CircuitBreaker("my-api-service")
        
        # Assert
        assert breaker.service_name == "my-api-service"


class TestCircuitBreakerState:
    """Test circuit breaker state management."""
    
    def test_get_state_closed(self):
        """Test get_state returns correct info for closed circuit."""
        # Arrange
        breaker = CircuitBreaker("test-service")
        
        # Act
        state = breaker.get_state()
        
        # Assert
        assert state["service_name"] == "test-service"
        assert state["state"] == "closed"
        assert state["failure_count"] == 0
        assert state["opened_at"] is None
    
    @pytest.mark.asyncio
    async def test_get_state_open(self):
        """Test get_state returns correct info for open circuit."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=2, timeout_seconds=30)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Act
        state = breaker.get_state()
        
        # Assert
        assert state["state"] == "open"
        assert state["failure_count"] == 2
        assert state["opened_at"] is not None
        assert state["time_until_half_open"] is not None
        assert state["time_until_half_open"] <= 30
    
    def test_record_success_resets_failure_count(self):
        """Test that record_success resets failure count in half-open state."""
        # Arrange
        breaker = CircuitBreaker("test-service")
        breaker.state = "half_open"
        breaker.failure_count = 3
        breaker.failure_timestamps = [time.time()] * 3
        
        # Act
        breaker.record_success()
        
        # Assert
        assert breaker.state == "closed"
        assert breaker.failure_count == 0
        assert len(breaker.failure_timestamps) == 0
    
    def test_record_failure_increments_count(self):
        """Test that record_failure increments failure count."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=10)
        
        # Act
        breaker.record_failure()
        
        # Assert
        assert breaker.failure_count == 1
        assert len(breaker.failure_timestamps) == 1
        assert breaker.last_failure_time is not None


class TestCircuitBreakerLogging:
    """Test circuit breaker logging behavior."""
    
    @pytest.mark.asyncio
    async def test_logs_circuit_opening(self, caplog):
        """Test that circuit opening is logged."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=3)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act
        with caplog.at_level(logging.ERROR):
            for _ in range(3):
                with pytest.raises(Exception):
                    await breaker.call(mock_func)
        
        # Assert
        assert any("Circuit breaker opened" in record.message for record in caplog.records)
        assert any("test-service" in record.message for record in caplog.records)
    
    @pytest.mark.asyncio
    async def test_logs_half_open_transition(self, caplog):
        """Test that transition to half-open is logged."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=2, timeout_seconds=0.5)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Wait for timeout
        await asyncio.sleep(0.6)
        
        # Act
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        with caplog.at_level(logging.INFO):
            await breaker.call(mock_func)
        
        # Assert
        assert any("half-open" in record.message for record in caplog.records)
    
    @pytest.mark.asyncio
    async def test_logs_circuit_closing(self, caplog):
        """Test that circuit closing is logged."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=2, timeout_seconds=0.5)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Wait and recover
        await asyncio.sleep(0.6)
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        # Act
        with caplog.at_level(logging.INFO):
            await breaker.call(mock_func)
        
        # Assert
        assert any("closing" in record.message for record in caplog.records)


class TestCircuitBreakerWithArguments:
    """Test circuit breaker with function arguments."""
    
    @pytest.mark.asyncio
    async def test_passes_args_to_function(self):
        """Test that arguments are passed correctly to wrapped function."""
        # Arrange
        breaker = CircuitBreaker("test-service")
        mock_func = AsyncMock(return_value="result")
        
        # Act
        result = await breaker.call(mock_func, "arg1", "arg2")
        
        # Assert
        assert result == "result"
        mock_func.assert_called_once_with("arg1", "arg2")
    
    @pytest.mark.asyncio
    async def test_passes_kwargs_to_function(self):
        """Test that keyword arguments are passed correctly."""
        # Arrange
        breaker = CircuitBreaker("test-service")
        mock_func = AsyncMock(return_value="result")
        
        # Act
        result = await breaker.call(mock_func, key1="value1", key2="value2")
        
        # Assert
        assert result == "result"
        mock_func.assert_called_once_with(key1="value1", key2="value2")
    
    @pytest.mark.asyncio
    async def test_passes_mixed_args_and_kwargs(self):
        """Test that mixed args and kwargs are passed correctly."""
        # Arrange
        breaker = CircuitBreaker("test-service")
        mock_func = AsyncMock(return_value="result")
        
        # Act
        result = await breaker.call(mock_func, "arg1", key1="value1")
        
        # Assert
        assert result == "result"
        mock_func.assert_called_once_with("arg1", key1="value1")


class TestRequirementValidation:
    """Test that implementation meets specific requirements."""
    
    @pytest.mark.asyncio
    async def test_requirement_11_5_circuit_breaker_activation(self):
        """
        Requirement 11.5: THE System SHALL implement circuit breakers for 
        frequently failing services.
        
        Property 52: For any external service that fails more than 5 times 
        in a 1-minute window, the System should open a circuit breaker.
        """
        # Arrange
        breaker = CircuitBreaker(
            "external-api",
            failure_threshold=5,
            time_window_seconds=60,
            timeout_seconds=30
        )
        mock_api_call = AsyncMock(side_effect=Exception("Service unavailable"))
        
        # Act - Trigger 5 failures within 1 minute
        for i in range(5):
            with pytest.raises(Exception):
                await breaker.call(mock_api_call)
            if i < 4:
                await asyncio.sleep(0.1)  # Small delay between calls
        
        # Assert - Circuit should be open
        assert breaker.state == "open"
        
        # Verify subsequent calls are rejected
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(mock_api_call)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_timeout_30_seconds(self):
        """Test that circuit breaker uses 30 second timeout as per requirement."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=3, timeout_seconds=30)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Assert
        assert breaker.timeout_seconds == 30
        assert breaker.state == "open"
        
        # Verify timeout is enforced
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            await breaker.call(mock_func)
        
        assert exc_info.value.timeout_remaining <= 30
    
    @pytest.mark.asyncio
    async def test_metrics_publishing_on_state_change(self, caplog):
        """Test that metrics are published when circuit state changes."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=2)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act
        with caplog.at_level(logging.DEBUG):
            for _ in range(2):
                with pytest.raises(Exception):
                    await breaker.call(mock_func)
        
        # Assert - Verify metric publishing was attempted
        assert any("Publishing circuit breaker state metric" in record.message 
                  for record in caplog.records)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_exactly_threshold_failures_opens_circuit(self):
        """Test that exactly threshold failures opens circuit."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=5)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act - Exactly 5 failures
        for _ in range(5):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Assert
        assert breaker.state == "open"
    
    @pytest.mark.asyncio
    async def test_threshold_minus_one_keeps_closed(self):
        """Test that threshold-1 failures keeps circuit closed."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=5)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act - 4 failures (threshold - 1)
        for _ in range(4):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Assert
        assert breaker.state == "closed"
    
    @pytest.mark.asyncio
    async def test_zero_timeout_immediate_half_open(self):
        """Test that zero timeout allows immediate half-open transition."""
        # Arrange
        breaker = CircuitBreaker("test-service", failure_threshold=2, timeout_seconds=0)
        mock_func = AsyncMock(side_effect=Exception("Error"))
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(mock_func)
        
        # Act - Immediate retry should enter half-open
        mock_func.side_effect = None
        mock_func.return_value = "success"
        result = await breaker.call(mock_func)
        
        # Assert
        assert result == "success"
        assert breaker.state == "closed"
