# TrueNAS CLI - Expansion Opportunities Analysis

**Analysis Date:** January 2025
**Current Version:** Based on main branch
**Target Audience:** System administrators automating TrueNAS SCALE operations

---

## Executive Summary

This comprehensive analysis identifies **28 distinct expansion opportunities** for the TrueNAS CLI application, organized into five strategic categories. The current implementation provides solid coverage of core storage operations (pools, datasets, snapshots, shares) and basic system monitoring, representing approximately **30-35% coverage** of common TrueNAS administrative tasks.

**Key Findings:**
- **High-Priority Gaps:** User/group management, service control, disk operations, and replication are critical missing features affecting automation workflows
- **Quick Wins:** Several features (service management, basic user operations, job monitoring) offer high user value with relatively low implementation complexity
- **Strategic Opportunities:** Advanced monitoring dashboards, backup/restore workflows, and interactive wizards could significantly differentiate the CLI from web UI
- **API Maturity:** TrueNAS SCALE REST API v2.0 provides comprehensive endpoint coverage for most recommended features

**Top 3 Recommendations:**
1. **Implement service management** (start/stop/status for NFS, SMB, SSH, etc.) - critical for automation scripts
2. **Add user and group management** - essential for access control automation
3. **Develop replication management** - core backup/DR workflow currently missing

---

## Current State Assessment

### Implemented Features Overview

The TrueNAS CLI currently implements **6 major command groups** with **40+ individual commands**:

#### System Monitoring (7 commands)
- ✅ System information and version
- ✅ Health checks and alerts
- ✅ Resource statistics (CPU, memory)
- ✅ Boot ID retrieval

#### Storage Pool Management (5 commands)
- ✅ List pools with filtering
- ✅ Detailed pool status and topology
- ✅ Pool scrub operations (start/stop)
- ✅ I/O statistics
- ✅ Expansion information

#### Dataset Operations (5 commands)
- ✅ Create/read/update/delete datasets
- ✅ Property management (compression, quota, recordsize)
- ✅ Listing with filters

#### Snapshot Management (5 commands)
- ✅ Create snapshots (with recursive and VMware sync)
- ✅ Clone snapshots to new datasets
- ✅ Rollback (with safety confirmations)
- ✅ Delete with dependency handling
- ✅ Detailed snapshot information

#### Share Management (4 commands)
- ✅ NFS share creation and management
- ✅ SMB share creation and management
- ✅ Share listing with type filters
- ✅ Detailed share information

#### Configuration Management (7 commands)
- ✅ Multi-profile support
- ✅ Interactive initialization wizard
- ✅ Configuration validation and testing
- ✅ Health diagnostics (doctor command)
- ✅ Shell completion support

### Coverage Analysis

**Estimated Coverage by Administrative Area:**
- Storage Operations: **85%** - Excellent coverage of pools, datasets, snapshots
- Share Management: **60%** - Basic NFS/SMB, missing iSCSI and advanced options
- System Monitoring: **50%** - Basic info and alerts, missing detailed metrics
- User Management: **0%** - Critical gap
- Service Management: **0%** - Critical gap
- Network Configuration: **0%** - Not implemented
- Disk Management: **10%** - Only via pool operations
- Backup/Replication: **0%** - Critical gap for DR workflows
- Applications/VMs: **0%** - Not implemented
- Security/Certificates: **0%** - Not implemented

### Current Strengths

1. **Excellent Storage Foundation:** Comprehensive ZFS operations with safety features
2. **Robust Error Handling:** Helpful error messages with actionable tips
3. **Professional UX:** Watch mode, filtering, multiple output formats (JSON/YAML/table/plain)
4. **Safe Operations:** Confirmation prompts for destructive actions, force flags for safety
5. **Automation-Friendly:** JSON output, quiet mode, exit codes, multi-profile support
6. **Well-Architected:** Clean separation of concerns, consistent patterns, type-safe with Pydantic

### Current Gaps

1. **No User/Group Management:** Cannot automate access control
2. **No Service Control:** Cannot start/stop services (NFS, SMB, SSH, etc.)
3. **No Replication:** Missing critical backup/DR workflows
4. **No Disk Operations:** Cannot manage individual disks or SMART tests
5. **Limited Network Config:** No IPMI, network interface, or DNS management
6. **No Task/Job Monitoring:** Cannot track long-running operations
7. **No Application Management:** Cannot deploy or manage TrueNAS SCALE apps
8. **Limited Reporting:** No detailed performance or capacity reports

---

## Expansion Opportunities

### Category 1: Missing Core API Features

These are essential TrueNAS administrative functions with confirmed API support.

#### 1.1 User and Group Management
- **Description:** Commands to create, list, update, and delete users and groups
- **User Value:** **HIGH** - Essential for access control automation, onboarding/offboarding
- **Implementation Effort:** **Medium** - API available (`/user`, `/group`), moderate complexity for permissions
- **API Availability:** ✅ Confirmed - `/api/v2.0/user`, `/api/v2.0/group`
- **Priority:** **P0 (Critical)**
- **Commands Needed:**
  - `truenas-cli user list/create/update/delete/info`
  - `truenas-cli user set-password/set-ssh-key`
  - `truenas-cli group list/create/update/delete/info`
  - `truenas-cli group add-member/remove-member`
