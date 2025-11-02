# PyQuizHub Configuration Guide# Configuration Guide



## OverviewPyQuizHub uses a flexible configuration system based on YAML files with environment variable overrides. The system automatically discovers configuration files and validates all settings on startup.



PyQuizHub uses a flexible, layered configuration system that supports both local development and production deployment. The configuration system is built on **Pydantic Settings** and supports:## Table of Contents



- YAML configuration files for defaults- [Quick Start](#quick-start)

- Environment variable overrides- [Configuration File Locations](#configuration-file-locations)

- Automatic validation- [Configuration Structure](#configuration-structure)

- Type safety- [Environment Variables](#environment-variables)

- [Deployment Scenarios](#deployment-scenarios)

## Configuration Layers- [Validation](#validation)

- [Troubleshooting](#troubleshooting)

Configuration is loaded in order of priority (highest to lowest):

## Quick Start

1. **Environment Variables** - `PYQUIZHUB_*` prefixed variables

2. **`.env` File** - Optional file for environment-specific settings### Local Development

3. **`config.yaml`** - Base configuration with sensible defaults

1. Copy the default configuration:

## File Locations```bash

cp pyquizhub/config/config.yaml config.yaml

### config.yaml```

The base configuration file should be placed in one of these locations (searched in order):

2. Edit `config.yaml` to match your needs:

1. Path specified in `PYQUIZHUB_CONFIG_PATH` environment variable```yaml

2. `./config.yaml` (project root)storage:

3. `pyquizhub/config/config.yaml` (package location - not recommended for custom configs)  type: "file"  # or "sql"

  file:

### .env File    base_dir: ".pyquizhub"

Optional file for environment-specific overrides. Place in project root.  

api:

## Configuration Sections  host: "0.0.0.0"

  port: 8000

### Storage```



Controls where quiz data is stored.3. Run the application:

```bash

**YAML:**poetry run python -m pyquizhub.main

```yaml```

storage:

  type: "file"  # Options: "file" or "sql"### Docker Deployment

  file:

    base_dir: ".pyquizhub"1. Copy the environment template:

  sql:```bash

    connection_string: "sqlite:///pyquizhub.db"cp .env.example .env

``````



**Environment Variables:**2. Edit `.env` with your settings:

```bash```env

PYQUIZHUB_STORAGE__TYPE=sqlPYQUIZHUB_STORAGE__TYPE=sql

PYQUIZHUB_STORAGE__FILE__BASE_DIR=.pyquizhubPYQUIZHUB_STORAGE__SQL__CONNECTION_STRING=postgresql://user:pass@db:5432/pyquizhub

PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING=postgresql://user:pass@localhost/pyquizhub```

```

3. Start with Docker Compose:

**Storage Types:**```bash

- `file`: Stores data as JSON files in the filesystem. Good for development and small deployments.docker-compose up -d

- `sql`: Stores data in a SQL database (PostgreSQL, SQLite). Required for production.```



### API## Configuration File Locations



Controls the API server settings.The configuration system searches for `config.yaml` in the following order (first found is used):



**YAML:**1. **`PYQUIZHUB_CONFIG_PATH` environment variable** - Explicit path takes highest priority

```yaml2. **`/app/config/config.yaml`** - Docker primary location

api:3. **`/app/config.docker.yaml`** - Docker alternative config

  base_url: "http://127.0.0.1:8000"4. **`./config.docker.yaml`** - Docker config in current directory

  host: "0.0.0.0"5. **`./config/config.yaml`** - Mounted config directory

  port: 80006. **`./config.yaml`** - Project root

```7. **`pyquizhub/config/config.yaml`** - Package default location



**Environment Variables:**### Setting Explicit Path

```bash

PYQUIZHUB_API__BASE_URL=http://api:8000```bash

PYQUIZHUB_API__HOST=0.0.0.0export PYQUIZHUB_CONFIG_PATH=/path/to/my/config.yaml

PYQUIZHUB_API__PORT=8000python -m pyquizhub.main

``````



### Security## Configuration Structure



Controls authentication tokens.### Complete Configuration Example



**YAML:**```yaml

```yaml# Storage Configuration

security:storage:

  use_tokens: true  type: "file"  # Options: "file" or "sql"

  admin_token_env: "PYQUIZHUB_ADMIN_TOKEN"  

  creator_token_env: "PYQUIZHUB_CREATOR_TOKEN"  # File storage settings (used when type: "file")

  user_token_env: "PYQUIZHUB_USER_TOKEN"  file:

```    base_dir: ".pyquizhub"  # Directory for storing quiz data

  

**Environment Variables:**  # SQL storage settings (used when type: "sql")

```bash  sql:

PYQUIZHUB_ADMIN_TOKEN=your-secure-token-here    connection_string: "sqlite:///pyquizhub.db"

PYQUIZHUB_CREATOR_TOKEN=your-secure-token-here    # Examples:

PYQUIZHUB_USER_TOKEN=your-secure-token-here    # PostgreSQL: "postgresql://user:password@localhost:5432/pyquizhub"

```    # MySQL: "mysql+pymysql://user:password@localhost:3306/pyquizhub"



**Generating Secure Tokens:**# API Configuration

```bashapi:

python -c "import secrets; print(secrets.token_urlsafe(32))"  base_url: "http://127.0.0.1:8000"  # Public URL for API

```  host: "0.0.0.0"                     # Host to bind server to

  port: 8000                           # Port number (1-65535)

### Logging

# Security Configuration

Controls logging behavior. This is typically left in `config.yaml` as it rarely changes between environments.security:

  use_tokens: true  # Enable/disable token authentication

**YAML:**  

```yaml  # Environment variable names for tokens

logging:  admin_token_env: "PYQUIZHUB_ADMIN_TOKEN"

  version: 1  creator_token_env: "PYQUIZHUB_CREATOR_TOKEN"

  disable_existing_loggers: false  user_token_env: "PYQUIZHUB_USER_TOKEN"

  formatters:

    standard:# Logging Configuration

      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"logging:

  handlers:  version: 1

    console:  disable_existing_loggers: false

      class: logging.StreamHandler  

      level: INFO  formatters:

      formatter: standard    standard:

  root:      format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    level: INFO      datefmt: "%Y-%m-%d %H:%M:%S"

    handlers: [console]  

```  handlers:

    console:

## Usage Scenarios      class: logging.StreamHandler

      level: INFO

### Scenario 1: Local Development (Default)      formatter: standard

      stream: ext://sys.stdout

Just run the application - no configuration needed!    

    file:

```bash      class: logging.handlers.RotatingFileHandler

poetry run uvicorn pyquizhub.main:app --reload      level: DEBUG

```      formatter: standard

      filename: .pyquizhub/logs/pyquizhub.log

Uses:      maxBytes: 1048576  # 1MB

- File storage in `.pyquizhub/` directory      backupCount: 5

- API on `http://127.0.0.1:8000`  

- No authentication required  root:

    level: DEBUG

### Scenario 2: Local Development with PostgreSQL    handlers: [console, file]

  

Create a `.env` file:  loggers:

```bash    pyquizhub:

PYQUIZHUB_STORAGE__TYPE=sql      level: DEBUG

PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING=postgresql://user:pass@localhost:5432/pyquizhub      handlers: [console, file]

```      propagate: false

```

Run:

```bash### Configuration Sections

poetry run uvicorn pyquizhub.main:app --reload

```#### Storage



### Scenario 3: Docker DeploymentControls how quiz data is stored.



1. Copy `.env.example` to `.env`:| Option | Type | Default | Description |

```bash|--------|------|---------|-------------|

cp .env.example .env| `storage.type` | string | `"file"` | Storage backend: `"file"` or `"sql"` |

```| `storage.file.base_dir` | string | `".pyquizhub"` | Directory for file storage |

| `storage.sql.connection_string` | string | `"sqlite:///pyquizhub.db"` | SQLAlchemy connection URL |

2. Edit `.env`:

```bash#### API

PYQUIZHUB_STORAGE__TYPE=sql

PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING=postgresql://pyquizhub:pyquizhub@db:5432/pyquizhubConfigures the FastAPI server.

PYQUIZHUB_API__BASE_URL=http://api:8000

PYQUIZHUB_ADMIN_TOKEN=<generate-secure-token>| Option | Type | Default | Description |

PYQUIZHUB_CREATOR_TOKEN=<generate-secure-token>|--------|------|---------|-------------|

PYQUIZHUB_USER_TOKEN=<generate-secure-token>| `api.base_url` | string | `"http://127.0.0.1:8000"` | Public URL for the API |

| `api.host` | string | `"0.0.0.0"` | Host address to bind to |

POSTGRES_DB=pyquizhub| `api.port` | integer | `8000` | Port number (1-65535) |

POSTGRES_USER=pyquizhub

POSTGRES_PASSWORD=<change-this>#### Security

```

Manages authentication and tokens.

3. Run:

```bash| Option | Type | Default | Description |

docker-compose up -d|--------|------|---------|-------------|

```| `security.use_tokens` | boolean | `true` | Enable token authentication |

| `security.admin_token_env` | string | `"PYQUIZHUB_ADMIN_TOKEN"` | Env var name for admin token |

### Scenario 4: Production Deployment| `security.creator_token_env` | string | `"PYQUIZHUB_CREATOR_TOKEN"` | Env var name for creator token |

| `security.user_token_env` | string | `"PYQUIZHUB_USER_TOKEN"` | Env var name for user token |

For production, use environment variables set directly in your deployment environment (Kubernetes secrets, systemd environment files, etc.) rather than `.env` files.

#### Logging

Example systemd service file:

```iniPython logging configuration (uses `logging.config.dictConfig` format).

[Service]

Environment="PYQUIZHUB_STORAGE__TYPE=sql"See [Python logging documentation](https://docs.python.org/3/library/logging.config.html) for full options.

Environment="PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING=postgresql://user:pass@localhost/pyquizhub"

Environment="PYQUIZHUB_ADMIN_TOKEN=<secure-token>"## Environment Variables

Environment="PYQUIZHUB_CREATOR_TOKEN=<secure-token>"

Environment="PYQUIZHUB_USER_TOKEN=<secure-token>"Environment variables override configuration file values and use the format:

ExecStart=/usr/bin/poetry run uvicorn pyquizhub.main:app --host 0.0.0.0 --port 8000

``````

PYQUIZHUB_<SECTION>__<SUBSECTION>__<KEY>=value

## Environment Variable Syntax```



Environment variables use `__` (double underscore) to access nested configuration:**Note:** Use double underscores (`__`) to separate nested levels.



| Config Path | Environment Variable |### Common Environment Variables

|-------------|---------------------|

| `storage.type` | `PYQUIZHUB_STORAGE__TYPE` |```bash

| `storage.file.base_dir` | `PYQUIZHUB_STORAGE__FILE__BASE_DIR` |# Config file path

| `storage.sql.connection_string` | `PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING` |export PYQUIZHUB_CONFIG_PATH=/path/to/config.yaml

| `api.base_url` | `PYQUIZHUB_API__BASE_URL` |

| `api.host` | `PYQUIZHUB_API__HOST` |# Storage

| `api.port` | `PYQUIZHUB_API__PORT` |export PYQUIZHUB_STORAGE__TYPE=sql

export PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING="postgresql://user:pass@localhost/db"

## Troubleshooting

# API

### Config file not foundexport PYQUIZHUB_API__HOST=0.0.0.0

export PYQUIZHUB_API__PORT=8080

If you see an error about missing config file:export PYQUIZHUB_API__BASE_URL=https://api.example.com

1. Make sure `config.yaml` exists in project root OR

2. Set `PYQUIZHUB_CONFIG_PATH=/path/to/config.yaml` OR# Security

3. Use environment variables for all settings (no config file needed)export PYQUIZHUB_SECURITY__USE_TOKENS=true

export PYQUIZHUB_ADMIN_TOKEN=your-secure-admin-token

### Database connection errorsexport PYQUIZHUB_CREATOR_TOKEN=your-secure-creator-token

export PYQUIZHUB_USER_TOKEN=your-secure-user-token

For PostgreSQL:```

- Ensure database exists: `createdb pyquizhub`

- Check connection string format: `postgresql://user:password@host:port/database`### Type Conversion

- Verify credentials and network access

Environment variables are automatically converted to the appropriate type:

For SQLite:

- Use format: `sqlite:///path/to/database.db`- **Strings**: Used as-is

- Ensure write permissions to directory- **Integers**: `PYQUIZHUB_API__PORT=8000` → `8000` (integer)

- **Booleans**: `true`, `false`, `1`, `0`, `yes`, `no` (case-insensitive)

### Token authentication issues- **Nested objects**: Use `__` to separate levels



- Tokens must be set as environment variables (not in config.yaml)### Environment Variable Examples

- Generate secure random tokens for production

- Set all three tokens if `use_tokens: true````bash

# Simple string

## Best PracticesPYQUIZHUB_STORAGE__TYPE=sql



1. **Never commit `.env` files** - They contain secrets# Integer

2. **Use `.env.example`** - Commit this as a templatePYQUIZHUB_API__PORT=9000

3. **Generate strong tokens** - Use `secrets.token_urlsafe(32)` or longer

4. **Use SQL in production** - File storage is for development only# Boolean

5. **Set explicit `base_url`** - Especially in Docker/multi-service deploymentsPYQUIZHUB_SECURITY__USE_TOKENS=false

6. **Keep logging config in YAML** - It rarely changes between environments

7. **Validate early** - Run config validation before deployment# Nested value

PYQUIZHUB_STORAGE__FILE__BASE_DIR=/var/lib/pyquizhub

## Migration from Old Config

# Connection string with special characters

If you were using the old configuration system:PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING="postgresql://user:p%40ssw0rd@localhost:5432/db"

```

1. **Remove redundant files:**

   - Delete `config.docker.yaml`## Deployment Scenarios

   - Delete duplicate `config.yaml` files (keep only root one)

### Local Development (File Storage)

2. **Update docker-compose.yml:**

   - Remove config file volume mounts**config.yaml:**

   - Use `.env` file instead```yaml

storage:

3. **Create `.env` file:**  type: "file"

   ```bash  file:

   cp .env.example .env    base_dir: ".pyquizhub"

   # Edit with your settings

   ```api:

  base_url: "http://localhost:8000"

4. **Update environment variables:**  host: "127.0.0.1"

   - Old: `PYQUIZHUB_STORAGE_TYPE`  port: 8000

   - New: `PYQUIZHUB_STORAGE__TYPE`

   (Note the double underscore for nested keys)security:

  use_tokens: false  # Disable for local testing

logging:
  root:
    level: DEBUG
```

**Run:**
```bash
poetry run python -m pyquizhub.main
```

### Docker with PostgreSQL

**config.docker.yaml:**
```yaml
storage:
  type: "sql"
  sql:
    connection_string: "postgresql://pyquizhub:pyquizhub@db:5432/pyquizhub"

api:
  base_url: "http://api:8000"
  host: "0.0.0.0"
  port: 8000

logging:
  handlers:
    console:
      level: INFO
```

**.env:**
```env
PYQUIZHUB_ADMIN_TOKEN=your-secure-admin-token-here
PYQUIZHUB_CREATOR_TOKEN=your-secure-creator-token-here
PYQUIZHUB_USER_TOKEN=your-secure-user-token-here

POSTGRES_DB=pyquizhub
POSTGRES_USER=pyquizhub
POSTGRES_PASSWORD=pyquizhub
```

**Run:**
```bash
docker-compose up -d
```

### Production (Environment Variables Only)

For security, you can provide all configuration via environment variables without a config file:

```bash
export PYQUIZHUB_STORAGE__TYPE=sql
export PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING="postgresql://user:password@prod-db:5432/pyquizhub"
export PYQUIZHUB_API__BASE_URL="https://api.example.com"
export PYQUIZHUB_API__HOST=0.0.0.0
export PYQUIZHUB_API__PORT=8000
export PYQUIZHUB_SECURITY__USE_TOKENS=true
export PYQUIZHUB_ADMIN_TOKEN="$(openssl rand -hex 32)"
export PYQUIZHUB_CREATOR_TOKEN="$(openssl rand -hex 32)"
export PYQUIZHUB_USER_TOKEN="$(openssl rand -hex 32)"

poetry run uvicorn pyquizhub.main:app --host 0.0.0.0 --port 8000
```

### Kubernetes / Cloud Deployment

Use ConfigMaps and Secrets:

**configmap.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pyquizhub-config
data:
  config.yaml: |
    storage:
      type: "sql"
    api:
      host: "0.0.0.0"
      port: 8000
```

**secret.yaml:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: pyquizhub-secrets
type: Opaque
stringData:
  connection-string: "postgresql://user:password@db-service:5432/pyquizhub"
  admin-token: "your-admin-token"
  creator-token: "your-creator-token"
  user-token: "your-user-token"
```

**deployment.yaml:**
```yaml
env:
  - name: PYQUIZHUB_CONFIG_PATH
    value: /config/config.yaml
  - name: PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING
    valueFrom:
      secretKeyRef:
        name: pyquizhub-secrets
        key: connection-string
  - name: PYQUIZHUB_ADMIN_TOKEN
    valueFrom:
      secretKeyRef:
        name: pyquizhub-secrets
        key: admin-token
volumeMounts:
  - name: config
    mountPath: /config
volumes:
  - name: config
    configMap:
      name: pyquizhub-config
```

## Validation

The configuration system validates all settings on startup:

### Automatic Validation

- **Storage type**: Must be `"file"` or `"sql"`
- **Port numbers**: Must be between 1 and 65535
- **Required fields**: Checked automatically
- **Type checking**: Ensures correct data types

### Validation Errors

If configuration is invalid, you'll see clear error messages:

```
Configuration validation failed:
2 validation errors for AppSettings
storage.type
  Input should be 'file' or 'sql' (type=literal_error)
api.port
  Input should be less than or equal to 65535 (type=less_than_equal)
```

### Manual Validation

Test your configuration without starting the full application:

```python
from pyquizhub.config.settings_v2 import AppSettings

# This will validate and show errors
settings = AppSettings.from_yaml("config.yaml")
print("Configuration is valid!")
```

## Troubleshooting

### Config File Not Found

**Error:**
```
FileNotFoundError: No configuration file found. Searched in:
  - /app/config/config.yaml
  - ./config.yaml
  - pyquizhub/config/config.yaml
```

**Solutions:**
1. Create a `config.yaml` file in the project root
2. Set `PYQUIZHUB_CONFIG_PATH` to point to your config file
3. Copy the default config: `cp pyquizhub/config/config.yaml ./config.yaml`

### Invalid YAML Syntax

**Error:**
```
ValueError: Invalid YAML in configuration file: ...
```

**Solutions:**
1. Check YAML indentation (use spaces, not tabs)
2. Validate YAML syntax with: `python -c "import yaml; yaml.safe_load(open('config.yaml'))"`
3. Use a YAML linter or validator

### Environment Variables Not Working

**Issue:** Environment variables don't override config values

**Solutions:**
1. Check naming: Use `PYQUIZHUB_SECTION__KEY` format
2. Use double underscores (`__`) for nested values
3. Restart the application after setting env vars
4. Check for typos in environment variable names

### Database Connection Errors

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**
1. Verify connection string format
2. Check database server is running
3. Verify credentials and permissions
4. For Docker: ensure database service is started first

### Permission Denied for Log Files

**Error:**
```
PermissionError: [Errno 13] Permission denied: '.pyquizhub/logs/pyquizhub.log'
```

**Solutions:**
1. Create log directory: `mkdir -p .pyquizhub/logs`
2. Check file permissions
3. For Docker: mount a volume for logs

### Token Authentication Issues

**Issue:** API returns 401 Unauthorized

**Solutions:**
1. Verify tokens are set in environment:
   ```bash
   echo $PYQUIZHUB_ADMIN_TOKEN
   ```
2. Check `security.use_tokens` is `true` in config
3. Ensure you're passing tokens in requests:
   ```bash
   curl -H "Authorization: Bearer $PYQUIZHUB_ADMIN_TOKEN" http://localhost:8000/admin/...
   ```

## Advanced Topics

### Custom Configuration Profiles

Create environment-specific configs:

```bash
# Development
cp config.yaml config.dev.yaml
export PYQUIZHUB_CONFIG_PATH=config.dev.yaml

# Staging
cp config.yaml config.staging.yaml
export PYQUIZHUB_CONFIG_PATH=config.staging.yaml

# Production
cp config.yaml config.prod.yaml
export PYQUIZHUB_CONFIG_PATH=config.prod.yaml
```

### Configuration Inheritance

Start with a base config and override specific values:

**config.base.yaml:**
```yaml
storage:
  type: "file"
api:
  host: "0.0.0.0"
```

**Override with environment variables:**
```bash
export PYQUIZHUB_CONFIG_PATH=config.base.yaml
export PYQUIZHUB_STORAGE__TYPE=sql
export PYQUIZHUB_STORAGE__SQL__CONNECTION_STRING="postgresql://..."
```

### Accessing Configuration in Code

```python
from pyquizhub.config.settings import get_config_manager

# Get config manager
config = get_config_manager()

# Access values
storage_type = config.storage_type
port = config.api_port

# Get nested values
base_dir = config.get("storage.file.base_dir")

# Get with default
timeout = config.get("api.timeout", 30)

# Get entire config as dict
full_config = config.get_config()
```

### Migration from Old Config System

If you're upgrading from an older version:

1. **No code changes needed** - The new system is backward compatible
2. **Update imports** (optional): Change from `from pyquizhub.config.settings import get_logger` to `from pyquizhub.logging.setup import get_logger`
3. **Environment variables**: Continue working as before
4. **Config file structure**: Remains the same

## Reference

### Related Documentation

- [Getting Started Guide](getting_started.rst)
- [Deployment Guide](deployment.rst)
- [Architecture Overview](architecture.rst)

### Configuration API Reference

For programmatic access to configuration:

- `ConfigManager.get(key, default)` - Get config value
- `ConfigManager.load(path)` - Load configuration
- `ConfigManager.get_config()` - Get full config dict
- `AppSettings.from_yaml(path)` - Load and validate config

### Support

For issues or questions:
- GitHub Issues: https://github.com/imtambovtcev/pyquizhub/issues
- Documentation: See `docs/` directory
