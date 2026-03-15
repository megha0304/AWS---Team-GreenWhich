# CloudForge Bug Intelligence — What Needs to Be Completed (bedrock-integration branch)

> Current branch: `bedrock-integration`, commit `e0c17cb`.

---

## 🔴 High Priority — Fix Broken Tests

The Bedrock integration changed agent interfaces. 34 tests need updating:

### test_analysis.py (6 failures)

| Test | Issue |
|------|-------|
| `TestMockCauseGeneration` (3 tests) | Calls `_generate_mock_cause()` — method removed |
| `TestConfidenceEstimation` (3 tests) | Calls `_estimate_mock_confidence()` — method removed |

**Fix:** Remove these test classes or rewrite them to test `_analyze_failure()` with a mocked Bedrock response.

### test_execution.py (2 failures)

| Test | Issue |
|------|-------|
| `TestLambdaExecution::test_execute_on_lambda_placeholder` | Expects old placeholder behavior, now calls real `lambda_client.invoke()` |
| `TestECSExecution::test_execute_on_ecs_placeholder` | Expects old placeholder behavior, now calls real `ecs_client.run_task()` |

**Fix:** Mock `lambda_client.invoke()` and `ecs_client.run_task()` return values. The mock config also needs `environment` attribute.

### test_resolution.py (2 failures)

| Test | Issue |
|------|-------|
| `TestFixGeneration::test_generate_fix_description` | Expects old `_generate_fix_description()` method |
| `TestFixGeneration::test_generate_code_diff_format` | Expects old `_generate_code_diff()` method |

**Fix:** Update to test `_generate_fix()` with mocked Bedrock response, or test the static helper methods.

### test_test_architect.py (1 failure + 21 errors)

| Test | Issue |
|------|-------|
| `TestTestArchitectAgentInitialization` (1 fail) | Fixture creates agent with old constructor signature |
| All other tests (21 errors) | Setup fixture fails — agent constructor changed |

**Fix:** Update the `agent` fixture to pass `model_id` via config mock. The `q_developer_client` is now a bedrock-runtime client.

### test_retry.py (2 failures)

| Test | Issue |
|------|-------|
| `TestEdgeCases::test_zero_retries` | Edge case with 0 retries |
| `TestRequirementValidation::test_configurable_base_delay` | Delay assertion mismatch |

**Fix:** Check if retry behavior changed or if these are pre-existing issues.

---

## 🟡 Medium Priority — Remaining Development

### AWS Infrastructure Deployment
- CDK stacks written but never deployed
- DynamoDB tables, S3 buckets, Lambda functions, ECS cluster need provisioning
- Run: `cd infrastructure && cdk deploy --all`

### Hosting / Shareable Link
- No live deployment exists
- Deploy to Render.com, Railway, or AWS directly

### LocalStack Local Dev (Task 21.3)
- `docker-compose.yml` exists but LocalStack not fully configured

### End-to-End Integration Tests (Task 21.4)
- No integration tests exist yet

### CDK Infrastructure Tests (Task 18.5)
- Only a smoke test exists — needs real assertions

---

## 🟠 Optional — Property-Based Tests

~30 property-based tests marked `*` in tasks.md are not implemented. These are optional for MVP:

Tasks: 2.2, 2.3, 3.2, 3.3, 4.2-4.4, 5.3-5.4, 7.5, 8.2-8.4, 9.2-9.4, 10.2-10.4, 11.2-11.4, 13.2-13.4, 14.4-14.5, 15.4-15.6, 16.2, 18.5, 20.2

---

## 🟠 Optional — React Web Dashboard (Task 19)

The spec called for React + TypeScript. Flask was built instead. If React is required:
- Tasks 19.1 through 19.6 are entirely not done
- Estimated effort: 8-12 hours

---

## Effort Estimates

| Scope | Time |
|-------|------|
| Fix broken tests (high priority) | 2-3 hours |
| Deploy AWS infrastructure | 1-2 hours |
| Deploy hosting + shareable link | 30-60 min |
| Integration tests | 2-3 hours |
| Property-based tests (all 30) | 6-10 hours |
| React dashboard | 8-12 hours |
