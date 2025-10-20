# 🚀 Deployment Guide - Crypto Invoice Payment System

Production deployment guide for Delta Energy Paraguay operations.

---

## 📋 Pre-Deployment Checklist

### 1. MEXC API Setup
- [ ] Create MEXC account at https://www.mexc.com
- [ ] Enable API access in account settings
- [ ] Generate API Key and Secret
- [ ] **Important:** Enable these permissions:
  - ✅ Read account information
  - ✅ View deposit history
  - ✅ Generate deposit addresses
  - ❌ Disable withdrawal permissions (security)
- [ ] Whitelist server IP address (if using IP restrictions)

### 2. Server Requirements
- [ ] Ubuntu 20.04+ or similar Linux distribution
- [ ] Python 3.9+
- [ ] 2GB RAM minimum (4GB recommended)
- [ ] 10GB disk space
- [ ] Open port 5002 (or configure reverse proxy)

### 3. Email Configuration (Optional but Recommended)
- [ ] Gmail App Password or SMTP credentials
- [ ] Configure aldo@deltaenergy.com and tiago@deltaenergy.com as recipients

---

## 🔧 Installation Steps

### Step 1: Clone and Setup

```bash
# Navigate to project directory
cd /var/www/DeltaCFOAgentv2

# Verify crypto_invoice_system directory exists
ls crypto_invoice_system

# Install dependencies
cd crypto_invoice_system
pip3 install -r requirements.txt

# OR use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Configuration:**

```env
# MEXC API (REQUIRED)
MEXC_API_KEY=your_actual_api_key_here
MEXC_API_SECRET=your_actual_api_secret_here

# Flask (REQUIRED)
FLASK_SECRET_KEY=$(openssl rand -hex 32)
FLASK_ENV=production
FLASK_DEBUG=False

# Email (RECOMMENDED)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=billing@deltaenergy.com
SMTP_PASSWORD=your_gmail_app_password
NOTIFICATION_EMAIL_CC=aldo@deltaenergy.com,tiago@deltaenergy.com
```

### Step 3: Initialize Database

```bash
python3 -c "from models.database_postgresql import CryptoInvoiceDatabaseManager; CryptoInvoiceDatabaseManager()"

# Verify PostgreSQL connection and table creation
python3 -c "from models.database_postgresql import CryptoInvoiceDatabaseManager; db = CryptoInvoiceDatabaseManager(); print('PostgreSQL database initialized successfully')"
```

### Step 4: Test MEXC Connection

```bash
# Start server temporarily
python3 api/invoice_api.py &
SERVER_PID=$!

# Wait for startup
sleep 3

# Test MEXC API
curl http://localhost:5002/api/test-mexc

