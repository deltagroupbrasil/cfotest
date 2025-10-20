# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeltaCFOAgent is an AI-powered financial transaction processing and management system that integrates Claude AI for intelligent transaction classification, smart document ingestion, and business intelligence. Delta is the entity that is designing the system for its own use, BUT Delta will market this CFO AI Agent to other companies - so all Claude Code changes and code should be written to work for any user. The project is built for a company with multiple business entities with automated invoice processing, cryptocurrency pricing, and comprehensive financial dashboards and all other CFO corporate responsibilities. Reinforcement learning systems should be put in palce wherever and everywhere users input and provide data on the user's business.

## Development Commands

### Environment Setup
```bash
# Install dependencies (includes all modules)
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add ANTHROPIC_API_KEY and database credentials
```

### Running the Application
```bash
# Main web dashboard (PostgreSQL)
cd web_ui && python app_db.py
# Access: http://localhost:5001

# Legacy dashboard (CSV-based)
cd web_ui && python app.py
# Access: http://localhost:5002

# Crypto invoice system
cd crypto_invoice_system && python api/invoice_api.py
# Access: http://localhost:5003

# Analytics service
cd services/analytics_service && python app.py
# Access: http://localhost:8080
```

### Testing
```bash
# Manual integration tests (no automated framework exists)
python test_final.py  # Production health checks
python invoice_processing/test_database.py  # Database operations
python invoice_processing/test_full_pipeline.py  # Full pipeline with Flask UI

# Note: No pytest framework currently implemented
```

### Database Operations
```bash
# Create database tables
python create_tables.py

# Apply schema (multiple regional options)
python apply_schema_sa.py  # South America region

# Validate database setup
python validate_simple.py
```

## Architecture Overview

### Core System Architecture
The system follows a modular microservices architecture with three main layers:

1. **Processing Layer**: Smart document ingestion with Claude AI classification
2. **Data Layer**: PostgreSQL-only architecture (production-ready)
3. **Presentation Layer**: Multiple web interfaces for different use cases

### Key Components

**Main Transaction Processing (`main.py`)**
- `DeltaCFOAgent` class: Core transaction classification and processing
- Business knowledge integration from `business_knowledge.md`
- Support for multiple file formats (CSV, bank statements)
- Reinforcement learning from user feedback

**Smart Ingestion System (`smart_ingestion.py`)**
- Claude API integration for document structure analysis
- Automatic format detection and column mapping
- Handles Chase bank formats, standard CSV, and custom formats

**Web Interfaces**
- `web_ui/app_db.py`: Advanced dashboard with database backend
- `web_ui/app.py`: Simple dashboard with CSV backend
- Templates in `web_ui/templates/` with advanced JavaScript interactions

**Specialized Modules**
- `crypto_invoice_system/`: Complete invoice processing with MEXC exchange integration
- `invoice_processing/`: PDF/OCR processing with Claude Vision
- `services/analytics_service/`: Microservice for financial analytics

### Database Architecture

**PostgreSQL-Only Strategy**:
- **All Environments**: PostgreSQL (development and production)
- **Production**: PostgreSQL on Google Cloud SQL
- **Development**: Direct connection to production PostgreSQL instance

**Key Tables**:
- `transactions`: Main transaction records with AI classifications
- `invoices`: Invoice data with vendor information and line items
- `learned_patterns`: Machine learning feedback storage
- `user_interactions`: Reinforcement learning data

**Connection Management**: `DatabaseManager` class in `web_ui/database.py` provides centralized PostgreSQL connectivity for all components.

### AI Integration Patterns

**Claude API Integration**:
- Transaction classification with confidence scoring
- Document structure analysis for smart ingestion
- Business rule application from `business_knowledge.md`
- Vision API for PDF/image processing in invoice module

**Business Classification Rules**:
The system uses a hierarchical classification approach:
1. Exact pattern matching (high confidence)
2. Claude AI classification (medium confidence)
3. Fallback categorization (low confidence)

Business entities and rules are defined in `business_knowledge.md`.

### Deployment Configuration

**Google Cloud Run** (Primary):
- Multi-stage Docker builds (`Dockerfile`)
- Cloud Build integration (`cloudbuild.yaml`)
- Secret Manager for API keys and credentials
- Cloud SQL for production database

**Alternative Deployment**:
- Vercel support via `api/index.py` and `vercel.json`
- Development server with direct PostgreSQL access

### Security Considerations

