# TrueNAS CLI - Quick Start Guide

## Installation

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/truenas-cli.git
cd truenas-cli

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

### 2. Verify Installation

```bash
# Check version
truenas-cli --help

# Should show:
# Command-line interface for managing TrueNAS SCALE appliances
```

## Configuration

### 1. Generate TrueNAS API Key

Before using the CLI, you need to generate an API key from your TrueNAS SCALE web interface:

1. Log in to TrueNAS SCALE web interface
2. Click on your username (top-right corner)
3. Select "API Keys"
4. Click "Add" button
5. Give your key a name (e.g., "CLI Access")
6. Copy the generated API key (you won't see it again!)

### 2. Initialize Configuration

```bash
# Interactive setup (recommended for first-time setup)
truenas-cli config init

# You'll be prompted for:
# - TrueNAS URL: https://your-truenas-server.local
# - API Key: (paste your API key here)
```

Or use non-interactive mode:

```bash
truenas-cli config init \
  --url https://truenas.local \
  --api-key "your-api-key-here"
```

### 3. Verify Connection

```bash
truenas-cli system info
```

If successful, you'll see your TrueNAS system information!

## Basic Usage

### System Commands

```bash
# Get system information
truenas-cli system info

# Get TrueNAS version
truenas-cli system version

# Get system state
truenas-cli system state
```

### Configuration Management

```bash
# List all profiles
truenas-cli config list

# Show current profile details
truenas-cli config show

# Create a production profile
truenas-cli config init --profile production

# Switch to production profile
truenas-cli config set-profile production
```

### Output Formats

```bash
# Table format (default)
truenas-cli system info

# JSON format
truenas-cli --output-format json system info

# YAML format
truenas-cli --output-format yaml system info
```

### Using Multiple Profiles

```bash
# Create profiles for different environments
truenas-cli config init --profile dev
truenas-cli config init --profile staging
truenas-cli config init --profile production

# Use specific profile for a command
truenas-cli --profile production system info

# Switch default profile
truenas-cli config set-profile production
```

## Common Workflows

### Daily System Check

```bash
# Quick health check
truenas-cli system info
truenas-cli system version
```

### Setting Up Multiple TrueNAS Instances

```bash
# Home server
truenas-cli config init \
  --profile home \
  --url https://truenas-home.local \
  --api-key "home-api-key"

# Office server
truenas-cli config init \
  --profile office \
  --url https://truenas-office.local \
  --api-key "office-api-key"

# Use them
truenas-cli --profile home system info
truenas-cli --profile office system info
```

### Environment-Specific Setup

```bash
# Development (self-signed cert)
truenas-cli config init \
  --profile dev \
  --url https://dev-truenas.local \
  --api-key "dev-key" \
  --no-verify-ssl

# Production (valid cert)
truenas-cli config init \
  --profile prod \
  --url https://prod-truenas.company.com \
  --api-key "prod-key" \
  --verify-ssl
```

## Troubleshooting

### Connection Issues

```bash
# Enable verbose mode for detailed error messages
truenas-cli --verbose system info
```

### Authentication Errors

```bash
# Verify your configuration
truenas-cli config show

# Check if API key is still valid in TrueNAS web interface
# If expired, regenerate and update:
truenas-cli config init  # Will update existing profile
```

### SSL Certificate Errors

If using self-signed certificates:

```bash
# Disable SSL verification (not recommended for production)
truenas-cli config init --no-verify-ssl

# Or set environment variable
export TRUENAS_VERIFY_SSL=false
```

### Configuration File Location

The configuration is stored at:
- Linux/macOS: `~/.truenas-cli/config.json`
- Windows: `%USERPROFILE%\.truenas-cli\config.json`

You can also set a custom location:
```bash
export TRUENAS_CONFIG_DIR=/path/to/config
```

## Environment Variables

Override settings without modifying configuration:

```bash
# Override URL
export TRUENAS_URL=https://truenas.local

# Override API key (be careful with this!)
export TRUENAS_API_KEY=your-api-key

# Override active profile
export TRUENAS_PROFILE=production

# Override output format
export TRUENAS_OUTPUT_FORMAT=json

# Use them
truenas-cli system info
```

## Shell Completion

Enable auto-completion for your shell:

```bash
# Bash
truenas-cli --install-completion bash
source ~/.bashrc

# Zsh
truenas-cli --install-completion zsh
source ~/.zshrc

# Fish
truenas-cli --install-completion fish
```

## Security Best Practices

1. **Never commit API keys to version control**
   - Use environment variables in CI/CD
   - Add `.truenas-cli/` to your `.gitignore`

2. **Use profile-specific keys**
   - Generate separate API keys for dev/staging/prod
   - Rotate keys regularly

3. **Enable SSL verification**
   - Use valid certificates in production
   - Only disable for local development

4. **Restrict API key permissions**
   - Create API keys with minimal required permissions
   - Use read-only keys where possible

5. **Secure your configuration**
   - Config file is automatically set to 600 permissions
   - Keep your system user account secure

## Getting Help

### Command Help

```bash
# Main help
truenas-cli --help

# Command-specific help
truenas-cli config --help
truenas-cli config init --help
truenas-cli system --help
```

### Verbose Mode

```bash
# See detailed request/response information
truenas-cli --verbose system info
```

### Version Information

```bash
truenas-cli config --version  # Shows CLI version
truenas-cli system version     # Shows TrueNAS version
```

## Next Steps

Now that you have the basics working, you can:

1. Explore available commands with `--help`
2. Set up profiles for all your TrueNAS instances
3. Start automating your workflows
4. Check the README.md for advanced features
5. Review VERIFICATION.md for all available functionality

## Example Script

Here's a simple script to check all your TrueNAS instances:

```bash
#!/bin/bash
# check-all-truenas.sh

PROFILES=("home" "office" "backup")

for profile in "${PROFILES[@]}"; do
  echo "=== Checking $profile ==="
  truenas-cli --profile "$profile" system info
  echo ""
done
```

Make it executable and run:
```bash
chmod +x check-all-truenas.sh
./check-all-truenas.sh
```

---

**Happy TrueNAS managing!** 🚀