# Stop test server
kill $SERVER_PID
```

Expected response:
```json
{
  "success": true,
  "server_time": 1696161600000,
  "message": "MEXC API connection successful"
}
```

---

## 🌐 Production Deployment Options

### Option 1: Systemd Service (Recommended)

Create service file:

```bash
sudo nano /etc/systemd/system/crypto-invoice.service
```

Add configuration:

```ini
[Unit]
Description=Delta Energy Crypto Invoice Payment System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/DeltaCFOAgentv2/crypto_invoice_system
Environment="PATH=/var/www/DeltaCFOAgentv2/crypto_invoice_system/venv/bin"
ExecStart=/var/www/DeltaCFOAgentv2/crypto_invoice_system/venv/bin/python api/invoice_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable crypto-invoice
sudo systemctl start crypto-invoice
sudo systemctl status crypto-invoice
```

View logs:
```bash
sudo journalctl -u crypto-invoice -f
```

### Option 2: Gunicorn with Nginx

Install Gunicorn:

```bash
pip install gunicorn
```

Create Gunicorn start script:

```bash
nano start_gunicorn.sh
```

```bash
#!/bin/bash
cd /var/www/DeltaCFOAgentv2/crypto_invoice_system
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5002 api.invoice_api:app
```

Make executable:
```bash
chmod +x start_gunicorn.sh
```

Nginx configuration:

```nginx
server {
    listen 80;
    server_name invoices.deltaenergy.com;

    location / {
        proxy_pass http://127.0.0.1:5002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Option 3: Docker Container

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_ENV=production

EXPOSE 5002

CMD ["python", "api/invoice_api.py"]
```

Build and run:

```bash
docker build -t crypto-invoice-system .
docker run -d -p 5002:5002 --env-file .env crypto-invoice-system
```

---

## 🔒 Security Hardening

### 1. Environment Variables

```bash
# Set restrictive permissions on .env
chmod 600 .env

# Verify
ls -la .env
# Should show: -rw------- (only owner can read/write)
```

### 2. Firewall Configuration

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS if using Nginx
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# OR allow direct access to Flask
sudo ufw allow 5002/tcp

# Enable firewall
sudo ufw enable
```

### 3. HTTPS Setup (Recommended)

Using Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d invoices.deltaenergy.com
```

### 4. Database Backups

Create backup script:

```bash
nano backup_db.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/crypto-invoices"
mkdir -p $BACKUP_DIR

# Backup database
cp /var/www/DeltaCFOAgentv2/crypto_invoice_system/crypto_invoices.db \
   $BACKUP_DIR/crypto_invoices_$DATE.db

# Keep only last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete

echo "Backup completed: crypto_invoices_$DATE.db"
```

Schedule daily backups:
```bash
chmod +x backup_db.sh
sudo crontab -e

# Add line:
0 2 * * * /path/to/backup_db.sh
```

---

## 📊 Monitoring Setup

### 1. Health Check Endpoint

Add to crontab for monitoring:

```bash
*/5 * * * * curl -s http://localhost:5002/api/polling-stats || echo "Crypto Invoice System DOWN" | mail -s "ALERT" aldo@deltaenergy.com
```

### 2. Log Rotation

```bash
sudo nano /etc/logrotate.d/crypto-invoice
```

```
/var/log/crypto-invoice/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload crypto-invoice > /dev/null 2>&1 || true
    endscript
}
```

### 3. Application Logging

Configure structured logging in production:

```python
# Add to invoice_api.py
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler(
        'crypto_invoice.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
```

---

## 🧪 Post-Deployment Testing

### 1. Create Test Invoice

```bash
curl -X POST http://localhost:5002/api/invoice/create \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "amount_usd": 100,
    "crypto_currency": "USDT",
    "crypto_network": "TRC20",
    "billing_period": "Test Period",
    "due_date": "2025-10-31",
    "description": "Test Invoice",
    "line_items": [
      {"description": "Test Item", "amount": 100}
    ]
  }'
```

### 2. Verify Invoice Created

```bash
curl http://localhost:5002/api/invoices | jq
```

### 3. Check Polling Service

```bash
curl http://localhost:5002/api/polling-stats | jq
```

Expected output shows `is_running: true` and polling activity.

### 4. Download PDF

Open in browser: `http://your-server:5002/api/invoice/1/pdf`

---

## 🚨 Troubleshooting Production Issues

### Service Won't Start

```bash
# Check logs
sudo journalctl -u crypto-invoice -n 50

# Check if port already in use
sudo netstat -tulpn | grep 5002

# Verify Python environment
source venv/bin/activate
python --version
pip list
```

### MEXC API Errors

```bash
# Test API connection
curl http://localhost:5002/api/test-mexc

# Check environment variables loaded
sudo systemctl show crypto-invoice | grep Environment
```

### Database Locked Errors

```bash
# Check file permissions
ls -la crypto_invoices.db

# Fix ownership
sudo chown www-data:www-data crypto_invoices.db
```

### Email Notifications Not Working

```bash
# Test SMTP manually
python3 << EOF
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your_email', 'your_password')
print("SMTP Connection Successful")
server.quit()
EOF
```

---

## 📈 Performance Tuning

### Database Optimization

```sql
-- Run periodically to optimize database
VACUUM;
ANALYZE;

-- Create additional indexes if needed
CREATE INDEX idx_invoices_paid_at ON invoices(paid_at);
CREATE INDEX idx_payments_detected_at ON payment_transactions(detected_at);
```

### Gunicorn Workers

Recommended worker count = (2 x CPU cores) + 1

```bash
# For 2 CPU server
gunicorn -w 5 -b 0.0.0.0:5002 api.invoice_api:app
```

---

## 🔄 Updates and Maintenance

### Updating the System

```bash
cd /var/www/DeltaCFOAgentv2/crypto_invoice_system

# Pull latest changes
git pull

# Backup database first!
cp crypto_invoices.db crypto_invoices.db.backup

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart crypto-invoice
```

### Database Migrations

For schema changes, create migration scripts:

```python
# migration_001_add_new_field.py
import sqlite3

conn = sqlite3.connect('crypto_invoices.db')
cursor = conn.cursor()

cursor.execute("""
    ALTER TABLE invoices
    ADD COLUMN new_field TEXT
""")

conn.commit()
conn.close()
print("Migration completed")
```

---

## 📞 Emergency Contacts

**System Issues:**
- Aldo: aldo@deltaenergy.com
- Tiago: tiago@deltaenergy.com

**MEXC API Issues:**
- MEXC Support: https://www.mexc.com/support

**Critical Failure Recovery:**
1. Stop service: `sudo systemctl stop crypto-invoice`
2. Restore database: `cp /var/backups/crypto-invoices/latest.db crypto_invoices.db`
3. Check logs: `sudo journalctl -u crypto-invoice -n 100`
4. Restart service: `sudo systemctl start crypto-invoice`

---

**System Status:** Production-Ready ✅
**Last Updated:** October 2025
**Version:** 1.0.0
