# CloudForge Bug Intelligence — What Needs to Be Completed (bedrock-integration branch)

> Current branch: `bedrock-integration`, latest commit `e5ea4ad`.
> All 345 tests passing — 0 failures, 0 errors.

---

## ✅ Recently Completed

### Fix Broken Tests (was 🔴 High Priority) — DONE

All 34 broken tests (7 failures + 21 errors + 6 from earlier) have been fixed.
See `report/completed.md` § 8 for details.

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
| ~~Fix broken tests~~ | ~~2-3 hours~~ ✅ Done |
| Deploy AWS infrastructure | 1-2 hours |
| Deploy hosting + shareable link | 30-60 min |
| Integration tests | 2-3 hours |
| Property-based tests (all 30) | 6-10 hours |
| React dashboard | 8-12 hours |
