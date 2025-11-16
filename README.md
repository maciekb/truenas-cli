# TrueNAS CLI

A modern, production-ready command-line interface for managing TrueNAS SCALE appliances. Built with Python, this CLI provides an intuitive way to automate TrueNAS operations through its REST API.

## Features

### Core Features
- **Type-safe API Client**: Built with httpx and Pydantic for robust API interactions
- **Multi-profile Support**: Manage multiple TrueNAS instances with profile switching
- **Secure Configuration**: API keys stored with proper file permissions (600)
- **Rich Terminal Output**: Beautiful, colorful output powered by Rich
- **Auto-completion**: Shell completion for bash, zsh, and fish
- **Error Handling**: Helpful error messages with actionable guidance
- **Retry Logic**: Automatic retry with exponential backoff for transient failures

### Advanced Features
- **Watch Mode**: Auto-refreshing display for monitoring commands
- **Filtering & Sorting**: Query-based filtering and sorting for list commands
- **Batch Operations**: Process multiple operations from YAML/JSON files
- **Parallel Execution**: Run batch operations in parallel for speed
- **Verbose Logging**: Multiple verbosity levels (-v, -vv, -vvv) with file logging
- **Configuration Doctor**: Comprehensive health checks and diagnostics
- **Operation Timing**: Measure command execution time
- **Quiet Mode**: Minimal output for automation scripts

## Requirements

- Python 3.10 or higher
- TrueNAS SCALE with API access
- TrueNAS API key (generated from the TrueNAS web interface)

## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/maciekb/truenas-cli.git
cd truenas-cli
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install in development mode:
```bash
pip install -e .
```

For development with additional tools:
```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Generate a TrueNAS API Key

1. Log in to your TrueNAS SCALE web interface
2. Navigate to the top-right user menu → API Keys
3. Click "Add" to create a new API key
4. Copy the generated key (you won't be able to see it again)

### 2. Initialize Configuration

Run the interactive configuration wizard:

```bash
truenas-cli config init
```

You'll be prompted for:
- Profile name (default: "default")
- TrueNAS URL (e.g., https://truenas.local or https://192.168.1.100)
- API key (the key you generated in step 1)

The configuration will be saved to `~/.truenas-cli/config.json` with secure permissions.

### 3. Verify Connection

```bash
truenas-cli system info
```

## Usage

### Configuration Management

```bash
# Initialize a new profile
truenas-cli config init

# List all profiles
truenas-cli config list

# Set active profile
truenas-cli config set-profile production

# Show current configuration
truenas-cli config show
```

### System Commands

```bash
# Get system information
truenas-cli system info

# Get system version
truenas-cli system version

# Check system health
truenas-cli system health

# View system resource statistics
truenas-cli system stats

# List active system alerts
truenas-cli system alerts
```

### Storage Pool Commands

```bash
# List all storage pools
truenas-cli pool list

# Get detailed status of a specific pool
truenas-cli pool status tank

# View I/O statistics for a pool
truenas-cli pool stats tank

# Start a pool scrub (data integrity check)
truenas-cli pool scrub tank

# Stop a running scrub
truenas-cli pool scrub tank --action stop

# Get pool expansion information
truenas-cli pool expand tank
```

### Dataset Commands

```bash
# List all datasets
truenas-cli dataset list

# List datasets in a specific pool
truenas-cli dataset list tank

# Create a new dataset
truenas-cli dataset create tank/mydata

# Create dataset with compression and quota
truenas-cli dataset create tank/mydata --compression lz4 --quota 100G

# Create dataset with custom record size
truenas-cli dataset create tank/mydata --recordsize 1M

# Get detailed dataset information
truenas-cli dataset info tank/mydata

# Modify dataset properties
truenas-cli dataset set tank/mydata compression zstd
truenas-cli dataset set tank/mydata quota 200G
truenas-cli dataset set tank/mydata readonly on

# Delete a dataset (with confirmation)
truenas-cli dataset delete tank/mydata

# Delete dataset recursively without confirmation
truenas-cli dataset delete tank/mydata --recursive --yes
```

### Snapshot Commands

```bash
# List all snapshots
truenas-cli snapshot list

# List snapshots for a specific dataset
truenas-cli snapshot list tank/data

# Create a snapshot
truenas-cli snapshot create tank/data@backup-2025-01-15

