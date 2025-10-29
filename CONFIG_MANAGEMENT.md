# Environment Configuration & Secrets Management

## Overview

This document explains how configuration and secrets are managed in the voting app. All sensitive values and environment-specific settings are now externalized via `.env` files and environment variables.

## File Structure

```
example-voting-app/
├── .env                  # Local environment configuration (DO NOT COMMIT)
├── .env.example          # Template for .env with safe defaults
├── docker-compose.yml    # Uses ${VAR} syntax to load from .env
├── vote/
│   └── app.py           # Reads REDIS_HOST, REDIS_PORT, OPTION_A, OPTION_B
├── result/
│   └── server.js        # Reads DB_HOST, DB_PORT, DB_NAME, POSTGRES_USER, POSTGRES_PASSWORD
├── worker/
│   └── Program.cs       # Reads DB_HOST, DB_PORT, DB_NAME, POSTGRES_USER, POSTGRES_PASSWORD, REDIS_HOST
└── .gitignore           # Prevents .env from being committed
```

## Environment Variables Reference

### PostgreSQL Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postgres` | PostgreSQL superuser username |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL superuser password |
| `DB_HOST` | `db` | PostgreSQL host (container name in Docker Compose) |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `postgres` | PostgreSQL database name |

### Redis Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis host (container name in Docker Compose) |
| `REDIS_PORT` | `6379` | Redis port |

### Voting App Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `OPTION_A` | `Cats` | Label for option A |
| `OPTION_B` | `Dogs` | Label for option B |
| `VOTE_PORT` | `80` | Port for vote service (container only) |

### Results App Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `RESULT_PORT` | `80` | Port for results service (container only) |

### Worker Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_LOG_LEVEL` | `info` | Logging level |

### Framework Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `development` | Flask environment (development/production) |
| `FLASK_DEBUG` | `1` | Flask debug mode (0/1) |
| `NODE_ENV` | `development` | Node environment (development/production) |

## Setup Instructions

### 1. Local Development

**First time setup:**

```bash
# Copy the example file to create your local .env
cp .env.example .env

# (Optional) Edit .env for local changes
# nano .env
```

**The `.env` file will be automatically loaded by Docker Compose:**

```bash
# Start services with environment variables from .env
docker compose up -d

# Services will read variables from .env
```

### 2. Staging/Production

**Create environment-specific `.env` files:**

```bash
# Staging configuration
cp .env.example .env.staging

# Production configuration  
cp .env.example .env.production
```

**Edit with secure values:**

```bash
# For production, use strong passwords:
POSTGRES_USER=postgres_prod
POSTGRES_PASSWORD=$(openssl rand -base64 32)
REDIS_PASSWORD=redis_prod_$(openssl rand -base64 16)
```

**Use with Docker Compose:**

```bash
# Staging
docker compose --env-file .env.staging up -d

# Production
docker compose --env-file .env.production up -d
```

### 3. Kubernetes / Container Orchestration

**Create secrets from .env:**

```bash
# Create a Kubernetes secret from .env file
kubectl create secret generic voting-app-config --from-env-file=.env.production

# Reference in deployment:
# env:
#   - name: POSTGRES_USER
#     valueFrom:
#       secretKeyRef:
#         name: voting-app-config
#         key: POSTGRES_USER
```

## Security Best Practices

### ✅ DO:
- ✅ Keep `.env` out of version control (listed in `.gitignore`)
- ✅ Use strong random passwords for production
  ```bash
  openssl rand -base64 32  # Generate random password
  ```
- ✅ Rotate secrets regularly
- ✅ Use `.env.example` as a template (safe to commit)
- ✅ Use Docker secrets or Kubernetes secrets in production
- ✅ Store `.env` files securely (restricted file permissions)
  ```bash
  chmod 600 .env  # Only owner can read
  ```
- ✅ Document required variables in `.env.example`

### ❌ DON'T:
- ❌ Commit `.env` file with real passwords
- ❌ Share `.env` files via email or chat
- ❌ Use same password for dev and production
- ❌ Log environment variables containing secrets
- ❌ Store plaintext secrets in repositories
- ❌ Hardcode credentials in source code

