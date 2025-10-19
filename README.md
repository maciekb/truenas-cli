# TrueNAS CLI

A modern, feature-rich command-line interface for TrueNAS SCALE API v25.10+

## Features

- **WebSocket-based** - Fast, efficient API communication using JSON-RPC 2.0
- **Comprehensive** - Manage pools, datasets, shares, snapshots, services, and more
- **Type-safe** - Full type hints and runtime validation
- **Well-tested** - Extensive test coverage (unit + integration)
- **User-friendly** - Clear error messages, JSON output, dry-run mode

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/truenas-cli.git
cd truenas-cli

# Create a virtual environment managed by uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install project (and development) dependencies
uv sync --group dev
```

### Configuration

Start from the provided template:

```bash
cp config/.env.example .env
```

Then set your TrueNAS credentials:

```bash
TRUENAS_HOST=192.168.1.100
TRUENAS_API_KEY=your-api-key-here
TRUENAS_PORT=443
TRUENAS_INSECURE=false
```

Or use command-line arguments:

```bash
uv run python truenas-cli.py -H truenas.local -k your-api-key [command]
```

### Basic Usage

```bash
# Test connection
uv run python truenas-cli.py test

# Get system information
uv run python truenas-cli.py system info

# List pools
uv run python truenas-cli.py pool list

# List datasets
uv run python truenas-cli.py dataset list

# Create SMB share
uv run python truenas-cli.py smb create --pool tank --dataset data --share Media

# List snapshots
uv run python truenas-cli.py snapshot list

# Check alerts
uv run python truenas-cli.py alerts list

# List applications (TrueNAS SCALE)
uv run python truenas-cli.py app list

# Start/stop applications
uv run python truenas-cli.py app start plex
uv run python truenas-cli.py app stop plex
```

## Available Commands

### General
- `test` - Test connection to TrueNAS

### System
- `system info` - Display system information
- `system version` - Show TrueNAS version
- `system reboot` - Reboot the system
- `system shutdown` - Shutdown the system

### Storage Pools
- `pool list` - List all pools
- `pool info <pool>` - Get pool details
- `pool create` - Create a new pool
- `pool delete` - Delete a pool
- `pool import` - Import existing pool
- `pool scrub list|run|update|delete` - Manage scrub schedules and runs
- `pool resilver status|update` - Manage resilver priority windows
- `pool snapshottask list|create|update|delete|run` - Manage periodic snapshot tasks

### Datasets
- `dataset list` - List datasets
- `dataset info <dataset>` - Get dataset details
- `dataset create` - Create new dataset
- `dataset delete` - Delete dataset

### Shares
- `smb list` - List SMB shares
- `smb create` - Create SMB share
- `smb delete` - Delete SMB share
- `nfs list` - List NFS shares
- `nfs create` - Create NFS share
- `nfs delete` - Delete NFS share

### Snapshots
- `snapshot list` - List snapshots
- `snapshot create` - Create snapshot
- `snapshot delete` - Delete snapshot
- `snapshot rollback` - Rollback to snapshot

### Disks
- `disk list` - List all disks
- `disk health <disk>` - Show disk health details

### Services
- `service list` - List all services
- `service start <name>` - Start a service
- `service stop <name>` - Stop a service
- `service restart <name>` - Restart a service

### Alerts
- `alerts list` - List active alerts
- `alerts dismiss <id>` - Dismiss an alert

### Applications (TrueNAS SCALE)
- `app list` - List installed applications
- `app info <name>` - Get application details
- `app available` - List available applications
- `app categories` - List application categories
- `app start <name>` - Start an application
- `app stop <name>` - Stop an application
- `app delete <name>` - Delete/uninstall an application
- `app redeploy <name>` - Redeploy an application
- `app upgrade <name>` - Upgrade an application
- `app config` - Get apps configuration
- `app images` - List Docker images

### Users
- `user list` - List all users
- `user info <id>` - Get user details
- `user create <username> <fullname>` - Create a new user
- `user delete <id>` - Delete a user
- `user set-password <id> <password>` - Set user password
- `user shells` - List available shells

### Groups
- `group list` - List all groups
- `group info <id>` - Get group details
- `group create <name>` - Create a new group
- `group update <id>` - Update a group
- `group delete <id>` - Delete a group

### Replication
- `replication list` - List all replication tasks
- `replication info <id>` - Get task details
- `replication create <name> <direction> <transport> <source> <target>` - Create task
- `replication update <id>` - Update a task
- `replication delete <id>` - Delete a task
- `replication run <id>` - Run a task
- `replication run-once <direction> <transport> <source> <target>` - One-time replication
- `replication datasets` - List available datasets
- `replication schemas` - List snapshot naming schemas

### Cloud Sync
- `cloudsync list` - List all cloud sync tasks
- `cloudsync info <id>` - Get task details
- `cloudsync create <path> <credentials> <direction> <transfer_mode> <bucket>` - Create task
- `cloudsync update <id>` - Update a task
- `cloudsync delete <id>` - Delete a task
- `cloudsync sync <id>` - Run a task
- `cloudsync abort <id>` - Abort running task
- `cloudsync providers` - List supported cloud providers
- `cloudsync list-buckets <credentials>` - List buckets
- `cloudsync creds list` - List credentials
- `cloudsync creds info <id>` - Get credential details
- `cloudsync creds create <name> <provider> <attributes>` - Create credentials
- `cloudsync creds delete <id>` - Delete credentials
- `cloudsync creds verify <provider> <attributes>` - Verify credentials

## Advanced Usage

### JSON Output

All commands support `--json` flag for machine-readable output:

```bash
uv run python truenas-cli.py pool list --json | jq '.[] | {name, status}'
```
uv run python truenas-cli.py pool snapshottask list --dataset tank/data
uv run python truenas-cli.py pool snapshottask create tank/data \
  --naming-schema "auto_%Y-%m-%d_%H-%M" \
  --lifetime-value 2 --lifetime-unit WEEK \
  --schedule "0 * * * *" --recursive
uv run python truenas-cli.py pool snapshottask run 7
```

