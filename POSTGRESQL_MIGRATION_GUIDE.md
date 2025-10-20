# 🚀 DeltaCFOAgent PostgreSQL Migration Guide

Complete step-by-step guide for migrating the DeltaCFOAgent system from SQLite to PostgreSQL.

---

## 📋 Migration Overview

This migration moves all components from SQLite to a centralized PostgreSQL database:

### ✅ **Migrated Components:**
- **Main Transaction System** (`web_ui/`) - Uses centralized DatabaseManager
- **Crypto Pricing System** (`crypto_pricing.py`) - PostgreSQL backend
- **Crypto Invoice System** (`crypto_invoice_system/`) - New PostgreSQL implementation
- **Analytics Service** (`services/analytics_service/`) - DatabaseManager integration

### 🗄️ **Database Architecture:**
- **Before**: Multiple SQLite files (development-oriented)
- **After**: Single PostgreSQL instance (production-ready)

---

## 🛠️ Pre-Migration Setup

### 1. PostgreSQL Database Setup

First, ensure you have a PostgreSQL database ready:

```bash
# Option A: Local PostgreSQL
sudo -u postgres createdb delta_cfo
sudo -u postgres createuser delta_user
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE delta_cfo TO delta_user;"

# Option B: Google Cloud SQL (recommended for production)
# Follow: migration/CLOUD_SQL_SETUP.md
```

### 2. Environment Configuration

Update your `.env` file with PostgreSQL settings:

```env
# Database Configuration
DB_TYPE=postgresql
DB_HOST=your-postgresql-host
DB_PORT=5432
DB_NAME=delta_cfo
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_SSL_MODE=require

# For Google Cloud SQL
DB_SOCKET_PATH=/cloudsql/project-id:region:instance-name
GOOGLE_CLOUD_PROJECT=your-project-id
```

### 3. Install Dependencies

Ensure PostgreSQL dependencies are installed:

```bash
pip install -r requirements.txt
# This includes psycopg2-binary and google-cloud-sql-python-connector
```

---

## 🗃️ Step-by-Step Migration Process

### Step 1: Create PostgreSQL Schema

Run the unified schema creation script:

```bash
# Connect to your PostgreSQL database and run:
psql -h your-host -U your-user -d delta_cfo -f postgres_unified_schema.sql

# Or for Google Cloud SQL:
cloud_sql_proxy project-id:region:instance-name &
psql -h 127.0.0.1 -U your-user -d delta_cfo -f postgres_unified_schema.sql
```

This creates all required tables, indexes, and initial data.

### Step 2: Test Database Connectivity

Verify the new PostgreSQL setup works:

```bash
python test_postgresql_migration.py --component=main --verbose
```

Expected output:
```
✅ PASS: Database Connection
✅ PASS: Database Type Check
✅ PASS: Core Tables Exist
✅ PASS: Basic CRUD Operations
```

### Step 3: Migrate Existing Data

**⚠️ Important**: Back up your existing data first!

```bash
# Backup existing SQLite databases
cp web_ui/delta_transactions.db web_ui/delta_transactions.db.backup
cp crypto_invoice_system/crypto_invoices.db crypto_invoice_system/crypto_invoices.db.backup

# Run migration script (dry-run first)
python migrate_data_to_postgresql.py --dry-run

# If everything looks good, run the actual migration
python migrate_data_to_postgresql.py --backup
```

### Step 4: Validate All Components

Test each component individually:

```bash
# Test all components
python test_postgresql_migration.py --verbose

# Or test individual components
python test_postgresql_migration.py --component=main
python test_postgresql_migration.py --component=crypto_pricing
python test_postgresql_migration.py --component=crypto_invoice
python test_postgresql_migration.py --component=analytics
```

### Step 5: Update Application Configuration

The following files have been automatically updated:

- ✅ `web_ui/database.py` - Centralized DatabaseManager
- ✅ `crypto_pricing.py` - PostgreSQL implementation
- ✅ `crypto_invoice_system/models/database_postgresql.py` - New PostgreSQL model
- ✅ `crypto_invoice_system/api/invoice_api.py` - Updated imports
- ✅ `services/analytics_service/app.py` - DatabaseManager integration

### Step 6: Clean Up SQLite Files (Optional)

Remove obsolete SQLite files:

```bash
# Dry-run to see what would be cleaned
python cleanup_sqlite_files.py --dry-run

# Clean up with backups
python cleanup_sqlite_files.py --backup

# Clean up without backups (use with caution)
python cleanup_sqlite_files.py
```

---

## 🧪 Testing the Migration

### Comprehensive Testing

Run the complete test suite:

