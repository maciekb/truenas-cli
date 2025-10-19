# TrueNAS Client Examples

This directory contains comprehensive examples demonstrating the TrueNAS Python client library with modern patterns and best practices.

## Python Examples

### 1. Basic Usage (`basic_usage.py`)

Simple introduction to using the TrueNAS client library.

**What it shows:**
- Connecting to TrueNAS with API key authentication
- Using the context manager for automatic cleanup
- Querying system information
- Listing pools and datasets
- Proper error handling

**Key features:**
- Environment variable configuration (`.env` support)
- Clean, readable code structure
- Async/await patterns

**Run it:**
```bash
export TRUENAS_HOST=truenas.local
export TRUENAS_API_KEY=your-api-key
uv run python examples/basic_usage.py
```

**Expected output:**
```
=== System Information ===
Hostname: nas.local
Uptime: 432000 seconds
System: TrueNAS SCALE

=== Pools (1) ===
  - tank: ONLINE

=== Datasets (5) ===
  - tank
  - tank/backup
  - tank/media
  - tank/home
  - tank/docs
```

---

### 2. Error Handling (`error_handling.py`)

Comprehensive error handling patterns with specific exception types and recovery strategies.

**What it shows:**
- Handling specific exception types
  - `TrueNASConnectionError` - Network failures
  - `TrueNASNotFoundError` - Resource not found
  - `TrueNASValidationError` - Input validation errors
  - `TrueNASAPIError` - Generic API errors
- Using the `@with_retry` decorator for resilient operations
- Input validation with helpful error messages
- Response validation and defensive checks

**Key features:**
- Automatic retry with exponential backoff
- Type-specific exception handling
- Graceful degradation
- Validation examples

**Run it:**
```bash
uv run python examples/error_handling.py
```

Or with API key for full tests:
```bash
export TRUENAS_API_KEY=your-key
uv run python examples/error_handling.py
```

**Output includes:**
- Validation test results (pool names, dataset paths)
- Connection error handling
- API error handling
- Retry logic demonstration
- Defensive response validation

---

### 3. Logging Configuration (`logging_example.py`)

Demonstration of structured logging with multiple verbosity levels and automatic sanitization.

**What it shows:**
- Configuring logging levels
  - `quiet=True` (ERROR level only)
  - `verbose=0` (WARNING level)
  - `verbose=1` (INFO level - recommended)
  - `verbose=2` (DEBUG level - detailed)
- File logging with persistent records
- Automatic sensitive data sanitization
  - API keys redacted
  - Passwords redacted
  - Tokens redacted
- Performance metrics in logs
- Structured logging with context

**Key features:**
- Automatic credential redaction
- Multiple output destinations (console, file)
- Per-level formatting
- Request/response tracking
- Connection timing metrics

**Run it:**
```bash
# Show different logging levels
export TRUENAS_API_KEY=your-key
uv run python examples/logging_example.py 2>&1 | less

# Direct error output to capture logs
uv run python examples/logging_example.py 2> debug.log
```

**Log output example (DEBUG level):**
```
2024-10-18 10:30:45,123 - truenas_client.client - DEBUG - Establishing WebSocket connection to wss://192.168.1.100:443/websocket
2024-10-18 10:30:45,245 - truenas_client.client - INFO - WebSocket connected (0.12s): wss://192.168.1.100:443/websocket
2024-10-18 10:30:45,256 - truenas_client.client - DEBUG - API request: method=auth.login_with_api_key id=req_1 params=['[REDACTED]']
2024-10-18 10:30:45,389 - truenas_client.client - INFO - Successfully authenticated with API key (0.23s)
```

---

## Shell Script Examples

The `scripts/` directory contains practical automation scripts.

### Daily Backup (`scripts/daily_backup.sh`)
Automated backup script for scheduled daily snapshots.

### Create Shares (`scripts/create_shares.sh`)
Batch creation of storage shares with configuration.

### Health Monitor (`scripts/health_monitor.sh`)
System health monitoring and alerting.

---

## Configuration

All examples use the `.env` file for configuration. Create one from the template:

