# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrueNAS CLI is a Python-based command-line interface for managing TrueNAS SCALE appliances through the REST API. It's built with Typer for CLI structure, httpx for API calls, Pydantic for data validation, and Rich for terminal output.

**Target Python version:** 3.10+

## Development Commands

### Installation and Setup

```bash
# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install without dev dependencies
pip install -e .
```

### Running Tests

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_client.py

# Run specific test function
pytest tests/test_client.py::test_client_initialization

# Run tests without coverage report
pytest --no-cov

# Run with verbose output
pytest -v

# Run only unit tests (skip integration)
pytest -m unit

# Run excluding slow tests
pytest -m "not slow"
```

### Code Quality

```bash
# Format code (automatically fixes issues)
black src/ tests/

# Lint code (check for issues)
ruff check src/

# Lint with auto-fix
ruff check --fix src/

# Type check (strict mode enabled)
mypy src/

# Run all quality checks
black src/ tests/ && ruff check src/ && mypy src/ && pytest
```

### Running the CLI

```bash
# Run from source (after pip install -e .)
truenas-cli --help

# Run as Python module
python -m truenas_cli --help

# Initialize configuration
truenas-cli config init

# Test with verbose logging
truenas-cli -vvv --log-file debug.log system info
```

## Architecture Overview

### Three-Layer Architecture

1. **CLI Layer** (`src/truenas_cli/commands/`)
   - Typer-based command definitions
   - User input validation and formatting
   - Global context (profile, output format, verbosity) passed via `ctx.obj`

2. **API Client Layer** (`src/truenas_cli/client/`)
   - `base.py`: HTTP client with retry logic and error handling
   - `models.py`: Pydantic models for type-safe API responses
   - `exceptions.py`: Exception hierarchy (TrueNASError → AuthenticationError, APIError, etc.)

3. **Configuration Layer** (`src/truenas_cli/config.py`)
   - Multi-profile support stored in `~/.truenas-cli/config.json`
   - Secure file permissions (600) enforced automatically
   - Pydantic-validated configuration with environment variable overrides

### Key Design Patterns

**Global Context Flow:**
```
cli.py:main_callback() creates CLIContext
    → stored in ctx.obj
    → passed to all subcommands
    → contains: profile, output_format, verbose, quiet, timing, log_file
```

**API Client Initialization:**
```
Command reads profile from CLIContext
    → loads Config from ~/.truenas-cli/config.json
    → creates TrueNASClient with ProfileConfig
    → client auto-handles retries, auth headers, SSL verification
```

**Output Formatting:**
```
All list/info commands use utils/formatters.py
    → format_output(data, format, columns)
    → Supports: table (Rich), json, yaml, plain (TSV)
    → Color coding: green=healthy, yellow=warning, red=error
```

**Error Handling:**
```
Custom exceptions in client/exceptions.py:
    TrueNASError (base)
        ├── AuthenticationError (401) → exit code 2
        ├── ConfigurationError → exit code 3
        ├── APIError (4xx/5xx) → exit code 1
        └── NetworkError → exit code 1

cli.py:main() catches and formats these with helpful tips
```

### Command Structure Pattern

All commands follow this pattern (see `commands/pool.py` as reference):

```python
from truenas_cli.client.base import TrueNASClient
from truenas_cli.config import load_config
from truenas_cli.utils.formatters import format_output

@app.command()
def list_items(
    ctx: typer.Context,
    # Command-specific options
):
    """Command description with examples in docstring."""
    # 1. Get context
    cli_ctx = ctx.obj

    # 2. Load config and create client
    config = load_config()
    profile = config.get_profile(cli_ctx.profile or config.active_profile)
    client = TrueNASClient(profile, verbose=cli_ctx.verbose > 0)

    # 3. Make API call
    items = client.get_items()

    # 4. Format and output
    format_output(items, cli_ctx.output_format, columns)