```bash
python test_postgresql_migration.py --verbose
```

### Manual Testing

1. **Start the web dashboard:**
   ```bash
   cd web_ui && python app_db.py
   # Visit http://localhost:5001
   ```

2. **Test crypto invoice system:**
   ```bash
   cd crypto_invoice_system && python api/invoice_api.py
   # Visit http://localhost:5003
   ```

3. **Test analytics service:**
   ```bash
   cd services/analytics_service && python app.py
   # Visit http://localhost:8080
   ```

### Data Verification

Check that your data migrated correctly:

```sql
-- Connect to PostgreSQL and verify:

-- Check transaction count
SELECT COUNT(*) FROM transactions;

-- Check business entities
SELECT * FROM business_entities;

-- Check crypto prices
SELECT COUNT(*) FROM crypto_historic_prices;

-- Check invoice data
SELECT COUNT(*) FROM invoices;
SELECT COUNT(*) FROM clients;
```

---

## 🚨 Troubleshooting

### Common Issues

**1. Connection Errors**
```
Error: could not connect to server
```
- Verify PostgreSQL is running
- Check host, port, username, password in `.env`
- For Cloud SQL, ensure Cloud SQL Proxy is running

**2. Permission Errors**
```
Error: permission denied for table
```
- Ensure database user has proper permissions
- Run: `GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;`

**3. Missing Tables**
```
Error: relation "transactions" does not exist
```
- Run the schema creation script: `postgres_unified_schema.sql`
- Check that the script completed without errors

**4. Import Errors**
```
ModuleNotFoundError: No module named 'psycopg2'
```
- Install PostgreSQL dependencies: `pip install psycopg2-binary`

### Data Migration Issues

**Partial Migration**
```bash
# Check migration status
python migrate_data_to_postgresql.py --dry-run

# Force re-migration if needed
python migrate_data_to_postgresql.py --force
```

**Data Validation**
```bash
# Compare record counts between SQLite and PostgreSQL
python -c "
import sqlite3
conn = sqlite3.connect('web_ui/delta_transactions.db')
print('SQLite transactions:', conn.execute('SELECT COUNT(*) FROM transactions').fetchone()[0])
"

# Then check PostgreSQL
python -c "
from web_ui.database import db_manager
result = db_manager.execute_query('SELECT COUNT(*) FROM transactions', fetch_one=True)
print('PostgreSQL transactions:', result[0])
"
```

---

## 📊 Performance Benefits

### Before (SQLite)
- Multiple separate database files
- Limited concurrent access
- File-based storage limitations
- Development-oriented setup

### After (PostgreSQL)
- Single centralized database
- Full ACID compliance
- Excellent concurrent performance
- Production-ready with Cloud SQL
- Advanced indexing and query optimization
- Built-in backup and replication

---

## 🚀 Post-Migration Steps

### 1. Update Deployment Scripts

Update your deployment configurations:

```bash
# Update environment variables in production
# Configure Cloud SQL connection strings
# Update Docker/Cloud Run configurations
```

### 2. Setup Database Monitoring

```bash
# Enable Cloud SQL monitoring
# Setup performance insights
# Configure backup schedules
```

### 3. Remove SQLite Dependencies

Optional cleanup:

```bash
# Remove SQLite files
python cleanup_sqlite_files.py --backup

# Update .gitignore to ignore future SQLite files
# Remove SQLite-related imports from legacy files
```

---

## 📞 Support

### Migration Complete ✅

If all tests pass, your migration is complete! The DeltaCFOAgent system is now running entirely on PostgreSQL.

### Issues or Questions

1. **Check test results**: `python test_postgresql_migration.py --verbose`
2. **Review migration logs**: Check output from migration scripts
3. **Verify configuration**: Ensure `.env` file has correct PostgreSQL settings
4. **Database connectivity**: Test connection with `psql` or database client

### Rolling Back (Emergency)

If you need to roll back to SQLite:

1. Stop all services
2. Restore SQLite database backups
3. Temporarily change `DB_TYPE=sqlite` in `.env`
4. Restart services

However, this should only be a temporary measure while fixing the PostgreSQL setup.

---

## 🎉 Migration Complete!

Your DeltaCFOAgent system is now running on a modern, scalable PostgreSQL backend. Enjoy the improved performance, reliability, and production-readiness!

**Key Benefits Achieved:**
- ✅ Unified database architecture
- ✅ Production-ready scalability
- ✅ Enhanced data integrity
- ✅ Cloud-native deployment ready
- ✅ Improved concurrent access
- ✅ Advanced query capabilities

The system is ready for production deployment and can now scale to meet enterprise requirements.