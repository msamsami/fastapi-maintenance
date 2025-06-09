# Command Line Interface

FastAPI Maintenance provides a command-line interface (CLI) for managing maintenance mode from the terminal. This is particularly useful for deployment scripts, system administration, and monitoring tasks.

## Installation

The CLI is available when you [install the package](./install.md#optional-dependencies) with the `cli` extra:

```bash
pip install fastapi-maintenance[cli]
```

The CLI command becomes available as `fastapi-maintenance` in your terminal.

## Quick Start

Check if the CLI is working:

```bash
fastapi-maintenance --version
```

Check the current maintenance mode status:

```bash
fastapi-maintenance status
```

## Commands

### `status` - Check Maintenance Mode Status

The `status` command allows you to check the current maintenance mode state using different backends.

#### Basic Usage

```bash
# Check status using the default backend
fastapi-maintenance status
```

This will show output like:
```
🟢 Maintenance mode is OFF (using default backend)
```

or

```
🔴 Maintenance mode is ON (using default backend)
```

#### Backend Options

You can specify different backends to check the maintenance mode status:

##### Environment Variable Backend

```bash
# Check status using environment variable backend
fastapi-maintenance status --backend env
```

Use a custom environment variable name:

```bash
# Check status using custom environment variable
fastapi-maintenance status --backend env --var-name MY_MAINTENANCE_FLAG
```

##### File Backend

```bash
# Check status using file backend
fastapi-maintenance status --backend file --file-path /tmp/maintenance.txt
```

## Command Reference

### Global Options

- `--version`: Show the package version and exit
- `--help`: Show help message and exit

### `status` Command Options

- `--backend`: Backend to use (`env` or `file`)
- `--var-name`: Environment variable name (for env backend, default: `FASTAPI_MAINTENANCE_MODE`)
- `--file-path`: Path to the maintenance mode state file (required for file backend)

## Examples

### Development Workflow

Check maintenance status during development:

```bash
# Check current status
fastapi-maintenance status

# Check status with specific backend
fastapi-maintenance status --backend file --file-path ./maintenance.txt
```

### Production Monitoring

Use the CLI in monitoring scripts:

```bash
#!/bin/bash

# Check maintenance status and act accordingly
if fastapi-maintenance status --backend env --var-name PROD_MAINTENANCE_MODE | grep -q "ON"; then
    echo "Application is in maintenance mode"
    exit 1
else
    echo "Application is running normally"
    exit 0
fi
```

### Deployment Scripts

Integrate with deployment automation:

```bash
#!/bin/bash

# Check if maintenance mode is active before deployment
echo "Checking maintenance mode status..."
fastapi-maintenance status --backend file --file-path /app/maintenance.txt

# The exit code can be used in conditional logic
if [ $? -eq 0 ]; then
    echo "Status check completed successfully"
else
    echo "Failed to check maintenance status"
    exit 1
fi
```

### Docker Integration

Use in Docker health checks or initialization scripts:

```dockerfile
# In your Dockerfile
COPY maintenance_check.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/maintenance_check.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD /usr/local/bin/maintenance_check.sh
```

```bash
#!/bin/bash
# maintenance_check.sh
fastapi-maintenance status --backend env
```
