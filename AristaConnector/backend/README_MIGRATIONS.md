# Database Migrations

## Quick Start

### First Time Setup

1. **Create initial migration:**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Initial migration"
   ```

2. **Review the generated migration file** in `alembic/versions/`

3. **Apply migration:**
   ```bash
   alembic upgrade head
   ```

### Using Docker

```bash
# Create migration
docker compose exec backend alembic revision --autogenerate -m "Description"

# Apply migration
docker compose exec backend alembic upgrade head

# Or use Makefile
make migrate
```

## Current Schema

### Devices Table
- `id` (UUID, primary key)
- `hostname` (string, nullable)
- `ip` (string, required, indexed)
- `port` (integer, default 443)
- `username` (string, required)
- `password_enc` (text, encrypted password)
- `interval_sec` (integer, default 10)
- `enabled` (boolean, default true, indexed)
- `created_at` (timestamp)
- `updated_at` (timestamp, nullable)

### Events Table
- `id` (UUID, primary key)
- `device_id` (UUID, foreign key to devices.id)
- `event_type` (string, indexed)
- `message` (text, nullable)
- `metadata` (text, JSON stored as text)
- `created_at` (timestamp, indexed)

## Migration from Old Schema

If you have existing data with integer IDs, you'll need a custom migration to:
1. Add UUID columns
2. Generate UUIDs for existing records
3. Update foreign keys
4. Drop old integer columns

See `MIGRATION_GUIDE.md` for details.