```bash
cp config/.env.example .env
```

Edit `.env` with your settings:
```env
TRUENAS_HOST=192.168.1.100
TRUENAS_API_KEY=your-api-key-here
TRUENAS_PORT=443
TRUENAS_INSECURE=false
```

Or use environment variables:
```bash
export TRUENAS_HOST=truenas.local
export TRUENAS_API_KEY=your-api-key
python examples/basic_usage.py
```

---

## Running Examples

### Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure access:**
   ```bash
   # Option 1: Environment variables
   export TRUENAS_HOST=truenas.local
   export TRUENAS_API_KEY=your-api-key

   # Option 2: .env file
   cp config/.env.example .env
   # Edit .env with your details
   ```

3. **Verify connectivity:**
   ```bash
   python truenas-cli.py test
   ```

### Running Individual Examples

```bash
# Basic usage
python examples/basic_usage.py

# Error handling (with/without API key)
python examples/error_handling.py
export TRUENAS_API_KEY=key
python examples/error_handling.py

# Logging configuration
python examples/logging_example.py 2>&1 | head -50
```

### Running All Examples

```bash
for example in examples/*.py; do
    echo "=== Running $example ==="
    python "$example"
    echo
done
```

---

## What You'll Learn

### From `basic_usage.py`:
- ✓ Setting up the client
- ✓ Authentication patterns
- ✓ Query operations
- ✓ Context manager usage

### From `error_handling.py`:
- ✓ Exception hierarchy
- ✓ Specific error handling
- ✓ Retry patterns
- ✓ Input validation
- ✓ Defensive programming

### From `logging_example.py`:
- ✓ Configurable logging levels
- ✓ Sensitive data protection
- ✓ Performance monitoring
- ✓ Structured logging
- ✓ File logging setup

---

## Common Patterns

### Authentication
```python
async with TrueNASClient(host="truenas.local") as client:
    await client.login_with_api_key("api-key")
    # Use client
```

### Error Handling
```python
try:
    result = await client.get_pool("tank")
except TrueNASNotFoundError:
    print("Pool not found")
except TrueNASConnectionError:
    print("Connection failed")
```

### Retry Logic
```python
from truenas_client.retry import with_retry

@with_retry(max_attempts=3)
async def fetch_pools():
    return await client.get_pools()
```

### Logging
```python
from truenas_cli.logging_config import configure_logging

configure_logging(verbose=1)  # INFO level
logger.info("Starting operation")
```

---

## Troubleshooting

### "Connection refused"
- Verify TrueNAS is running and accessible
- Check hostname/IP address and port
- Ensure firewall allows WebSocket connections (port 443)

### "Authentication failed"
- Verify API key is correct
- Check if API key has expired
- Ensure user account is active

### "SSL verification failed"
- Use `TRUENAS_INSECURE=true` for self-signed certificates
- Or use `verify_ssl=False` in TrueNASClient initialization

### Credential leakage in logs
- Redaction is automatic - verify it worked
- Check that sensitive data appears as `[REDACTED]`
- Enable file logging for audit trail

---

## Next Steps

1. **Explore the CLI:**
   ```bash
   python truenas-cli.py --help
   python truenas-cli.py pool --help
   ```

2. **Read the source code:**
   - `src/truenas_client/client.py` - Main client implementation
   - `src/truenas_cli/` - CLI commands
   - `src/truenas_client/retry.py` - Retry logic

3. **Build your own scripts:**
   - Use patterns from examples
   - Start simple, add complexity
   - Test with `verbose=2` (DEBUG) first

4. **Review documentation:**
   - [Development Guide](../DEVELOPMENT.md)
   - [CLI Reference](../CLI.md)
   - [API Documentation](../DOCUMENTATION_INDEX.md)
   - [TrueNAS API Docs](https://api.truenas.com/v25.10/)

---

## Contributing

Found an issue with examples? Have a better pattern?

1. Test thoroughly
2. Follow existing style
3. Document your example
4. Submit a pull request

---

## License

MIT - See LICENSE file for details
