# Contributing to Delta CFO Agent

## Welcome Developers! 👋

Thank you for your interest in contributing to Delta CFO Agent. This guide will help you get started with the development process for our enterprise financial intelligence platform.

## 🎯 Current Development Focus

We are actively developing three major features for v3.0:

### 1. Multi-User Onboarding System
- **Lead Developer Needed**: Backend + Frontend specialist
- **Skills Required**: Python Flask, SQLite/PostgreSQL, React/Vue.js, OAuth
- **Timeline**: 4-6 weeks
- **Key Features**: User management, client onboarding wizard, role-based access

### 2. Revenue Recognition Dashboard
- **Lead Developer Needed**: Full-stack with accounting knowledge
- **Skills Required**: Financial systems, OCR/AI integration, Data visualization
- **Timeline**: 6-8 weeks
- **Key Features**: Invoice processing, ASC 606 compliance, revenue analytics

### 3. Advanced Reporting Engine
- **Lead Developer Needed**: Data visualization + BI specialist
- **Skills Required**: Chart.js/D3.js, PDF generation, SQL optimization
- **Timeline**: 8-10 weeks
- **Key Features**: Financial statements, AI insights, interactive dashboards

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.9+
- Node.js 16+ (for frontend builds)
- SQLite (development) / PostgreSQL (production)
- Anthropic API key

### Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/delta-cfo-agent
cd delta-cfo-agent

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
cp .env.example .env
# Edit .env with your API keys and database URLs

# 5. Initialize database
python setup_database.py

# 6. Start development server
cd web_ui && python app_db.py
# Server runs on http://localhost:5002
```

### Verify Installation
```bash
# Run tests
pytest tests/

# Check code style
flake8 --max-line-length=100 *.py

# Start frontend development
cd web_ui/static && npm run dev
```

## 🏗️ Project Architecture

### Current Structure
```
delta-cfo-agent/
├── main.py                    # Core transaction processor
├── web_ui/
│   ├── app_db.py             # Flask web server
│   ├── templates/            # HTML templates
│   └── static/               # CSS, JS, images
├── smart_ingestion.py        # AI document analysis
├── business_knowledge.md     # Classification rules
├── tests/                    # Test suites
└── docs/                     # Documentation
```

### Planned v3.0 Structure
```
delta-cfo-agent/
├── services/
│   ├── onboarding/           # 🆕 Multi-user system
│   ├── revenue/              # 🆕 Revenue recognition
│   ├── reporting/            # 🆕 Report generation
│   └── core/                 # Current transaction processing
├── models/                   # Database models
├── api/                      # REST API endpoints
├── frontend/                 # Modern React/Vue frontend
├── tests/                    # Comprehensive test suite
└── deployment/               # Docker, Kubernetes configs
```

## 💻 Development Workflow

### 1. Feature Development Process
1. **Create Feature Branch**
   ```bash
   git checkout -b feature/onboarding-system
   ```

2. **Follow TDD Approach**
   - Write tests first
   - Implement feature
   - Ensure all tests pass

3. **Code Quality Checks**
   ```bash
   # Run linting
   flake8 --max-line-length=100 *.py

   # Run tests
   pytest tests/ --cov=. --cov-report=html

   # Type checking
   mypy *.py
   ```

4. **Submit Pull Request**
   - Create PR against `develop` branch
   - Include comprehensive description
   - Request code review

### 2. Commit Message Format
```
type(scope): brief description

Detailed explanation of changes made.

- List key changes
- Reference issue numbers: Fixes #123
- Breaking changes: BREAKING CHANGE: describe change
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### 3. Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Individual feature development
- `hotfix/*`: Emergency production fixes

## 🧪 Testing Standards

### Test Coverage Requirements
- **Minimum Coverage**: 90% for all new code
- **Unit Tests**: All business logic functions
- **Integration Tests**: API endpoints and database operations
- **End-to-End Tests**: Critical user workflows

### Testing Framework
```python
# Example test structure
import pytest
from unittest.mock import Mock, patch

class TestOnboardingService:
    def test_create_user_success(self):
        # Test successful user creation
        assert result.status == "success"
        assert result.user_id is not None

    def test_create_user_duplicate_email(self):
        # Test duplicate email handling
        with pytest.raises(UserExistsError):
            service.create_user(existing_email)
```

## 📐 Coding Standards