- **Notes:** Core security feature. Must handle UIDs/GIDs, shell assignment, home directory creation, password policies

#### 1.2 Service Management
- **Description:** Start, stop, restart, and check status of TrueNAS services
- **User Value:** **HIGH** - Critical for automation scripts that configure then enable services
- **Implementation Effort:** **Simple** - Straightforward API endpoints
- **API Availability:** ✅ Confirmed - `/api/v2.0/service`
- **Priority:** **P0 (Critical)**
- **Commands Needed:**
  - `truenas-cli service list` - Show all services and their status
  - `truenas-cli service start/stop/restart <service>`
  - `truenas-cli service status <service>` - Detailed service info
  - `truenas-cli service enable/disable <service>` - Start on boot
- **Services:** NFS, SMB, SSH, FTP, SNMP, S3, iSCSI, UPS, SMART
- **Notes:** Must handle service dependencies, provide clear status messages

#### 1.3 Replication Management
- **Description:** Configure and manage ZFS replication tasks for backup/DR
- **User Value:** **HIGH** - Essential for disaster recovery automation
- **Implementation Effort:** **Complex** - Advanced ZFS features, SSH keys, scheduling
- **API Availability:** ✅ Confirmed - `/api/v2.0/replication`
- **Priority:** **P1 (Important)**
- **Commands Needed:**
  - `truenas-cli replication list/create/delete`
  - `truenas-cli replication run <task-id>` - Trigger immediate run
  - `truenas-cli replication status <task-id>` - Show progress
  - `truenas-cli replication test <task-id>` - Validate configuration
- **Notes:** Complex feature requiring SSH key management, snapshot coordination, bandwidth throttling

#### 1.4 Disk Management
- **Description:** View disk information, run SMART tests, manage disk lifecycle
- **User Value:** **HIGH** - Proactive hardware monitoring and maintenance
- **Implementation Effort:** **Medium** - SMART test scheduling, result parsing
- **API Availability:** ✅ Confirmed - `/api/v2.0/disk`, `/api/v2.0/smart`
- **Priority:** **P1 (Important)**
- **Commands Needed:**
  - `truenas-cli disk list` - Show all disks with serial, model, temperature
  - `truenas-cli disk info <disk-name>` - Detailed disk info
  - `truenas-cli disk smart-test <disk-name>` - Run SMART tests
  - `truenas-cli disk temperature` - Show all disk temps
  - `truenas-cli disk wipe <disk-name>` - Securely erase disk
- **Notes:** Critical for hardware lifecycle management, prevent failures

#### 1.5 Task and Job Monitoring
- **Description:** Track status of long-running background jobs
- **User Value:** **HIGH** - Essential for automation workflows waiting on operations
- **Implementation Effort:** **Medium** - Job state tracking, progress display
- **API Availability:** ✅ Confirmed - `/api/v2.0/core/get_jobs`
- **Priority:** **P1 (Important)**
- **Commands Needed:**
  - `truenas-cli job list` - Show running and recent jobs
  - `truenas-cli job status <job-id>` - Detailed job status with progress
  - `truenas-cli job wait <job-id>` - Block until job completes
  - `truenas-cli job logs <job-id>` - View job output
  - `truenas-cli job abort <job-id>` - Cancel running job
- **Notes:** Enables automation scripts to wait for scrubs, replication, etc.

#### 1.6 iSCSI Target Management
- **Description:** Manage iSCSI targets, extents, initiators for block storage
- **User Value:** **Medium** - Important for virtualization environments
- **Implementation Effort:** **Complex** - Many interconnected components
- **API Availability:** ✅ Confirmed - `/api/v2.0/iscsi/*` (multiple endpoints)
- **Priority:** **P2 (Nice-to-have)**
- **Commands Needed:**
  - `truenas-cli iscsi target list/create/delete`
  - `truenas-cli iscsi extent list/create/delete`
  - `truenas-cli iscsi portal list/create/delete`
  - `truenas-cli iscsi initiator list/add/remove`
- **Notes:** Complex multi-component system, may need wizard-style commands

#### 1.7 Network Configuration
- **Description:** Manage network interfaces, static routes, DNS settings
- **User Value:** **Medium** - Useful for initial setup and network changes
- **Implementation Effort:** **Medium** - Network changes are sensitive, need validation
- **API Availability:** ✅ Confirmed - `/api/v2.0/network/*`
- **Priority:** **P2 (Nice-to-have)**
- **Commands Needed:**
  - `truenas-cli network interface list/configure`
  - `truenas-cli network route list/add/delete`
  - `truenas-cli network dns show/set`
  - `truenas-cli network test` - Validate connectivity
- **Notes:** Dangerous - incorrect network config can lock out users

#### 1.8 Cloud Sync Tasks
- **Description:** Manage cloud synchronization to S3, Azure, Google Cloud, etc.
- **User Value:** **Medium** - Growing importance for hybrid cloud backups
- **Implementation Effort:** **Medium** - Multiple cloud providers, credential management
- **API Availability:** ✅ Confirmed - `/api/v2.0/cloudsync`
- **Priority:** **P2 (Nice-to-have)**
- **Commands Needed:**
  - `truenas-cli cloudsync list/create/delete`
  - `truenas-cli cloudsync run <task-id>`
  - `truenas-cli cloudsync test-credentials`
  - `truenas-cli cloudsync providers` - List supported clouds
