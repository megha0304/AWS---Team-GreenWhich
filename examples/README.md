# CloudForge Bug Intelligence Examples

This directory contains example workflows, scripts, and sample repositories for testing CloudForge Bug Intelligence.

## Contents

- `sample_repository/` - Example code repository with intentional bugs for testing
- `api_examples/` - API usage examples in multiple languages
- `workflow_scenarios/` - Common workflow scenarios and use cases
- `integration_examples/` - Integration examples with CI/CD pipelines

## Quick Start

### 1. Run Example Workflow

```bash
# Start the API
cd ../backend
python -m uvicorn cloudforge.api.main:app --reload

# In another terminal, run example workflow
cd examples/api_examples
python basic_workflow.py
```

### 2. Test with Sample Repository

```bash
# Run bug detection on sample repository
cd examples/api_examples
python scan_sample_repo.py
```

### 3. Try Different Scenarios

```bash
# Security vulnerability detection
python workflow_scenarios/security_scan.py

# Performance issue detection
python workflow_scenarios/performance_scan.py

# Code quality analysis
python workflow_scenarios/quality_scan.py
```

## Example Scenarios

### Scenario 1: Basic Bug Detection
Scan a repository for common bugs and generate fixes.

### Scenario 2: Security Vulnerability Scan
Focus on security issues (SQL injection, XSS, etc.).

### Scenario 3: Performance Analysis
Identify performance bottlenecks and optimization opportunities.

### Scenario 4: Code Quality Review
Analyze code quality, style issues, and best practices.

### Scenario 5: CI/CD Integration
Integrate bug detection into your CI/CD pipeline.

## Sample Repository

The `sample_repository/` directory contains intentional bugs for testing:

- **Null pointer dereferences**: Missing null checks
- **SQL injection**: Unsafe query construction
- **Resource leaks**: Unclosed files and connections
- **Race conditions**: Thread safety issues
- **Memory leaks**: Unreleased resources
- **Logic errors**: Incorrect algorithms

## API Examples

Examples are provided in multiple languages:

- **Python**: `api_examples/python/`
- **JavaScript/Node.js**: `api_examples/javascript/`
- **Bash**: `api_examples/bash/`
- **Go**: `api_examples/go/`

## Integration Examples

### GitHub Actions

```yaml
# .github/workflows/bug-detection.yml
name: Bug Detection
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run CloudForge Bug Detection
        run: |
          python examples/integration_examples/github_actions.py
```

### GitLab CI

```yaml
# .gitlab-ci.yml
bug-detection:
  script:
    - python examples/integration_examples/gitlab_ci.py
```

### Jenkins

```groovy
// Jenkinsfile
pipeline {
    agent any
    stages {
        stage('Bug Detection') {
            steps {
                sh 'python examples/integration_examples/jenkins.py'
            }
        }
    }
}
```

## Contributing Examples

To add a new example:

1. Create a new file in the appropriate directory
2. Add clear comments explaining the example
3. Include error handling and best practices
4. Update this README with a description
5. Test the example thoroughly

## Support

For questions about examples:
- Open a GitHub issue
- Check the main documentation in `../README.md`
- Review API documentation in `../API_DOCUMENTATION.md`