# Create a recursive snapshot (includes all child datasets)
truenas-cli snapshot create tank/data@daily --recursive

# Create snapshot with VMware sync
truenas-cli snapshot create tank/vmware@pre-update --vmware-sync

# View detailed snapshot information
truenas-cli snapshot info tank/data@backup-2025-01-15

# Clone a snapshot to a new dataset
truenas-cli snapshot clone tank/data@backup-2025-01-15 tank/data-restore

# Delete a snapshot (with confirmation)
truenas-cli snapshot delete tank/data@old-snapshot

# Delete snapshot without confirmation
truenas-cli snapshot delete tank/data@old-snapshot --yes

# Delete snapshot and its dependent clones
truenas-cli snapshot delete tank/data@old-snapshot --recursive --yes

# Rollback to a snapshot (DESTRUCTIVE - requires --force and confirmation)
truenas-cli snapshot rollback tank/data@backup-2025-01-15 --force

# Rollback with recursive deletion of newer snapshots
truenas-cli snapshot rollback tank/data@last-good --force --recursive
```

### Share Commands

```bash
# List all shares (NFS and SMB)
truenas-cli share list

# List only NFS shares
truenas-cli share list --type nfs

# List only SMB shares
truenas-cli share list --type smb

# Create an NFS share
truenas-cli share create-nfs /mnt/tank/data

# Create NFS share with options
truenas-cli share create-nfs /mnt/tank/data \
  --comment "Public data" \
  --readonly \
  --networks "192.168.1.0/24,10.0.0.0/8"

# Create an SMB share
truenas-cli share create-smb myshare /mnt/tank/data

# Create SMB share with guest access
truenas-cli share create-smb public /mnt/tank/public \
  --comment "Public files" \
  --guest

# Get share information
truenas-cli share info 1 --type nfs
truenas-cli share info 2 --type smb

# Delete a share
truenas-cli share delete 1 --type nfs
truenas-cli share delete 2 --type smb --yes
```

### Global Options

All commands support these global options:

```bash
# Use a specific profile
truenas-cli --profile production system info

# Change output format (json, yaml, table, plain)
truenas-cli --output-format json system info

# Enable verbose output (multiple levels)
truenas-cli -v system info         # INFO level
truenas-cli -vv system info        # DEBUG level
truenas-cli -vvv system info       # Maximum verbosity

# Quiet mode for automation
truenas-cli --quiet pool list

# Show operation timing
truenas-cli --timing pool list

# Write logs to file
truenas-cli --log-file debug.log -vv system info

# Get help
truenas-cli --help
truenas-cli system --help
```

## Advanced Usage

### Shell Completion

Install shell completion for command and argument suggestions:

```bash
# Auto-detect shell and install
truenas-cli completion install

# Install for specific shell
truenas-cli completion install --shell bash
truenas-cli completion install --shell zsh
truenas-cli completion install --shell fish

# Show completion script
truenas-cli completion show --shell bash

# Uninstall completion
truenas-cli completion uninstall
```

After installation, restart your shell or source the completion file.

### Watch Mode

Monitor commands with auto-refresh:

```bash
# Watch pool status (refreshes every 2 seconds)
truenas-cli pool status tank --watch

# Custom interval
truenas-cli pool status tank --watch --interval 5

# Watch system stats
truenas-cli system stats --watch
```

Press Ctrl+C to exit watch mode.

### Filtering and Sorting

Filter list output with query expressions:

```bash
# Filter by exact match
truenas-cli pool list --filter "status=ONLINE"

# Filter by contains (case-insensitive)
truenas-cli dataset list --filter "name~backup"

# Numeric comparisons
truenas-cli dataset list --filter "used>1000000000"

# Multiple filters (AND logic)
truenas-cli pool list --filter "status=ONLINE" --filter "healthy=true"

# Sort results
truenas-cli pool list --sort name
truenas-cli pool list --sort size --reverse

# Select specific columns
truenas-cli pool list --columns name,status,size
```

### Batch Operations

Process multiple operations from YAML or JSON files:

```bash
# Validate a batch file
truenas-cli batch validate operations.yaml

# Execute batch operations sequentially
truenas-cli batch execute operations.yaml

# Execute in parallel with 8 workers
truenas-cli batch execute operations.yaml --parallel --workers 8

