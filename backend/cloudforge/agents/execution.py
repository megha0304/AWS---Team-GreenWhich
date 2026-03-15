"""
Execution Agent - Executes generated test cases on AWS compute infrastructure.

Routes tests to AWS Lambda (<15min, <10GB) or AWS ECS (larger tests).
Captures output and persists results to DynamoDB.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import json
import logging
import time
from typing import List, Dict, Any
from datetime import datetime
from uuid import uuid4

from cloudforge.models.state import AgentState, TestCase, TestResult
from cloudforge.models.config import SystemConfig
from cloudforge.utils.retry import retry_with_backoff

logger = logging.getLogger(__name__)


class ExecutionAgent:
    """
    Executes test cases on AWS Lambda or ECS.

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
    """

    def __init__(
        self,
        lambda_client: Any,
        ecs_client: Any,
        dynamodb_client: Any,
        config: SystemConfig,
    ):
        self.lambda_client = lambda_client
        self.ecs_client = ecs_client
        self.dynamodb_client = dynamodb_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.lambda_max_runtime = config.lambda_max_runtime_seconds
        self.lambda_max_memory = config.lambda_max_memory_mb
        self.max_retries = config.max_retries
        self.dynamodb_table = config.dynamodb_workflows_table

    async def execute_tests(self, state: AgentState) -> AgentState:
        """Execute all test cases. Main entry point."""
        self.logger.info(
            f"Starting test execution for workflow {state.workflow_id}",
            extra={"test_count": len(state.test_cases)},
        )

        if not state.test_cases:
            self.logger.warning("No test cases to execute")
            state.current_agent = "execution"
            return state

        test_results = []
        for test_case in state.test_cases:
            try:
                estimate = self._estimate_resources(test_case)
                if self._should_use_lambda(estimate):
                    result = await self._execute_on_lambda(test_case, state.workflow_id)
                else:
                    result = await self._execute_on_ecs(test_case, state.workflow_id)
                test_results.append(result)
                await self._persist_result(result, state.workflow_id)
            except Exception as e:
                self.logger.error(f"Failed to execute test {test_case.test_id}: {e}")
                state.add_error("test_execution_failed", str(e), "execution")
                continue

        state.test_results = test_results
        state.current_agent = "execution"
        passed = sum(1 for r in test_results if r.status == "passed")
        self.logger.info(f"Executed {len(test_results)} tests: {passed} passed")
        return state

    def _estimate_resources(self, test_case: TestCase) -> Dict[str, int]:
        code_lines = len(test_case.test_code.split('\n'))
        base_runtime, base_memory = 30, 512
        if code_lines > 100:
            base_runtime *= 2
            base_memory *= 21
        elif code_lines > 50:
            base_runtime = int(base_runtime * 1.5)
            base_memory = int(base_memory * 1.5)
        if test_case.test_framework in ('pytest', 'unittest'):
            base_memory = max(base_memory, 1024)
        if any(kw in test_case.test_code.lower() for kw in ('sleep', 'wait', 'timeout', 'long')):
            base_runtime *= 3
        return {"runtime_seconds": base_runtime, "memory_mb": base_memory}

    def _should_use_lambda(self, estimate: Dict[str, int]) -> bool:
        return (
            estimate["runtime_seconds"] < self.lambda_max_runtime
            and estimate["memory_mb"] < self.lambda_max_memory
        )

    async def _execute_on_lambda(self, test_case: TestCase, workflow_id: str) -> TestResult:
        """Execute test on AWS Lambda."""
        start_time = time.time()

        payload = {
            "test_id": test_case.test_id,
            "test_code": test_case.test_code,
            "test_framework": test_case.test_framework,
            "workflow_id": workflow_id,
        }

        try:
            response = self.lambda_client.invoke(
                FunctionName=f"cloudforge-test-runner-{self.config.environment}",
                InvocationType="RequestResponse",
                Payload=json.dumps(payload),
            )

            response_payload = json.loads(response["Payload"].read())
            status_code = response.get("StatusCode", 200)
            func_error = response.get("FunctionError")

            execution_time_ms = int((time.time() - start_time) * 1000)

            if func_error:
                return TestResult(
                    test_id=test_case.test_id,
                    status="error",
                    stdout=json.dumps(response_payload.get("body", "")),
                    stderr=response_payload.get("errorMessage", func_error),
                    exit_code=1,
                    execution_time_ms=execution_time_ms,
                    execution_platform="lambda",
                )

            body = response_payload if isinstance(response_payload, dict) else {}
            exit_code = body.get("exit_code", 0 if status_code == 200 else 1)
            status = "passed" if exit_code == 0 else "failed"

            return TestResult(
                test_id=test_case.test_id,
                status=status,
                stdout=body.get("stdout", str(response_payload)),
                stderr=body.get("stderr", ""),
                exit_code=exit_code,
                execution_time_ms=execution_time_ms,
                execution_platform="lambda",
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.logger.error(f"Lambda execution failed for {test_case.test_id}: {e}")
            return TestResult(
                test_id=test_case.test_id,
                status="error",
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time_ms=execution_time_ms,
                execution_platform="lambda",
            )

    async def _execute_on_ecs(self, test_case: TestCase, workflow_id: str) -> TestResult:
        """Execute test on AWS ECS."""
        start_time = time.time()

        try:
            run_response = self.ecs_client.run_task(
                cluster=f"cloudforge-{self.config.environment}",
                taskDefinition=f"cloudforge-test-runner-{self.config.environment}",
                launchType="FARGATE",
                overrides={
                    "containerOverrides": [{
                        "name": "test-runner",
                        "environment": [
                            {"name": "TEST_ID", "value": test_case.test_id},
                            {"name": "TEST_CODE", "value": test_case.test_code[:10000]},
                            {"name": "TEST_FRAMEWORK", "value": test_case.test_framework},
                            {"name": "WORKFLOW_ID", "value": workflow_id},
                        ],
                    }],
                },
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": [self.config.__dict__.get("ecs_subnet", "subnet-default")],
                        "assignPublicIp": "ENABLED",
                    }
                },
            )

            tasks = run_response.get("tasks", [])
            if not tasks:
                failures = run_response.get("failures", [])
                raise RuntimeError(f"ECS task failed to start: {failures}")

            task_arn = tasks[0]["taskArn"]

            # Wait for task completion
            waiter = self.ecs_client.get_waiter("tasks_stopped")
            waiter.wait(
                cluster=f"cloudforge-{self.config.environment}",
                tasks=[task_arn],
                WaiterConfig={"Delay": 10, "MaxAttempts": 90},
            )

            # Get task result
            desc = self.ecs_client.describe_tasks(
                cluster=f"cloudforge-{self.config.environment}",
                tasks=[task_arn],
            )
            task = desc["tasks"][0]
            container = task["containers"][0]
            exit_code = container.get("exitCode", 1)
            status = "passed" if exit_code == 0 else "failed"
            execution_time_ms = int((time.time() - start_time) * 1000)

            return TestResult(
                test_id=test_case.test_id,
                status=status,
                stdout=container.get("reason", "ECS task completed"),
                stderr="",
                exit_code=exit_code,
                execution_time_ms=execution_time_ms,
                execution_platform="ecs",
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.logger.error(f"ECS execution failed for {test_case.test_id}: {e}")
            return TestResult(
                test_id=test_case.test_id,
                status="error",
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time_ms=execution_time_ms,
                execution_platform="ecs",
            )

    async def _persist_result(self, test_result: TestResult, workflow_id: str) -> None:
        """Persist test result to DynamoDB."""
        try:
            self.dynamodb_client.put_item(
                TableName=self.dynamodb_table,
                Item={
                    "PK": {"S": f"WORKFLOW#{workflow_id}"},
                    "SK": {"S": f"TEST_RESULT#{test_result.test_id}"},
                    "test_id": {"S": test_result.test_id},
                    "status": {"S": test_result.status},
                    "stdout": {"S": test_result.stdout[:10000]},
                    "stderr": {"S": test_result.stderr[:10000]},
                    "exit_code": {"N": str(test_result.exit_code)},
                    "execution_time_ms": {"N": str(test_result.execution_time_ms)},
                    "execution_platform": {"S": test_result.execution_platform},
                    "timestamp": {"S": datetime.utcnow().isoformat()},
                },
            )
            self.logger.info(f"Persisted result for test {test_result.test_id}")
        except Exception as e:
            self.logger.error(f"Failed to persist result {test_result.test_id}: {e}")
            # Don't raise - persistence failure shouldn't block the workflow
