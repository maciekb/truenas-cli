# Changelog

All notable changes to TrueNAS CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Shell completion for bash, zsh, and fish
- Dynamic completion for pool names and dataset paths from API
- Watch mode for monitoring commands with auto-refresh
- Advanced filtering with query expressions (=, !=, >, <, >=, <=, ~)
- Column selection for customizing table output
- Sorting capability for list commands
- Quiet mode for automation scripts
- Comprehensive logging system with multiple verbosity levels
- Operation timing measurements
- Log file support for debugging
- Configuration validation command
- Connection testing command
- Configuration health check (doctor command)
- Comprehensive test suite with pytest
- Test fixtures for API mocking
- Testing documentation and examples
- Troubleshooting guide
- Contributing guidelines

### Changed
- Enhanced verbose output with multiple levels (-v, -vv, -vvv)
- Improved error messages with actionable suggestions
- Better SSL certificate error handling
- Enhanced configuration security checks

### Fixed
- SSL verification issues with self-signed certificates
- Configuration file permission warnings
- API error response handling

## [0.1.0] - 2025-01-16

### Added
- Initial release
- Type-safe API client with httpx and Pydantic
- Multi-profile configuration support
- Secure configuration storage (600 permissions)
- Rich terminal output with colors and tables
- Retry logic with exponential backoff
- System information and monitoring commands
- Storage pool management commands
- Dataset management commands
- NFS and SMB share management commands
- Multiple output formats (table, JSON, YAML, plain)
- Global options for profile and output format selection
- Error handling with specific exit codes
- Configuration management commands (init, list, show, set-profile, delete)
- Environment variable support for configuration

### Documentation
- Comprehensive README with usage examples
- Installation instructions
- Quick start guide
- API endpoint documentation
- Common use cases and automation examples
- Security considerations

[Unreleased]: https://github.com/maciekb/truenas-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/maciekb/truenas-cli/releases/tag/v0.1.0