- **Notes:** Requires secure credential storage, supports 20+ providers

#### 1.9 Update Management
- **Description:** Check for and install TrueNAS updates
- **User Value:** **Medium** - Automation of maintenance windows
- **Implementation Effort:** **Medium** - Must handle reboots, rollback
- **API Availability:** ✅ Confirmed - `/api/v2.0/update`
- **Priority:** **P2 (Nice-to-have)**
- **Commands Needed:**
  - `truenas-cli update check` - Check for available updates
  - `truenas-cli update list` - Show update history
  - `truenas-cli update download` - Pre-download update
  - `truenas-cli update apply` - Install and reboot
  - `truenas-cli update rollback` - Revert to previous version
- **Notes:** High-risk operation, needs extensive safety checks

#### 1.10 Certificate Management
- **Description:** Manage SSL/TLS certificates for services
- **User Value:** **Low-Medium** - Security automation
- **Implementation Effort:** **Medium** - CSR generation, cert installation
- **API Availability:** ✅ Confirmed - `/api/v2.0/certificate`
- **Priority:** **P2 (Nice-to-have)**
- **Commands Needed:**
  - `truenas-cli cert list/create/delete/import`
  - `truenas-cli cert renew` - Renew expiring certs
  - `truenas-cli cert csr` - Generate certificate signing requests
- **Notes:** Important for HTTPS, iSCSI, LDAP configurations

---

### Category 2: User Experience Enhancements

Improvements to make the CLI more intuitive and productive.

#### 2.1 Interactive Setup Wizards
- **Description:** Guided interactive workflows for complex multi-step operations
- **User Value:** **High** - Reduces errors for complex tasks
- **Implementation Effort:** **Medium** - Use libraries like `questionary` or `inquirer`
- **API Availability:** N/A - Enhancement layer
- **Priority:** **P1 (Important)**
- **Wizards Needed:**
  - `truenas-cli wizard pool-create` - Interactive pool creation
  - `truenas-cli wizard share-setup` - Complete share setup (dataset + NFS/SMB + permissions)
  - `truenas-cli wizard replication-setup` - Configure replication end-to-end
  - `truenas-cli wizard first-run` - Initial TrueNAS configuration
- **Notes:** Drastically lowers learning curve for new users

#### 2.2 Enhanced Output Formatting
- **Description:** Better visualization of complex data structures
- **User Value:** **Medium** - Improved readability
- **Implementation Effort:** **Simple** - Leverage existing Rich library
- **API Availability:** N/A - Enhancement layer
- **Priority:** **P2 (Nice-to-have)**
- **Enhancements:**
  - Tree view for dataset hierarchies (`tree` command output style)
  - Sparklines for resource trends in watch mode
  - Color-coded health indicators (expand beyond current red/yellow/green)
  - Progress bars for operations with `--wait` flag
  - Column alignment improvements for large datasets
- **Notes:** Rich library already integrated, just needs expansion

#### 2.3 Bulk Operations
- **Description:** Operate on multiple resources simultaneously
- **User Value:** **High** - Massive time savings for large environments
- **Implementation Effort:** **Medium** - Pattern matching, error aggregation
- **API Availability:** N/A - CLI orchestration layer
- **Priority:** **P1 (Important)**
- **Operations:**
  - `truenas-cli dataset create --bulk tank/{data,logs,backups}`
  - `truenas-cli snapshot delete --pattern "tank/data@daily-*" --older-than 30d`
  - `truenas-cli user create --from-csv users.csv`
  - `truenas-cli share delete --filter "enabled=false"`
- **Notes:** Must handle partial failures gracefully, provide rollback

#### 2.4 Improved Error Messages
- **Description:** Context-aware error messages with troubleshooting suggestions
- **User Value:** **Medium** - Reduces support burden, faster problem resolution
- **Implementation Effort:** **Simple** - Enhance existing exception handlers
- **API Availability:** N/A - Enhancement layer
- **Priority:** **P2 (Nice-to-have)**
- **Improvements:**
  - Detect common issues (quota exceeded, permissions, network unreachable)
  - Suggest related documentation URLs
  - Provide example commands for fixes
  - Show relevant system state when errors occur
- **Notes:** Can leverage AI/LLM for intelligent suggestions in future

#### 2.5 Smart Autocomplete
- **Description:** Context-aware completion beyond basic shell completion
- **User Value:** **Medium** - Faster command composition
- **Implementation Effort:** **Medium** - Dynamic data fetching
- **API Availability:** Uses existing APIs
- **Priority:** **P2 (Nice-to-have)**
- **Features:**
  - Complete pool names, dataset paths, snapshot names from live system
  - Complete share IDs with descriptive text
  - Complete service names
  - Complete user/group names
- **Notes:** Current completion is static; dynamic would query API

#### 2.6 Command Aliases and Shortcuts
- **Description:** User-definable shortcuts for common command sequences
- **User Value:** **Low-Medium** - Convenience for power users
- **Implementation Effort:** **Simple** - Store in config file
- **API Availability:** N/A - Client-side feature
- **Priority:** **P2 (Nice-to-have)**
- **Examples:**
  - `truenas-cli alias set ds "dataset"`
  - `truenas-cli alias set snap-daily "snapshot create {dataset}@daily-$(date +%F)"`
  - Store in `~/.truenas-cli/aliases.json`
