# Database Migration Guide

## Creating Initial Migration

After updating the models, create a new migration:

```bash
# In the backend directory
alembic revision --autogenerate -m "Initial migration with UUID and encrypted passwords"
```

This will create a migration file in `alembic/versions/`.

## Review Migration

Always review the generated migration file before applying:

```bash
# View the migration file
cat alembic/versions/<migration_file>.py
```

## Apply Migration

```bash
# Apply all pending migrations
alembic upgrade head

# Or in Docker
docker compose exec backend alembic upgrade head
```

## Rollback Migration

```bash
# Rollback one step
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>
```

## Manual Migration Steps

If you need to migrate existing data:

1. **Backup existing database**
2. **Create migration script** with data transformation
3. **Test on staging** first
4. **Apply to production**

## Migration Checklist

- [ ] Review generated migration
- [ ] Test migration on development database
- [ ] Backup production database
- [ ] Apply migration during maintenance window
- [ ] Verify data integrity after migration
- [ ] Update application code if needed