# Dry run (preview without executing)
truenas-cli batch execute operations.yaml --dry-run

# Stop on first error
truenas-cli batch execute operations.yaml --stop-on-error

# Create a sample batch file
truenas-cli batch create-sample my-operations.yaml
```

**Example batch file** (`operations.yaml`):
```yaml
operations:
  - id: create_dataset_1
    command: dataset create
    args:
      path: tank/data
      compression: lz4

  - id: create_dataset_2
    command: dataset create
    args:
      path: tank/backup
      compression: zstd

  - id: snapshot_data
    command: snapshot create
    args:
      dataset: tank/data
      snapshot_name: backup-2025-01-15
      recursive: true

  - id: list_datasets
    command: dataset list
    args:
      pool: tank
```

See `examples/batch-operations.yaml` for a complete example.

### Configuration Validation

Check configuration health:

```bash
# Validate configuration syntax
truenas-cli config validate

# Test connection to TrueNAS
truenas-cli config test

# Comprehensive health check
truenas-cli config doctor
```

### Debugging and Troubleshooting

Debug connection and API issues:

```bash
# Maximum verbosity with file logging
truenas-cli -vvv --log-file debug.log system info

# Show request/response details
truenas-cli -vv pool list

# Test specific profile
truenas-cli config test --profile production

# Check configuration health
truenas-cli config doctor
```

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed troubleshooting guide.

## Configuration

### Configuration File Location

The default configuration is stored at `~/.truenas-cli/config.json`.

### Environment Variables

You can override configuration with environment variables:

- `TRUENAS_URL`: TrueNAS API URL
- `TRUENAS_API_KEY`: API key for authentication
- `TRUENAS_PROFILE`: Active profile name
- `TRUENAS_CONFIG_DIR`: Custom configuration directory

### Multiple Profiles

Manage multiple TrueNAS instances with profiles:

```bash
# Create profiles for different environments
truenas-cli config init  # Creates "default" profile
truenas-cli --profile production config init
truenas-cli --profile staging config init

# Switch between profiles
truenas-cli config set-profile production

# Or use --profile flag
truenas-cli --profile staging system info
```

### Configuration File Structure

```json
{
  "active_profile": "default",
  "profiles": {
    "default": {
      "url": "https://truenas.local",
      "api_key": "your-api-key-here",
      "verify_ssl": true,
      "timeout": 30
    },
    "production": {
      "url": "https://prod.truenas.local",
      "api_key": "prod-api-key",
      "verify_ssl": true,
      "timeout": 30
    }
  }
}
```

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/maciekb/truenas-cli.git
cd truenas-cli

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"
```

### Code Quality Tools

```bash
# Format code with Black
black src/

# Lint with Ruff
ruff check src/

# Type check with mypy
mypy src/

# Run tests
pytest

# Run tests with coverage
pytest --cov=truenas_cli --cov-report=html
```

### Project Structure

```
truenas-cli/
├── pyproject.toml          # Project configuration
├── README.md               # This file
├── .gitignore              # Git ignore rules
├── src/
│   └── truenas_cli/
│       ├── __init__.py     # Package initialization
│       ├── __main__.py     # Entry point for python -m
│       ├── cli.py          # Main Typer application
│       ├── config.py       # Configuration management
│       ├── client/
│       │   ├── __init__.py
│       │   ├── base.py     # Base API client with all endpoints
│       │   ├── models.py   # Pydantic models for API responses
│       │   └── exceptions.py  # Custom exceptions
│       ├── utils/
│       │   ├── __init__.py
│       │   └── formatters.py  # Output formatting utilities
│       └── commands/
│           ├── __init__.py
│           ├── config.py   # Configuration commands
│           ├── system.py   # System monitoring commands
│           ├── pool.py     # Storage pool commands
│           ├── dataset.py  # Dataset management commands
│           ├── snapshot.py # Snapshot management commands
│           └── share.py    # Share management commands
└── tests/
    └── __init__.py
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Authentication error
- `3`: Configuration error

## Security Considerations

- **API Keys**: Never commit API keys to version control
- **File Permissions**: Configuration files are automatically set to 600 (read/write for owner only)
- **SSL Verification**: SSL certificate verification is enabled by default
- **Environment Variables**: Use environment variables for CI/CD environments

## Common Use Cases

### Automated Pool Monitoring

Monitor pool health and trigger alerts:

```bash
#!/bin/bash
# Check pool health and alert if issues found
STATUS=$(truenas-cli pool status tank --output-format json | jq -r '.status')