#### Maintenance Windows

Resilver and scrub tasks support optional maintenance windows:

```bash
uv run python truenas-cli.py pool resilver update --begin 19:00 --end 05:00 --weekday 1,2,3,4,5 --enable
uv run python truenas-cli.py pool scrub update 3 --threshold 21 --schedule "0 2 * * *" --begin 01:00 --end 04:00
```

### Dry Run Mode

Preview changes without applying them:

```bash
uv run python truenas-cli.py dataset create tank/test --dry-run
```

### Verbose Logging

Use `-v` for INFO level, `-vv` for DEBUG level:

```bash
uv run python truenas-cli.py -vv pool list
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_client.py

# Run integration tests only
uv run pytest -m integration
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Check linting
uv run ruff check .

# Fix linting issues
uv run ruff check . --fix

# Initialize pyrefly (first run)
uv run pyrefly init

# Type checking
uv run pyrefly check
```

### Project Structure

```
truenas-cli/
├── src/
│   ├── truenas_client/     # API client library
│   │   ├── client.py       # Main client implementation
│   │   └── retry.py        # Retry logic
│   └── truenas_cli/        # CLI implementation
│       ├── cli.py          # Argument parser
│       ├── core.py         # Core utilities
│       ├── validation.py   # Input validation
│       └── commands/       # Command implementations
├── tests/                  # Test suite
├── examples/               # Usage examples
├── .api/                   # API documentation
└── truenas-cli.py         # Entry point
```

## API Coverage

Based on TrueNAS API v25.10.0 documentation:

**Implemented:**
- ✅ System operations
- ✅ Pool management
- ✅ Dataset operations
- ✅ SMB/NFS shares
- ✅ Snapshot management
- ✅ Service control
- ✅ Disk information
- ✅ Alert management
- ✅ App/Container management
- ✅ User/Group management
- ✅ **Replication (NEW!)**
- ✅ **Cloud Sync (NEW!)**

**Planned:**
- 🚧 VM/Virtualization
- 🚧 Network configuration
- 🚧 Certificate management
- 🚧 System updates

## Requirements

- Python 3.8+
- TrueNAS SCALE 25.10+ (Community Edition)
- Network access to TrueNAS WebSocket API (port 443)

## Authentication

### API Key (Recommended)

Generate an API key in TrueNAS WebUI:
1. Go to Settings → API Keys
2. Click "Add"
3. Set name and permissions
4. Copy the generated key

### Username/Password

```bash
uv run python truenas-cli.py -u root -P password [command]
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Follow coding guidelines (see CLAUDE.md)
4. Add tests for new features
5. Run quality checks (`ruff format`, `ruff check`, `pytest`)
6. Commit changes (`git commit -m 'feat: add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open Pull Request

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines.

## Documentation

- [Development Guide](CLAUDE.md) - Coding standards and guidelines
- [Examples](examples/README.md) - Detailed usage examples
- [API Documentation](.api/truenas-v25.10.0-docs/index.html) - TrueNAS API reference

## Troubleshooting

### Connection Issues

```bash
# Self-signed certificate
uv run python truenas-cli.py --insecure test

# Custom port
uv run python truenas-cli.py --port 8443 test

# Disable SSL
uv run python truenas-cli.py --no-ssl --port 80 test
```

### Authentication Errors

- Verify API key is valid and not expired
- Check user permissions in TrueNAS
- Ensure API access is enabled

### Common Errors

**"Connection refused"**
- TrueNAS is not running or unreachable
- Firewall blocking port 443
- Wrong hostname/IP address

**"SSL verification failed"**
- Use `--insecure` flag for self-signed certificates
- Or install the CA certificate properly

**"Method not found"**
- Incompatible TrueNAS version
- Feature not available in your edition

## License

MIT License - See [LICENSE](LICENSE) file for details

## Acknowledgments

- Built for TrueNAS SCALE Community Edition
- Uses the official TrueNAS WebSocket API
- Inspired by modern CLI tools and best practices

## Support

- Issues: [GitHub Issues](https://github.com/yourusername/truenas-cli/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/truenas-cli/discussions)
- API Docs: https://api.truenas.com/v25.10/
