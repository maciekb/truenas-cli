# Contributing to TrueNAS CLI

Thank you for your interest in contributing to TrueNAS CLI! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Assume good intentions

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a branch for your changes
4. Make your changes
5. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv, virtualenv, or conda)

### Initial Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/truenas-cli.git
cd truenas-cli

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Verify installation
truenas-cli --version
pytest --version
```

### Development Dependencies

The development environment includes:
- **Testing**: pytest, pytest-cov, pytest-httpx, respx
- **Linting**: ruff
- **Formatting**: black
- **Type checking**: mypy

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-watch-mode` - New features
- `fix/auth-error-handling` - Bug fixes
- `docs/improve-readme` - Documentation
- `refactor/client-module` - Code refactoring
- `test/increase-coverage` - Test improvements

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add watch mode for pool status
fix: handle SSL certificate errors correctly
docs: update installation instructions
test: add tests for filtering utilities
refactor: simplify API client error handling
```

Examples:
```
feat(completion): add dynamic pool name completion
fix(config): validate profile before saving
docs(troubleshooting): add SSL certificate section
test(client): increase API client test coverage to 95%
```

### Code Organization

```
truenas-cli/
├── src/truenas_cli/
│   ├── cli.py              # Main CLI application
│   ├── config.py           # Configuration management
│   ├── client/             # API client
│   │   ├── base.py         # HTTP client
│   │   ├── models.py       # Pydantic models
│   │   └── exceptions.py   # Custom exceptions
│   ├── commands/           # CLI commands
│   │   ├── config.py
│   │   ├── system.py
│   │   ├── pool.py
│   │   ├── dataset.py
│   │   └── share.py
│   └── utils/              # Utilities
│       ├── formatters.py
│       ├── completion.py
│       ├── filtering.py
│       ├── watch.py
│       └── batch.py
├── tests/                  # Test suite
│   ├── conftest.py         # Pytest fixtures
│   ├── test_client.py
│   ├── test_utils.py
│   └── test_commands/
└── docs/                   # Documentation
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=truenas_cli --cov-report=html

# Run specific test file
pytest tests/test_client.py

# Run specific test
pytest tests/test_client.py::test_client_initialization

# Run with verbose output
pytest -v

# Run only fast tests (skip slow tests)
pytest -m "not slow"
```

### Writing Tests

1. Place tests in the `tests/` directory
2. Name test files `test_*.py`
3. Name test functions `test_*`
4. Use descriptive test names

Example:
```python
def test_filter_expression_parses_equal_operator():
    """Test FilterExpression correctly parses = operator."""
    expr = FilterExpression("status=ONLINE")
    assert expr.field == "status"
    assert expr.op == "="
    assert expr.value == "ONLINE"
```

### Test Coverage Goals

- Aim for >80% overall coverage
- 100% coverage for critical paths (authentication, configuration)
- All new features must include tests
- Bug fixes should include regression tests

### Using Fixtures

Use pytest fixtures from `conftest.py`:

```python
def test_client_with_mock(mock_client, httpx_mock):
    """Test using pre-configured mocks."""
    response = mock_client.get("system/info")
    assert response["version"] == "TrueNAS-SCALE-24.04"
```

## Code Style

### Python Style Guide

We follow PEP 8 with these tools:

**Black** (code formatting):
```bash
# Format all code
black src/ tests/

# Check without modifying
black --check src/
```

**Ruff** (linting):
```bash
# Lint code
ruff check src/

# Auto-fix issues
ruff check --fix src/
```

**mypy** (type checking):
```bash
# Type check
mypy src/
```

### Code Style Rules

1. **Imports**: Use absolute imports, organize in three groups:
   ```python
   # Standard library
   import sys
   from pathlib import Path

   # Third-party
   import httpx
   import typer
   from rich.console import Console

   # Local
   from truenas_cli.config import Config
   ```

2. **Type hints**: Always include type hints
   ```python
   def process_items(items: List[Dict[str, Any]], limit: int = 10) -> List[str]:
       ...
   ```

3. **Docstrings**: Use Google-style docstrings
   ```python
   def validate_config(config: Config) -> bool:
       """Validate configuration structure.

       Args:
           config: Configuration object to validate

       Returns:
           True if valid, False otherwise

       Raises:
           ConfigurationError: If configuration is invalid
       """
   ```

4. **Error handling**: Use custom exceptions
   ```python
   if not api_key:
       raise ConfigurationError("API key is required")
   ```

5. **Logging**: Use appropriate log levels
   ```python
   logger.debug(f"Connecting to {url}")
   logger.info("Connection successful")
   logger.warning("Using self-signed certificate")
   logger.error(f"Authentication failed: {error}")
   ```

## Submitting Changes

### Pull Request Process

1. **Update your fork**:
   ```bash
   git remote add upstream https://github.com/original/truenas-cli.git
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "feat: add your feature"
   ```

4. **Run quality checks**:
   ```bash
   # Format code
   black src/ tests/

   # Lint
   ruff check src/

   # Type check
   mypy src/

   # Run tests
   pytest

   # Check coverage
   pytest --cov=truenas_cli
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request** on GitHub

### Pull Request Guidelines

- Title should follow conventional commits format
- Description should explain:
  - What changes were made
  - Why they were necessary
  - How to test them
- Link related issues
- Ensure all CI checks pass
- Request review from maintainers

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Type hints included
- [ ] Docstrings added/updated
- [ ] No linting errors
- [ ] Test coverage maintained or improved

## Reporting Bugs

### Before Reporting

1. Check existing issues
2. Verify bug on latest version
3. Collect diagnostic information:
   ```bash
   truenas-cli --version
   truenas-cli config doctor
   truenas-cli -vvv --log-file debug.log <command>
   ```

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. See error

**Expected Behavior**
What you expected to happen

**Actual Behavior**
What actually happened

**Environment**
- truenas-cli version: [version]
- Python version: [version]
- OS: [e.g., Ubuntu 22.04]
- TrueNAS version: [if applicable]

**Logs**
```
Paste relevant logs here
```

**Additional Context**
Any other relevant information
```

## Feature Requests

### Before Requesting

- Check if feature already exists
- Search existing feature requests
- Consider if feature fits project scope

### Feature Request Template

```markdown
**Feature Description**
Clear description of proposed feature

**Use Case**
Why is this feature needed?
How would it be used?

**Proposed Solution**
How should this feature work?

**Alternatives Considered**
Other approaches you considered

**Additional Context**
Screenshots, examples, references
```

## Development Tips

### Testing Changes Quickly

```bash
# Install in development mode
pip install -e .

# Your changes take effect immediately
truenas-cli system info
```

### Debugging

```bash
# Enable verbose logging
truenas-cli -vvv system info

# Write logs to file
truenas-cli --log-file debug.log -vv pool list

# Use Python debugger
python -m pdb -m truenas_cli system info
```

### Working with Tests

```bash
# Watch mode for tests
pytest-watch

# Run tests on file change
while true; do
  clear
  pytest tests/test_client.py
  sleep 2
done
```

## Getting Help

- Open an issue for questions
- Join community discussions
- Check documentation in `docs/`
- Read troubleshooting guide

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

Thank you for contributing to TrueNAS CLI!