```

### TrueNAS API Client

**Base URL handling:**
- All endpoints are normalized to `/api/v2.0/{endpoint}`
- Client auto-prepends `/api/v2.0/` if missing
- Example: `client.get("pool")` → `GET {base_url}/api/v2.0/pool`

**Retry Logic:**
- Exponential backoff: 1s, 2s, 4s (3 retries default)
- Retries on: network errors, 5xx responses, rate limits (429)
- No retry on: 4xx client errors (except 429)

**Authentication:**
- Uses Bearer token: `Authorization: Bearer {api_key}`
- API key stored securely in config with 600 permissions
- Auth failures raise `AuthenticationError` with actionable messages

### Advanced Features

**Watch Mode** (`utils/watch.py`):
- Uses Rich Live display for flicker-free updates
- Refreshes command output at specified interval
- Any list/status command can add `--watch --interval N`

**Filtering** (`utils/filtering.py`):
- Query syntax: `field=value`, `field!=value`, `field>value`, `field~value` (contains)
- Supports nested fields: `topology.status=ONLINE`
- Multiple filters use AND logic
- Applied to list commands via `--filter` flag

**Shell Completion** (`utils/completion.py`):
- Dynamic completion for pool names, dataset paths
- Fetches values from API when possible
- Install with `truenas-cli completion install [bash|zsh|fish]`

## Important Conventions

### API Method Naming

API client methods follow this pattern:
- `get_{resource}()` - Get single resource
- `list_{resources}()` - List all resources
- `create_{resource}()` - Create new resource
- `update_{resource}()` - Update existing resource
- `delete_{resource}()` - Delete resource

### Pydantic Models

All API responses are validated through Pydantic models in `client/models.py`:
- Use `Optional[]` for nullable fields
- Use `Field()` for field descriptions and validation
- Models auto-convert API response to typed objects

### Exit Codes

Consistent exit codes defined in `cli.py:main()`:
- `0` - Success
- `1` - General error (APIError, NetworkError)
- `2` - Authentication error
- `3` - Configuration error
- `130` - User cancelled (Ctrl+C)

### Logging Levels

Controlled by `-v` flags:
- Default (no flag): WARNING level
- `-v`: INFO level
- `-vv`: DEBUG level
- `-vvv`: DEBUG with maximum detail (shows request/response)
- `--quiet`: ERROR level only

### Environment Variables

Recognized environment variables:
- `TRUENAS_URL` - Override profile URL
- `TRUENAS_API_KEY` - Override profile API key
- `TRUENAS_PROFILE` - Set active profile
- `TRUENAS_CONFIG_DIR` - Custom config directory
- `TRUENAS_OUTPUT_FORMAT` - Default output format

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_client.py           # API client tests
├── test_utils.py            # Utility function tests
└── test_commands/           # Command tests (if added)
    ├── test_system.py
    ├── test_pool.py
    └── test_dataset.py
```

### Key Fixtures (conftest.py)

- `mock_config_dir()` - Temporary config directory
- `mock_config()` - Pre-configured Config object
- `mock_client()` - TrueNASClient with mocked responses
- `httpx_mock` - pytest-httpx for HTTP mocking
- `mock_*_response()` - Sample API responses for each resource type

### Mocking API Calls

Use `httpx_mock` fixture (from pytest-httpx):

```python
def test_get_pools(mock_client, httpx_mock):
    httpx_mock.add_response(
        url="https://truenas.local/api/v2.0/pool",
        json=[{"name": "tank", "status": "ONLINE"}]
    )
    pools = mock_client.list_pools()
    assert len(pools) == 1
```

## Common Development Patterns

### Adding a New Command

1. Create command in `commands/{category}.py`
2. Add corresponding API method to `client/base.py`
3. Create Pydantic model in `client/models.py` if new resource
4. Register command group in `cli.py` with `app.add_typer()`
5. Add tests in `tests/test_commands/test_{category}.py`
6. Update README.md with usage examples

### Adding a New API Endpoint

1. Add method to `TrueNASClient` in `client/base.py`:
   ```python
   def get_resource(self, resource_id: int) -> Dict[str, Any]:
       """Get resource by ID."""
       return self.get(f"resource/{resource_id}")
   ```

2. Create Pydantic model in `client/models.py`:
   ```python
   class Resource(BaseModel):
       id: int
       name: str
       status: str
   ```

3. Update method to return typed model:
   ```python
   def get_resource(self, resource_id: int) -> Resource:
       data = self.get(f"resource/{resource_id}")
       return Resource(**data)
   ```

### Extending Output Formatters

All formatters in `utils/formatters.py` accept:
- `data`: List or dict of items
- `output_format`: "table", "json", "yaml", "plain"
- `columns`: Optional list of column names to display

For custom formatting needs, extend `format_output()` function.

## Code Style Configuration

All settings in `pyproject.toml`:

- **Black**: Line length 100, Python 3.10+ target
- **Ruff**: PEP 8 + pyflakes + bugbear + comprehensions + pyupgrade
- **mypy**: Strict mode enabled, all functions require type hints
  - Exception: Tests can omit type hints (configured in `[[tool.mypy.overrides]]`)

## API Endpoint Reference

TrueNAS SCALE API base: `/api/v2.0/`

**Implemented endpoints:**
- `GET /system/info` - System information
- `GET /system/version` - TrueNAS version
- `GET /system/state` - System state
- `GET /pool` - List pools
- `GET /pool/id/{id}` - Pool details
- `GET /pool/dataset` - List datasets
- `POST /pool/dataset` - Create dataset
- `DELETE /pool/dataset/id/{id}` - Delete dataset
- `GET /sharing/nfs` - List NFS shares
- `GET /sharing/smb` - List SMB shares
- `POST /sharing/nfs` - Create NFS share
- `POST /sharing/smb` - Create SMB share

All endpoints require `Authorization: Bearer {api_key}` header.