- **Notes:** Similar to Git aliases, enhances productivity

---

### Category 3: Automation and Scripting Features

Features specifically designed to support automated workflows.

#### 3.1 Template System
- **Description:** Reusable templates for creating resources with consistent settings
- **User Value:** **High** - Ensures consistency, reduces errors
- **Implementation Effort:** **Medium** - Template engine, variable substitution
- **API Availability:** N/A - CLI orchestration layer
- **Priority:** **P1 (Important)**
- **Capabilities:**
  - `truenas-cli template save dataset production-dataset dataset-template.yaml`
  - `truenas-cli template apply dataset-template.yaml --vars pool=tank,name=new-data`
  - Templates for datasets, shares, replication tasks, users
  - YAML-based with variable substitution
- **Notes:** Critical for IaC workflows, GitOps integration

#### 3.2 Dry-Run Mode
- **Description:** Preview changes without applying them
- **User Value:** **High** - Safety for automation scripts
- **Implementation Effort:** **Medium** - Requires API support or local simulation
- **API Availability:** Some endpoints support dry-run
- **Priority:** **P1 (Important)**
- **Usage:**
  - `truenas-cli dataset create tank/data --dry-run` → shows what would be created
  - `truenas-cli pool scrub tank --dry-run` → validates without starting
  - Output shows: "Would create dataset 'tank/data' with compression=lz4"
- **Notes:** Not all TrueNAS APIs support dry-run, may need client-side validation

#### 3.3 Diff and Comparison Tools
- **Description:** Compare configurations between systems or states
- **User Value:** **Medium** - Useful for troubleshooting and auditing
- **Implementation Effort:** **Medium** - State serialization, diff algorithm
- **API Availability:** Uses existing APIs
- **Priority:** **P2 (Nice-to-have)**
- **Commands:**
  - `truenas-cli diff dataset tank/data1 tank/data2` - Compare two datasets
  - `truenas-cli diff system --profile prod1 --profile prod2` - Compare systems
  - `truenas-cli snapshot diff dataset tank/data@snap1 tank/data@snap2` - Show changes
  - Output in unified diff format or structured JSON
- **Notes:** Valuable for change management, compliance

#### 3.4 Export/Import Configuration
- **Description:** Export entire system config to version-controllable files
- **User Value:** **High** - Disaster recovery, configuration drift detection
- **Implementation Effort:** **Medium** - State serialization, sensitive data handling
- **API Availability:** `/api/v2.0/config/save` (limited)
- **Priority:** **P1 (Important)**
- **Commands:**
  - `truenas-cli export --output truenas-config.json` - Full system export
  - `truenas-cli export --scope datasets --output datasets.yaml` - Partial export
  - `truenas-cli import truenas-config.json --dry-run` - Preview import
  - `truenas-cli import truenas-config.json --apply` - Restore config
- **Notes:** Must redact secrets, support selective import/export

#### 3.5 Event Hooks and Notifications
- **Description:** Execute custom scripts on events (webhook-style)
- **User Value:** **Medium** - Enables custom automation workflows
- **Implementation Effort:** **Complex** - Event subscription, webhook delivery
- **API Availability:** May need polling or websocket connection
- **Priority:** **P2 (Nice-to-have)**
- **Features:**
  - `truenas-cli hook add --event "pool.scrub.complete" --exec "./notify.sh"`
  - Events: scrub complete, disk failure, alert created, replication finished
  - Supports webhooks, email, scripts
- **Notes:** May require long-running daemon process

#### 3.6 CI/CD Integration Helpers
- **Description:** Commands optimized for CI/CD pipelines
- **User Value:** **Medium** - Easier GitLab/GitHub Actions integration
- **Implementation Effort:** **Simple** - Wrapper commands, documentation
- **API Availability:** Uses existing commands
- **Priority:** **P2 (Nice-to-have)**
- **Features:**
  - `truenas-cli ci preflight` - Validate environment (API key, connectivity)
  - `truenas-cli ci plan` - Generate execution plan (like Terraform)
  - `truenas-cli ci apply --plan plan.json` - Execute saved plan
  - Exit codes optimized for CI (0=success, 1=error, 2=auth, 3=config, 10=no changes)
  - JSON output by default in CI mode
- **Notes:** Examples for GitHub Actions, GitLab CI, Jenkins

---

### Category 4: Advanced Features

Sophisticated capabilities for power users and complex environments.

#### 4.1 Real-time Monitoring Dashboard
- **Description:** Live terminal dashboard with key metrics
- **User Value:** **Medium** - Quick system overview
- **Implementation Effort:** **Medium** - Rich Live display, metric aggregation
- **API Availability:** Uses existing reporting APIs
- **Priority:** **P2 (Nice-to-have)**
- **Features:**
  - `truenas-cli dashboard` - Full-screen live dashboard
  - Shows: pool status, disk temps, network I/O, top processes, alerts
  - Interactive (keyboard navigation to drill down)
  - Configurable refresh interval and panels
- **Notes:** Inspired by `htop`, `k9s` for Kubernetes

