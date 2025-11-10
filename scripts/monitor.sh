#!/bin/bash

# Application Monitoring Script
# Usage: ./scripts/monitor.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "Kundelik Predict - Monitoring"
echo "================================"
echo ""

# Check Docker services
echo "Checking Docker services..."
docker-compose ps

echo ""
echo "Service Status:"
echo "==============="

# Check web service
if docker-compose exec -T web curl -s http://localhost:8000/health/ > /dev/null; then
    echo -e "${GREEN}✓ Web Service${NC}: Healthy"
else
    echo -e "${RED}✗ Web Service${NC}: Unhealthy"
fi

# Check database
if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database${NC}: Connected"
else
    echo -e "${RED}✗ Database${NC}: Disconnected"
fi

# Check nginx
if docker-compose exec -T nginx nginx -t > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Nginx${NC}: Running"
else
    echo -e "${RED}✗ Nginx${NC}: Error"
fi

echo ""
echo "Resource Usage:"
echo "==============="
docker stats --no-stream

echo ""
echo "Recent Logs (last 20 lines):"
echo "============================"
docker-compose logs --tail=20 web

echo ""
echo "Monitoring complete!"