### Python Code Style
```python
# Use type hints
def process_transaction(transaction: Dict[str, Any]) -> ProcessingResult:
    """Process a financial transaction with AI classification."""
    pass

# Use dataclasses for models
@dataclass
class User:
    id: UUID
    email: str
    role: UserRole
    created_at: datetime
```

### Database Design Principles
```python
# Use proper foreign keys and indexes
class Transaction(BaseModel):
    __tablename__ = "transactions"

    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(DECIMAL(15, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

### API Design Standards
```python
# RESTful endpoints with proper status codes
@app.route('/api/v1/transactions', methods=['POST'])
def create_transaction():
    try:
        result = transaction_service.create(request.json)
        return jsonify(result), 201
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Transaction creation failed: {e}")
        return jsonify({"error": "Internal server error"}), 500
```

## 🔒 Security Guidelines

### Data Protection
- **Never log sensitive data** (SSNs, bank accounts, API keys)
- **Encrypt sensitive fields** in database
- **Use parameterized queries** to prevent SQL injection
- **Validate all inputs** on both client and server

### Authentication & Authorization
```python
# Example role-based access control
@require_role(UserRole.CONSULTANT)
def access_client_data(client_id: UUID):
    # Verify user has access to this client
    if not user_service.can_access_client(current_user.id, client_id):
        raise UnauthorizedError()
```

## 🤖 AI Integration Best Practices

### Claude API Usage
```python
# Centralized AI client with error handling
class AIService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def classify_transaction(self, description: str) -> Classification:
        try:
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            return self._parse_classification(response.content)
        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            return self._fallback_classification(description)
```

### Cost Optimization
- **Cache AI responses** for similar inputs
- **Use appropriate models** (Haiku for simple tasks, Sonnet for complex)
- **Batch requests** when possible
- **Implement fallback systems** for when AI is unavailable

## 📊 Performance Guidelines

### Database Optimization
```python
# Use proper indexing
CREATE INDEX idx_transactions_user_date ON transactions(user_id, date DESC);

# Optimize queries
def get_user_transactions(user_id: UUID, limit: int = 100):
    return session.query(Transaction)\
        .filter(Transaction.user_id == user_id)\
        .order_by(Transaction.date.desc())\
        .limit(limit)\
        .options(joinedload(Transaction.category))\
        .all()
```

### Frontend Performance
- **Lazy load components** for large datasets
- **Implement pagination** for transaction lists
- **Use debouncing** for search inputs
- **Cache API responses** with appropriate TTL

## 🐛 Debugging & Troubleshooting

### Common Issues
1. **Claude API Rate Limits**: Implement exponential backoff
2. **Database Connection Timeouts**: Use connection pooling
3. **Memory Issues**: Implement streaming for large datasets
4. **File Upload Errors**: Validate file types and sizes

### Logging Standards
```python
import logging
import structlog

# Use structured logging
logger = structlog.get_logger()

def process_document(file_path: str):
    logger.info("Processing document", file_path=file_path)
    try:
        # Process file
        logger.info("Document processed successfully",
                   file_path=file_path,
                   transactions_found=count)
    except Exception as e:
        logger.error("Document processing failed",
                    file_path=file_path,
                    error=str(e))
        raise
```

## 📚 Resources & Documentation

### Key Documentation
- [Project Vision](PROJECT_VISION.md) - Overall roadmap and architecture
- [API Documentation](docs/api.md) - REST API specifications
- [Database Schema](docs/database.md) - Data model documentation
- [Deployment Guide](docs/deployment.md) - Production deployment

### External Resources
- [Anthropic Claude API Docs](https://docs.anthropic.com/)
- [Flask Best Practices](https://flask.palletsprojects.com/en/2.3.x/)
- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)

## 🆘 Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Architecture discussions and questions
- **Slack**: #delta-cfo-dev (real-time communication)
- **Email**: dev-team@deltacfo.ai

### Code Review Process
1. **Self-Review**: Check your own code before submitting PR
2. **Automated Checks**: Ensure CI/CD pipeline passes
3. **Peer Review**: At least one team member must approve
4. **Final Review**: Lead developer approval for major features

## 🎉 Recognition

Contributors will be recognized in:
- **README.md**: All contributors list
- **Release Notes**: Feature contributors highlighted
- **Team Page**: Public recognition on website
- **LinkedIn**: Professional endorsements

---

**Ready to contribute? Pick a feature, create a branch, and let's build the future of financial intelligence together! 🚀**

Questions? Reach out on Slack or create a GitHub discussion.