**Critical Security Notes**:
- API keys must be stored in environment variables or Secret Manager
- Database credentials should never be hardcoded
- All endpoints currently lack authentication (development state)
- File uploads need validation and sanitization

### Module Dependencies

**Core Dependencies**:
- `anthropic`: Claude AI API integration
- `flask`: Web framework for all interfaces
- `pandas`: Data processing and CSV handling
- `psycopg2-binary`: PostgreSQL adapter
- `requests`: External API calls (CoinGecko, MEXC)

**Specialized Dependencies**:
- `PyMuPDF`, `pdfplumber`: PDF processing
- `pytesseract`: OCR functionality
- `exchangelib`: Email automation (invoice processing)
- `qrcode`: QR code generation (crypto invoices)

## Key Development Patterns

### Error Handling
The codebase uses a mix of patterns:
- Try-catch with logging for external API calls
- Graceful degradation when AI services are unavailable
- Database transaction rollback for data integrity

### Configuration Management
- Environment variables for API keys and database credentials
- `business_knowledge.md` for business logic configuration
- Regional deployment configurations for different Cloud SQL instances

### File Processing Pipeline
1. File upload and validation
2. Smart format detection (Claude analysis)
3. Data extraction and normalization
4. AI-powered classification
5. Database storage with confidence scoring
6. User feedback integration for learning

## Database Guidelines - PostgreSQL Only

### 🚨 CRITICAL: PostgreSQL-Only Policy

**This project has been fully migrated to PostgreSQL. NO NEW SQLite code should be added.**

### Database Development Rules:

1. **Always Use DatabaseManager**: All database access must go through the centralized `DatabaseManager` in `web_ui/database.py`
2. **No Direct SQLite**: Never import `sqlite3` or create new SQLite connections
3. **PostgreSQL Queries**: Write SQL compatible with PostgreSQL syntax
4. **Connection Pooling**: Use the existing connection management - never create direct connections
5. **Schema Updates**: All schema changes must be applied to `postgres_unified_schema.sql`

### Available Database Components:

- **Main System**: Uses `db_manager` from `web_ui/database.py`
- **Crypto Pricing**: Uses `CryptoPricingDB` → `db_manager`
- **Crypto Invoices**: Uses `CryptoInvoiceDatabaseManager` → `db_manager`
- **Analytics**: Uses `AnalyticsEngine` → `db_manager`

### Database Testing:

```bash
# Test PostgreSQL migration
python test_postgresql_migration.py --verbose

# Test specific component
python test_postgresql_migration.py --component=main
```

### Migration Resources:

- **Schema**: `postgres_unified_schema.sql` (unified schema for all components)
- **Data Migration**: `migrate_data_to_postgresql.py` (SQLite → PostgreSQL)
- **Testing**: `test_postgresql_migration.py` (comprehensive validation)
- **Guide**: `POSTGRESQL_MIGRATION_GUIDE.md` (step-by-step instructions)

## Important Notes

- The system is currently in active development with production deployment
- Database schema evolution is managed manually (no formal migration system)
- Business knowledge and classification rules are externalized in markdown files
- Multiple deployment guides exist - prefer `DEPLOYMENT_GUIDE.md` for comprehensive instructions
- Some test files are mixed with production code and should be cleaned up

Claude's Code Rules:
1. First, think about the problem, read the code base for the relevant files, and write a plan in tasks/todo.md.
2. The plan should have a list of tasks that you can mark as complete as you finish them.
3. Before you start working, contact me and I will check the plan.
4. Then start working on the tasks, marking them as complete as you go.
5. Please, every step of the way, just give me a detailed explanation of the changes you've made.
6. Make each task and code change as simple as possible. We want to avoid large or complex changes. Each change should impact as little code as possible. It all comes down to simplicity.
7. Finally, add a review section to the all.md file with a summary of the changes made and any other relevant information.
8. DON'T BE LAZY. NEVER BE LAZY. IF THERE IS A BUG, FIND THE ROOT CAUSE AND FIX IT. NO TEMPORARY FIXES. YOU ARE A SENIOR DEVELOPER. NEVER BE LAZY.
9. MAKE ALL CORRECTIONS AND CODE CHANGES AS SIMPLE AS POSSIBLE. THEY SHOULD ONLY IMPACT THE CODE THAT IS NECESSARY AND RELEVANT TO THE TASK AND NOTHING ELSE. IT SHOULD IMPACT AS LITTLE CODE AS POSSIBLE. YOUR GOAL IS TO NOT INTRODUCE ANY BUGS. IT'S ALL ABOUT SIMPLICITY.