#### 4.2 Advanced Query Language
- **Description:** Powerful filtering beyond simple key=value
- **User Value:** **Medium** - Complex data extraction
- **Implementation Effort:** **Complex** - Query parser, execution engine
- **API Availability:** N/A - Client-side processing
- **Priority:** **P2 (Nice-to-have)**
- **Examples:**
  - `truenas-cli dataset list --query "used > 1TB AND compression != 'lz4'"`
  - `truenas-cli pool list --query "status = 'ONLINE' AND healthy = true AND allocated/size > 0.8"`
  - JMESPath or custom DSL for JSON querying
- **Notes:** Could use JMESPath library for JSON querying

#### 4.3 Performance Profiling Tools
- **Description:** Analyze and optimize TrueNAS performance
- **User Value:** **Low-Medium** - For performance troubleshooting
- **Implementation Effort:** **Complex** - Statistical analysis, recommendations
- **API Availability:** `/api/v2.0/reporting/*`
- **Priority:** **P2 (Nice-to-have)**
- **Commands:**
  - `truenas-cli perf analyze` - Comprehensive performance report
  - `truenas-cli perf hotspots` - Identify bottlenecks
  - `truenas-cli perf recommend` - Suggest optimizations
  - `truenas-cli perf benchmark` - Run standard benchmarks
- **Notes:** Requires significant domain expertise to provide valuable insights

#### 4.4 Capacity Planning Tools
- **Description:** Predict storage exhaustion, plan expansions
- **User Value:** **Medium** - Proactive capacity management
- **Implementation Effort:** **Medium** - Trend analysis, projections
- **API Availability:** Uses reporting APIs
- **Priority:** **P2 (Nice-to-have)**
- **Features:**
  - `truenas-cli capacity forecast --days 90` - Project when pools fill up
  - `truenas-cli capacity trends` - Historical usage patterns
  - `truenas-cli capacity optimize` - Suggest compression/dedup savings
  - Export reports for management
- **Notes:** Machine learning could improve predictions

#### 4.5 Multi-System Management
- **Description:** Manage multiple TrueNAS systems simultaneously
- **User Value:** **Medium** - For users with multiple appliances
- **Implementation Effort:** **Medium** - Parallel execution, aggregation
- **API Availability:** Uses existing multi-profile support
- **Priority:** **P2 (Nice-to-have)**
- **Features:**
  - `truenas-cli --all-profiles pool list` - Query all systems
  - `truenas-cli exec --profiles prod1,prod2 "snapshot create {pool}/data@backup"`
  - Aggregate views across systems
  - Parallel execution with progress tracking
- **Notes:** Security concern - must prevent accidental mass changes

---

### Category 5: Developer Experience

Features to enhance CLI development, testing, and extensibility.

#### 5.1 Plugin System
- **Description:** Allow third-party commands and extensions
- **User Value:** **Low** - For ecosystem development
- **Implementation Effort:** **Complex** - Plugin architecture, sandboxing
- **API Availability:** N/A - Framework enhancement
- **Priority:** **P2 (Nice-to-have)**
- **Design:**
  - Plugins as Python packages in `~/.truenas-cli/plugins/`
  - Plugin discovery via entry points
  - Isolated namespace for plugin commands
  - Security considerations (code signing, permissions)
- **Notes:** Low priority but enables community contributions

#### 5.2 Mock/Sandbox Mode
- **Description:** Run commands against mock API for testing
- **User Value:** **Medium** - Safe script development and testing
- **Implementation Effort:** **Medium** - Mock API implementation
- **API Availability:** N/A - Testing infrastructure
- **Priority:** **P2 (Nice-to-have)**
- **Features:**
  - `truenas-cli --mock dataset create tank/test` - Simulated execution
  - `truenas-cli mock snapshot` - Start mock API server
  - Pre-populated test scenarios
  - Record/replay mode for integration tests
- **Notes:** Valuable for CI/CD testing without real TrueNAS instance

#### 5.3 Enhanced Testing Utilities
- **Description:** Built-in tools for testing CLI scripts
- **User Value:** **Low-Medium** - Quality assurance
- **Implementation Effort:** **Simple** - Documentation and examples
- **API Availability:** N/A - Testing tools
- **Priority:** **P2 (Nice-to-have)**
- **Tools:**
  - `truenas-cli test validate-script myscript.sh` - Lint CLI usage
  - Test fixtures and example data
  - Integration test helpers
  - Load testing utilities
- **Notes:** Reduces barrier for contribution

#### 5.4 Debug and Trace Mode
- **Description:** Enhanced debugging beyond -vvv
- **User Value:** **Low** - Development and troubleshooting
- **Implementation Effort:** **Simple** - Enhanced logging
- **API Availability:** N/A - Client enhancement
- **Priority:** **P2 (Nice-to-have)**
- **Features:**
  - `truenas-cli --trace` - Full request/response logging
  - `truenas-cli --profile-performance` - Timing breakdown
  - `truenas-cli --dump-state` - Save complete client state for bug reports
  - OpenTelemetry integration for distributed tracing
- **Notes:** Mostly for developers, not end users

---

## Prioritized Roadmap

### Phase 1: Quick Wins (High Value, Low-Medium Effort)
**Timeline:** 2-3 months
**Goal:** Address critical gaps in core administrative functions

