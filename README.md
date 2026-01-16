# ServantAssist Backend

FastAPI backend with Clean Architecture for ServantAssist platform.

## 🏗️ Architecture

- **Clean Architecture** (Hexagonal Architecture)
- **FastAPI** framework
- **PostgreSQL** database with Drizzle ORM
- **Redis** for caching
- **CloudFlare R2** for file storage

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start server
uvicorn src.main:app --reload
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test
pytest tests/unit/test_user_service.py
```

## 📚 Documentation

- API Docs: http://localhost:8000/api/docs
- Architecture: [CLEAN_ARCHITECTURE.md](../docs/CLEAN_ARCHITECTURE.md)

## 🔗 Related Repositories

- [Platform](https://github.com/your-org/servantassist-platform)
- [Frontend Web](https://github.com/your-org/servantassist-web)
- [Frontend Mobile](https://github.com/your-org/servantassist-mobile)