if [ "$STATUS" != "ONLINE" ]; then
  echo "WARNING: Pool tank is $STATUS" | mail -s "TrueNAS Alert" admin@example.com
fi
```

### Automated Dataset Creation

Create datasets with consistent settings:

```bash
#!/bin/bash
# Create multiple datasets with compression
for dataset in docs videos photos; do
  truenas-cli dataset create tank/$dataset \
    --compression lz4 \
    --quota 500G
done
```

### Share Management Automation

Automate share creation for new projects:

```bash
#!/bin/bash
PROJECT_NAME="$1"

# Create dataset
truenas-cli dataset create tank/projects/$PROJECT_NAME --compression zstd

# Create SMB share
truenas-cli share create-smb "$PROJECT_NAME" "/mnt/tank/projects/$PROJECT_NAME" \
  --comment "Project $PROJECT_NAME files"

echo "Project $PROJECT_NAME setup complete"
```

### System Health Monitoring

Regular health checks in cron:

```bash
# Add to crontab: */15 * * * *
#!/bin/bash
ALERTS=$(truenas-cli system alerts --output-format json | jq 'length')

if [ "$ALERTS" -gt 0 ]; then
  truenas-cli system alerts --output-format plain | \
    mail -s "TrueNAS Alerts" admin@example.com
fi
```

### Automated Snapshot Management

Create daily snapshots and cleanup old ones:

```bash
#!/bin/bash
# Daily snapshot script
DATE=$(date +%Y-%m-%d)
DATASET="tank/important-data"

# Create daily snapshot
truenas-cli snapshot create "${DATASET}@daily-${DATE}" --recursive

# List snapshots older than 30 days and delete them
truenas-cli snapshot list "$DATASET" --output-format json | \
  jq -r '.[] | select(.created < (now - 2592000)) | .name' | \
  while read snapshot; do
    truenas-cli snapshot delete "$snapshot" --yes
  done

echo "Snapshot management completed for $DATASET"
```

### Pre-Update Snapshot Workflow

Create safety snapshots before system updates:

```bash
#!/bin/bash
# Create pre-update snapshots
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Snapshot critical datasets
for dataset in tank/data tank/home tank/config; do
  truenas-cli snapshot create "${dataset}@pre-update-${TIMESTAMP}" --recursive
  echo "Created safety snapshot for $dataset"
done

echo "All pre-update snapshots created"
echo "To rollback if needed:"
echo "  truenas-cli snapshot rollback <dataset>@pre-update-${TIMESTAMP} --force"
```

## Output Formats

All commands support multiple output formats:

### Table Format (Default)

Human-readable tables with color coding:
```bash
truenas-cli pool list
```

### JSON Format

Machine-readable JSON for scripting:
```bash
truenas-cli pool list --output-format json
truenas-cli pool list --output-format json | jq '.[] | select(.status == "DEGRADED")'
```

### Plain Text Format

Tab-separated values for easy parsing:
```bash
truenas-cli pool list --output-format plain
truenas-cli pool list --output-format plain | awk '{print $1, $2}'
```

## Troubleshooting

### Connection Issues

```bash
# Verify your TrueNAS URL is accessible
curl https://your-truenas.local/api/v2.0/system/info

# Enable verbose mode for detailed error messages
truenas-cli --verbose system info
```

### Authentication Errors

- Verify your API key is correct
- Check that the API key hasn't been revoked in TrueNAS
- Ensure you're using the correct profile

### SSL Certificate Errors

If you're using self-signed certificates:

```bash
# Temporarily disable SSL verification (not recommended for production)
export TRUENAS_VERIFY_SSL=false
```

Or update your profile configuration to set `verify_ssl: false`.

### API Endpoint Not Found

If you get 404 errors:
- Ensure you're running TrueNAS SCALE (not CORE)
- Check your TrueNAS version supports the API endpoints
- Update TrueNAS to the latest version

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for the CLI framework
- Uses [httpx](https://www.python-httpx.org/) for HTTP operations
- Data validation powered by [Pydantic](https://docs.pydantic.dev/)
- Terminal output enhanced by [Rich](https://rich.readthedocs.io/)