1. **Service Management** (P0, Simple, 2 weeks)
   - List, start, stop, restart, enable/disable services
   - Critical for automation workflows
   - Low implementation complexity

2. **Job Monitoring** (P1, Medium, 3 weeks)
   - List, status, wait, logs for background jobs
   - Enables automation scripts to track operations
   - Medium complexity due to state tracking

3. **User Management Basics** (P0, Medium, 3 weeks)
   - User and group CRUD operations
   - Set passwords and SSH keys
   - Essential security automation

4. **Bulk Operations** (P1, Medium, 2 weeks)
   - Pattern-based snapshot deletion
   - Bulk dataset creation
   - High value for large environments

5. **Interactive Wizards** (P1, Medium, 3 weeks)
   - Pool creation wizard
   - Share setup wizard
   - Significantly improves UX

**Phase 1 Deliverables:**
- 3 new command groups (service, job, user)
- 15-20 new commands
- 2-3 interactive wizards
- Updated documentation with automation examples

---

### Phase 2: Core Expansions (High Value, Medium-Complex Effort)
**Timeline:** 4-6 months
**Goal:** Complete essential TrueNAS administration capabilities

1. **Replication Management** (P1, Complex, 4 weeks)
   - Create, run, monitor replication tasks
   - Critical for backup/DR workflows
   - Complex due to SSH, scheduling, snapshots

2. **Disk Management** (P1, Medium, 3 weeks)
   - Disk listing with detailed info
   - SMART test execution and monitoring
   - Proactive hardware management

3. **Template System** (P1, Medium, 3 weeks)
   - Save/apply resource templates
   - Variable substitution
   - Foundation for IaC workflows

4. **Export/Import Configuration** (P1, Medium, 3 weeks)
   - Full and partial system exports
   - Configuration restore with dry-run
   - Disaster recovery capability

5. **Group Management Advanced** (P0, Medium, 2 weeks)
   - Complete user/group implementation
   - Member management, advanced permissions
   - Completes access control automation

6. **Dry-Run Mode** (P1, Medium, 2 weeks)
   - Preview changes before applying
   - Safety for automation
   - Client-side validation where API lacks support

**Phase 2 Deliverables:**
- 3 new command groups (replication, disk, template)
- 20-25 new commands
- Configuration backup/restore capability
- Comprehensive automation guide

---

### Phase 3: Advanced Features (Medium-High Value, Complex Effort)
**Timeline:** 4-6 months
**Goal:** Differentiate CLI with advanced capabilities

1. **Real-time Dashboard** (P2, Medium, 4 weeks)
   - Interactive terminal dashboard
   - Live metrics and alerts
   - Inspired by htop/k9s

2. **iSCSI Management** (P2, Complex, 5 weeks)
   - Target, extent, portal, initiator management
   - Important for virtualization
   - Complex multi-component system

3. **Cloud Sync Tasks** (P2, Medium, 3 weeks)
   - Manage cloud synchronization
   - Support major providers
   - Hybrid cloud use cases

4. **Network Configuration** (P2, Medium, 3 weeks)
   - Interface, route, DNS management
   - Initial setup automation
   - Requires careful validation

5. **Advanced Query Language** (P2, Complex, 4 weeks)
   - Complex filtering expressions
   - JMESPath integration
   - Power user feature

6. **Multi-System Management** (P2, Medium, 3 weeks)
   - Execute across multiple profiles
   - Aggregate views
   - Fleet management

**Phase 3 Deliverables:**
- 4 new command groups (iscsi, cloudsync, network, dashboard)
- 25-30 new commands
- Advanced monitoring capabilities
- Fleet management guide

---

### Phase 4: Future Considerations (Lower Priority)
**Timeline:** 6-12 months
**Goal:** Polish, extensibility, and specialized features

1. **Update Management** (P2, Medium, 3 weeks)
   - Check, download, apply updates
   - Rollback capability
   - Automated maintenance

2. **Certificate Management** (P2, Medium, 2 weeks)
   - SSL/TLS cert lifecycle
   - CSR generation
   - Security automation

3. **Performance Profiling** (P2, Complex, 5 weeks)
   - Analyze performance
   - Identify bottlenecks
   - Optimization recommendations

4. **Capacity Planning** (P2, Medium, 3 weeks)
   - Usage forecasting
   - Trend analysis
   - Expansion recommendations

5. **Plugin System** (P2, Complex, 6 weeks)
   - Third-party extensions
   - Plugin marketplace
   - Ecosystem development

6. **Enhanced Debugging** (P2, Simple, 2 weeks)
   - Trace mode
   - Performance profiling
   - State dumps

**Phase 4 Deliverables:**
- 3-4 new command groups
- 15-20 new commands
- Plugin architecture
- Performance and capacity tools

---

## Implementation Notes

### Technical Dependencies and Prerequisites

#### Required Python Libraries (New)
- **Interactive prompts:** `questionary` or `inquirer` for wizards
- **Progress tracking:** `tqdm` for progress bars (already have Rich, could use that)
- **Query language:** `jmespath` for advanced filtering
- **Template engine:** `jinja2` for template system
- **SSH operations:** `paramiko` for replication management
- **Diff utilities:** `deepdiff` for configuration comparison