## Environment-Specific Configurations

### Development (.env)
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
FLASK_ENV=development
FLASK_DEBUG=1
NODE_ENV=development
```

### Staging (.env.staging)
```env
POSTGRES_USER=staging_user
POSTGRES_PASSWORD=<secure-random-password>
FLASK_ENV=production
FLASK_DEBUG=0
NODE_ENV=production
```

### Production (.env.production)
```env
POSTGRES_USER=prod_user
POSTGRES_PASSWORD=<secure-random-password>
DB_HOST=postgres.prod.internal
REDIS_HOST=redis.prod.internal
FLASK_ENV=production
FLASK_DEBUG=0
NODE_ENV=production
```

## Testing Configuration Changes

### Test with custom .env values:

```bash
# Stop current services
docker compose down

# Edit .env with new values
nano .env

# Start with new configuration
docker compose up -d

# Verify services loaded correct config
docker compose logs vote result worker | grep -i config
```

### Verify environment variables in running containers:

```bash
# View environment variables of vote service
docker compose exec vote printenv | grep -E "OPTION|REDIS|FLASK"

# View environment variables of result service  
docker compose exec result printenv | grep -E "DB|POSTGRES|NODE"

# View environment variables of worker service
docker compose exec worker printenv | grep -E "DB|POSTGRES|REDIS"
```

## Troubleshooting

### Issue: "Connection refused" to database/Redis

**Check if .env variables are loaded:**

```bash
# Check if DATABASE HOST is correct
docker compose exec result printenv | grep DB_HOST

# If DB_HOST is 'db', verify containers are on same network
docker network inspect example-voting-app_back-tier
```

### Issue: Services not starting

**Verify environment variables are set:**

```bash
# Check docker-compose parsed values
docker compose config | grep -A 20 "environment:"

# Check service logs for config errors
docker compose logs vote
```

### Issue: "Invalid connection string"

**Ensure connection string is properly formatted:**

```bash
# Test connection string manually
psql "postgres://postgres:postgres@db:5432/postgres"

# View parsed connection string in service
docker compose exec result node -e "console.log(process.env)"
```

## Application Code Changes

### vote/app.py
```python
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', 6379))
g.redis = Redis(host=redis_host, port=redis_port, db=0, socket_timeout=5)
```

### result/server.js
```javascript
var connectionString = `postgres://${dbUser}:${dbPassword}@${dbHost}:${dbPort}/${dbName}`;
var pool = new Pool({ connectionString: connectionString });
```

### worker/Program.cs
```csharp
var connectionString = $"Server={dbHost};Port={dbPort};Database={dbName};Username={dbUser};Password={dbPassword};";
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Production
on:
  push:
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      # Load production secrets from GitHub Secrets
      - name: Create production .env
        run: |
          echo "POSTGRES_USER=${{ secrets.PROD_POSTGRES_USER }}" >> .env.production
          echo "POSTGRES_PASSWORD=${{ secrets.PROD_POSTGRES_PASSWORD }}" >> .env.production
          echo "REDIS_HOST=${{ secrets.PROD_REDIS_HOST }}" >> .env.production
      
      # Deploy with production .env
      - name: Deploy
        run: |
          docker compose --env-file .env.production up -d
```

## Next Steps

1. **Review current .env file** - Ensure values match your deployment environment
2. **Generate strong passwords** for non-development environments
3. **Add to GitHub Secrets** if using CI/CD
4. **Test with different .env files** to verify configuration isolation
5. **Document any custom variables** your organization requires

## Related Documentation

- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [Kubernetes Secrets](https://kubernetes.io/docs/concepts/configuration/secret/)
- [OWASP Secrets Management](https://owasp.org/www-community/Sensitive_Data_Exposure)
- [12 Factor App - Configuration](https://12factor.net/config)

---

**Last Updated**: 2025-10-27  
**Status**: ✅ Environment variables fully implemented
