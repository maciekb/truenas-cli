# Troubleshooting Guide

This guide helps diagnose and fix common issues with truenas-cli.

## Table of Contents

- [Configuration Issues](#configuration-issues)
- [Connection Problems](#connection-problems)
- [Authentication Errors](#authentication-errors)
- [SSL Certificate Issues](#ssl-certificate-issues)
- [Command Execution Problems](#command-execution-problems)
- [Performance Issues](#performance-issues)
- [Getting Help](#getting-help)

## Configuration Issues

### Problem: Configuration file not found

**Symptom:**
```
Configuration Error: No configuration file found
```

**Solution:**
Run the configuration initialization wizard:
```bash
truenas-cli config init
```

This will create a new configuration file at `~/.truenas-cli/config.json`.

### Problem: Invalid JSON in configuration file

**Symptom:**
```
Configuration Error: Configuration file is invalid: ...
```

**Solutions:**
1. Validate the configuration:
   ```bash
   truenas-cli config validate
   ```

2. Check for syntax errors in `~/.truenas-cli/config.json`

3. If corrupted, backup and recreate:
   ```bash
   cp ~/.truenas-cli/config.json ~/.truenas-cli/config.json.backup
   truenas-cli config init
   ```

### Problem: Wrong profile is active

**Symptom:**
Commands connect to the wrong TrueNAS instance.

**Solutions:**
1. Check active profile:
   ```bash
   truenas-cli config list
   ```

2. Switch profiles:
   ```bash
   truenas-cli config set-profile <profile-name>
   ```

3. Or use `--profile` flag for one-time use:
   ```bash
   truenas-cli --profile production system info
   ```

## Connection Problems

### Problem: Cannot connect to TrueNAS

**Symptom:**
```
Network Error: Connection refused
```

**Diagnostic steps:**
1. Verify TrueNAS is accessible:
   ```bash
   ping <truenas-ip>
   curl https://<truenas-url>
   ```

2. Check configuration:
   ```bash
   truenas-cli config show
   ```

3. Test connection:
   ```bash
   truenas-cli config test
   ```

4. Run full diagnostic:
   ```bash
   truenas-cli config doctor
   ```

**Common fixes:**
- Ensure TrueNAS is powered on and connected to network
- Verify firewall allows connections on port 443
- Check URL is correct in configuration
- Ensure no VPN or proxy is interfering

### Problem: Timeout errors

**Symptom:**
```
Network Error: Request timeout
```

**Solutions:**
1. Increase timeout in configuration:
   ```bash
   truenas-cli config init --timeout 60
   ```

2. Check network latency:
   ```bash
   ping -c 5 <truenas-url>
   ```

3. Use `--timing` flag to measure operation duration:
   ```bash
   truenas-cli --timing pool list
   ```

## Authentication Errors

### Problem: API key rejected

**Symptom:**
```
Authentication Error: Invalid API key
```

**Solutions:**
1. Verify API key in configuration:
   ```bash
   truenas-cli config show
   ```

2. Generate new API key in TrueNAS:
   - Log in to TrueNAS web interface
   - Navigate to user menu → API Keys
   - Create new API key
   - Update configuration:
     ```bash
     truenas-cli config init
     ```

3. Check API key hasn't been revoked in TrueNAS

### Problem: Permission denied

**Symptom:**
```
TrueNAS Error: Permission denied
```

**Solution:**
Ensure the API key belongs to a user with appropriate permissions in TrueNAS:
- Administrative access for pool/dataset operations
- Read-only access sufficient for viewing information

## SSL Certificate Issues

### Problem: SSL verification failed

**Symptom:**
```
SSL Error: Certificate verify failed
```

**Solutions (in order of preference):**

1. **Recommended**: Add TrueNAS certificate to system trust store
   - Export certificate from TrueNAS web interface
   - Install in system certificate store

2. **For testing only**: Disable SSL verification
   ```bash
   truenas-cli config init --no-verify-ssl
   ```

   **Warning**: This reduces security and should only be used for testing.

3. Use `HTTPS_PROXY` for corporate environments:
   ```bash
   export HTTPS_PROXY=http://proxy.example.com:8080
   ```

### Problem: Self-signed certificate not trusted

**Symptom:**
```
SSL Error: self signed certificate
```

**Solution for development:**
```bash
truenas-cli config init --no-verify-ssl
```

**Production solution:**
Install a proper SSL certificate on TrueNAS or add self-signed cert to trust store.

## Command Execution Problems

### Problem: Command hangs or is slow

**Diagnostic:**
```bash
truenas-cli --timing -vv pool list
```

**Solutions:**
- Check network connectivity
- Increase timeout if needed
- Check TrueNAS system resources
- Try simpler commands first to isolate issue

### Problem: Unexpected output format

**Solution:**
Specify output format explicitly:
```bash
truenas-cli --output-format json pool list
truenas-cli --output-format table system info
```

### Problem: Watch mode not refreshing

**Diagnostic:**
Check terminal supports ANSI codes and has sufficient size.

**Solution:**
- Ensure terminal is not redirected
- Try different interval:
  ```bash
  truenas-cli pool status tank --watch --interval 5
  ```

## Performance Issues

### Problem: Slow command execution

**Diagnostic steps:**
1. Measure baseline:
   ```bash
   truenas-cli --timing system info
   ```

2. Enable debug logging:
   ```bash
   truenas-cli -vvv --log-file debug.log pool list
   ```

3. Check log file for bottlenecks

**Common causes:**
- Network latency
- Large dataset lists
- TrueNAS system under load

**Solutions:**
- Filter results to reduce data transfer
- Use `--quiet` mode for automation
- Consider caching frequently accessed data

### Problem: Batch operations taking too long

**Solution:**
Enable parallel execution:
```bash
truenas-cli batch --parallel --workers 10 operations.yaml
```

## Shell Completion Not Working

### Problem: Tab completion doesn't work

**Diagnostic:**
Check if completion is installed:
```bash
# For bash
ls ~/.bash_completion.d/truenas-cli

# For zsh
ls ~/.zfunc/_truenas-cli

# For fish
ls ~/.config/fish/completions/truenas-cli.fish
```

**Solution:**
Reinstall completion:
```bash
truenas-cli completion install
```

Then restart your shell:
```bash
# For bash
source ~/.bashrc

# For zsh
source ~/.zshrc

# For fish
fish_update_completions
```

## Common Error Messages

### "ModuleNotFoundError: No module named 'truenas_cli'"

**Cause**: Package not installed or virtual environment not activated

**Solution:**
```bash
# Install package
pip install -e .

# Or activate venv
source venv/bin/activate
```

### "PermissionError: [Errno 13] Permission denied: '~/.truenas-cli/config.json'"

**Cause**: Incorrect file permissions

**Solution:**
```bash
chmod 600 ~/.truenas-cli/config.json
chmod 700 ~/.truenas-cli
```

### "ValueError: Invalid output format"

**Cause**: Unsupported output format specified

**Solution:**
Use one of: `table`, `json`, `yaml`, `plain`
```bash
truenas-cli --output-format json pool list
```

## Getting Help

### Enable Verbose Logging

For detailed debugging information:
```bash
truenas-cli -vvv --log-file debug.log system info
```

Then share `debug.log` when requesting help.

### Run Configuration Doctor

Comprehensive health check:
```bash
truenas-cli config doctor
```

### Check Version

Ensure you're running latest version:
```bash
truenas-cli --version
```

### Report Issues

When reporting issues, include:
1. truenas-cli version
2. Python version (`python --version`)
3. Operating system
4. Output from `truenas-cli config doctor`
5. Debug log if applicable
6. Steps to reproduce

Create issue at: https://github.com/yourusername/truenas-cli/issues

## Advanced Troubleshooting

### Enable Python Debugging

```bash
python -m pdb -m truenas_cli pool list
```

### Inspect HTTP Requests

```bash
truenas-cli -vvv --log-file http-debug.log system info
grep -i "request\|response" http-debug.log
```

### Test API Directly

```bash
curl -H "Authorization: Bearer YOUR-API-KEY" \
     https://truenas.local/api/v2.0/system/info
```

### Check Python Environment

```bash
python -c "import truenas_cli; print(truenas_cli.__file__)"
pip list | grep truenas
```
