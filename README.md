# Kundelik Predict - Grade Prediction Calculator

A simple web app to predict what grades you need on tests and exams to reach your target grade.

## Quick Start

```bash
# Start services
docker-compose up -d

# Initialize database
docker-compose exec web python manage.py migrate

# Access at http://localhost
```

## Setup

1. Copy `.env.example` to `.env`
2. Update `.env` with your settings (optional for local dev)
3. Run `docker-compose up -d`

## Common Commands

```bash
# View logs
docker-compose logs -f web

# Stop services
docker-compose down

# Run migrations
docker-compose exec web python manage.py migrate

# Create admin user
docker-compose exec web python manage.py createsuperuser

# Database shell
docker-compose exec db psql -U postgres -d kundelik_predict
```

## Backup

```bash
# Backup database
./scripts/backup.sh

# Restore database
./scripts/restore.sh backups/kundelik_predict_*.sql.gz
```

## Troubleshooting

```bash
# Check service status
docker-compose ps

# Rebuild and restart
docker-compose down
docker-compose up -d --build

# Health check
curl http://localhost/health/
```

## Stack

- Django 4.2.23
- PostgreSQL 16
- Nginx
- Gunicorn
- Docker