#### API Compatibility
- **Target Version:** TrueNAS SCALE 24.04+ (REST API v2.0)
- **Deprecated APIs:** Note that REST API is deprecated in 25.04, being replaced by WebSocket API
  - **Migration Path:** Monitor TrueNAS API Client development, plan migration to WebSocket
  - **Timeline:** REST API removal planned for 26.04 (Q2 2025)
  - **Action:** This is a **CRITICAL** consideration - may need to refactor to WebSocket sooner

#### Architecture Considerations
1. **Async Support:** Consider adding async methods for long operations (replication, scrubs)
2. **State Management:** Job monitoring requires tracking operation state
3. **Error Aggregation:** Bulk operations need comprehensive error collection
4. **Template Storage:** Decide on template format (YAML vs JSON) and storage location
5. **Plugin Architecture:** Define clear plugin API boundaries and security model

### Potential Challenges

#### 1. API Deprecation (CRITICAL)
**Challenge:** TrueNAS is deprecating REST API in favor of WebSocket API
**Impact:** May require significant refactoring
**Mitigation:**
- Monitor TrueNAS API Client project: https://github.com/truenas/api_client
- Plan dual API support (REST + WebSocket)
- Implement abstraction layer for easy migration
- Timeline: Begin planning migration Q1 2025

#### 2. Complex Multi-Component Operations
**Challenge:** Features like iSCSI have many interdependent resources
**Impact:** Complex implementation, user confusion
**Mitigation:**
- Implement guided wizards for complex setups
- Provide validation before applying changes
- Clear documentation with examples

#### 3. Destructive Operations Safety
**Challenge:** Network config, updates can brick systems
**Impact:** Support burden, user data loss
**Mitigation:**
- Multiple confirmation prompts
- Mandatory dry-run for dangerous operations
- Clear rollback procedures
- Connection test before applying network changes

#### 4. Performance with Large Datasets
**Challenge:** Systems with 1000+ datasets, snapshots
**Impact:** Slow list operations, memory usage
**Mitigation:**
- Implement pagination for list commands
- Add --limit flag for large result sets
- Stream processing for bulk operations
- Consider caching for frequently accessed data

#### 5. Secret Management
**Challenge:** Storing cloud credentials, SSH keys securely
**Impact:** Security vulnerabilities
**Mitigation:**
- Use system keyring (keyring library)
- Encrypt sensitive config files
- Support environment variables
- Clear documentation on security best practices

#### 6. Cross-Platform Compatibility
**Challenge:** Maintaining compatibility across Linux, macOS, Windows
**Impact:** Platform-specific bugs
**Mitigation:**
- Comprehensive CI testing on all platforms
- Abstract platform-specific operations
- Use pathlib for filesystem operations

### Resource Requirements

#### Development Team
**Recommended Team Composition:**
- 1-2 Senior Python developers (CLI architecture, API integration)
- 1 TrueNAS/ZFS expert (domain knowledge, testing)
- 1 Technical writer (documentation, examples)
- 1 QA engineer (testing, automation)

**Timeline Estimates:**
- Phase 1: 2-3 months (1 developer)
- Phase 2: 4-6 months (2 developers)
- Phase 3: 4-6 months (2 developers)
- Phase 4: 6-12 months (1-2 developers)

#### Infrastructure
- **Test Environment:** 2-3 TrueNAS SCALE instances (dev, staging, prod-like)
- **CI/CD:** GitHub Actions or GitLab CI for automated testing
- **Documentation:** Sphinx or MkDocs for comprehensive docs
- **Demo Environment:** Public demo instance for examples and testing

### Testing Considerations

#### Test Coverage Goals
- **Unit Tests:** 80%+ coverage for business logic
- **Integration Tests:** All API endpoints with mock server
- **E2E Tests:** Critical workflows (pool creation, replication setup)
- **Performance Tests:** Large dataset handling (1000+ items)
- **Security Tests:** Permission checks, input validation

#### Test Infrastructure
1. **Mock API Server:** Simulate TrueNAS API for fast testing
2. **Docker Test Environment:** Spin up test TrueNAS instances
3. **Test Fixtures:** Pre-populated data for various scenarios
4. **Regression Tests:** Prevent breaking changes
5. **Load Tests:** Verify performance with large datasets

#### Testing Challenges
- **Destructive Operations:** Need isolated test instances
- **Long Operations:** Scrubs, replication take time
- **State Dependencies:** Tests must handle existing system state
- **Error Conditions:** Simulate network failures, API errors

---

## Recommendations

### Top 5 Immediate Actions

#### 1. Implement Service Management (2-3 weeks)
**Why:** Critical gap affecting nearly all automation workflows. Administrators need to configure services then enable them programmatically.
**Approach:**
- Start with basic start/stop/status for top 5 services (NFS, SMB, SSH, iSCSI, SNMP)
- Add enable/disable for boot startup
- Expand to remaining services
- Follow existing command patterns for consistency

#### 2. Add User and Group Management (3-4 weeks)
**Why:** Access control automation is essential for onboarding/offboarding, compliance.
**Approach:**
- Implement user CRUD first (list, create, update, delete, info)
- Add password and SSH key management
- Implement group CRUD
- Add group membership operations
- Thorough testing of UID/GID handling

#### 3. Develop Job Monitoring (2-3 weeks)
**Why:** Enables automation scripts to wait for long operations (scrubs, replication).
**Approach:**
- List active and recent jobs
- Get job status with progress percentage
- Implement wait command (blocking until completion)
- Add job logs viewing
- Handle job failures gracefully

#### 4. Plan WebSocket API Migration (4-6 weeks research + planning)
**Why:** REST API is deprecated, removal planned for TrueNAS 26.04 (Q2 2025). This is **CRITICAL**.
**Approach:**
- Study TrueNAS API Client: https://github.com/truenas/api_client
- Evaluate WebSocket vs REST tradeoffs
- Design abstraction layer for dual support
- Create migration plan with timeline
- Consider collaborating with TrueNAS team

#### 5. Create Comprehensive Documentation and Examples (Ongoing)
**Why:** Quality documentation drives adoption and reduces support burden.
**Approach:**
- Automation cookbook with real-world scenarios
- Integration guides (Ansible, Terraform, GitHub Actions)
- Video tutorials for complex workflows
- API reference documentation
- Troubleshooting guide

### Strategic Recommendations

#### A. Focus on Automation Excellence
The CLI's primary value is **automation**. Every feature should be evaluated through this lens:
- Is it scriptable?
- Does it support CI/CD integration?
- Can it be templated?
- Does it provide machine-readable output?

**Action Items:**
- Add `--json` flag to all commands (already mostly done)
- Standardize exit codes across all commands
- Develop CI/CD integration examples
- Create Ansible module wrapper

#### B. Differentiate from Web UI
The CLI should excel where the web UI is weak:
- **Bulk operations** - Change 100 datasets at once
- **Complex filtering** - Find all snapshots > 30 days with specific pattern
- **Templating** - Apply consistent configs across resources
- **Multi-system management** - Operate on multiple TrueNAS instances
- **GitOps workflows** - Version control configuration

**Action Items:**
- Prioritize bulk operations and templates
- Develop advanced query capabilities
- Create IaC examples (Terraform-like workflows)

#### C. Build Community and Ecosystem
A successful CLI needs an active community:
- Plugin system for extensibility
- Clear contribution guidelines
- Example scripts and templates
- Integration with popular tools (Ansible, Terraform, Kubernetes operators)

**Action Items:**
- Publish to PyPI for easy installation
- Create awesome-truenas-cli repository
- Engage with TrueNAS community forums
- Develop integration examples

#### D. Prepare for WebSocket API Migration
This is the **highest strategic priority**:
- REST API deprecated in 25.04
- Removal planned for 26.04 (Q2 2025)
- Significant architectural changes required

**Action Items:**
- Q1 2025: Research and design migration approach
- Q2 2025: Implement dual API support
- Q3 2025: Migrate primary codebase to WebSocket
- Q4 2025: Deprecate REST API support

#### E. Maintain High Quality Standards
Quality over quantity:
- Comprehensive test coverage (80%+)
- Clear, helpful error messages
- Consistent command patterns
- Safe defaults (confirmations for destructive ops)
- Excellent documentation

**Action Items:**
- Enforce test coverage requirements in CI
- User testing sessions for new features
- Regular usability reviews
- Documentation-first development

### Metrics for Success

#### Adoption Metrics
- Downloads per month (PyPI)
- GitHub stars and forks
- Active users (telemetry opt-in)
- Community contributions

#### Quality Metrics
- Test coverage (target: 80%+)
- Bug report rate
- Time to close issues
- Documentation completeness

#### Feature Metrics
- API endpoint coverage (target: 70%+)
- Command count vs web UI feature parity
- Automation use cases supported

#### User Satisfaction
- GitHub issue sentiment analysis
- User survey scores
- Support ticket volume
- Feature request themes

---

## Conclusion

The TrueNAS CLI has a **solid foundation** with excellent coverage of core storage operations. The expansion opportunities identified in this analysis would transform it from a **storage-focused tool** to a **comprehensive TrueNAS administration platform**.

**Key Takeaways:**

1. **Critical Gaps:** Service management, user/group management, and replication are the most important missing features affecting real-world automation workflows.

2. **Quick Wins:** 5-6 high-value features can be implemented in 2-3 months with medium effort, delivering immediate user value.

3. **Strategic Imperative:** WebSocket API migration is the highest priority technical challenge, requiring planning and execution in 2025.

4. **Differentiation Opportunity:** Advanced features like bulk operations, templates, and multi-system management would significantly differentiate the CLI from the web UI.

5. **Ecosystem Potential:** A plugin system and strong community engagement could create a vibrant ecosystem around the CLI.

**Recommended Next Steps:**

1. **Immediate (Month 1):** Implement service management and job monitoring
2. **Short-term (Months 2-3):** Complete user/group management, add bulk operations
3. **Medium-term (Months 4-6):** Develop replication management, template system, export/import
4. **Strategic (Q1-Q2 2025):** Plan and begin WebSocket API migration
5. **Ongoing:** Continuously improve documentation, examples, and community engagement

With focused execution on this roadmap, the TrueNAS CLI can become the **de facto standard** for TrueNAS automation and a critical tool for system administrators managing TrueNAS SCALE deployments.

---

**Document Version:** 1.0
**Last Updated:** January 2025
**Next Review:** March 2025 (post Phase 1 completion)
