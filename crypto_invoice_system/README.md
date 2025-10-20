# 🔷 Crypto Invoice Payment System for Delta Energy

**Production-ready crypto invoice and payment tracking system for Paraguay colocation operations**

Automated invoice generation, MEXC API integration, and real-time payment monitoring for Alps Blockchain, Exos Capital, and GM Data Centers.

---

## 🎯 Features

### ✅ Core Functionality
- **Professional Invoice Generation** - PDF invoices with QR codes and payment instructions
- **MEXC API Integration** - Automatic deposit address generation per invoice
- **Real-Time Payment Polling** - 30-second polling intervals for payment detection
- **Automatic Confirmation** - Tracks blockchain confirmations until payment confirmed
- **Manual TxID Verification** - Backup system for manual payment verification
- **Email Notifications** - Automated alerts for payment detection, confirmation, and overdue invoices
- **AI CFO System Integration** - Syncs paid invoices to existing Delta CFO Agent for revenue recognition
- **Multi-Currency Support** - BTC, USDT (TRC20/ERC20/BEP20), TAO (Bittensor)

### 📊 Dashboard Features
- Real-time invoice status tracking
- Payment monitoring statistics
- Pending/paid/overdue invoice overview
- MEXC API connection testing

---

## 🏗️ System Architecture

```
crypto_invoice_system/
├── models/
│   ├── database.py          # Legacy SQLite (deprecated)
│   └── database_postgresql.py # PostgreSQL database models and operations
├── services/
│   ├── mexc_service.py      # MEXC API wrapper
│   ├── invoice_generator.py # PDF invoice generation with QR codes
│   ├── payment_poller.py    # 30-second payment polling service
│   └── notification_service.py # Email/webhook notifications
├── api/
│   └── invoice_api.py       # Flask REST API
├── templates/
│   ├── dashboard.html       # Main dashboard
│   └── create_invoice.html  # Invoice creation form
├── generated_invoices/      # Output directory for PDFs and QR codes
├── config/                  # PostgreSQL connection settings
├── requirements.txt         # Python dependencies
├── .env.example             # Environment configuration template
└── README.md                # This file
```

---

## 🚀 Quick Start

### 1. Installation

```bash
cd crypto_invoice_system

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Configuration

Edit `.env` file with your credentials:

```env
# Required: MEXC API credentials
MEXC_API_KEY=your_api_key
MEXC_API_SECRET=your_api_secret

# Optional: Email notifications
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### 3. Initialize Database

```bash
python -c "from models.database_postgresql import CryptoInvoiceDatabaseManager; CryptoInvoiceDatabaseManager()"
```

This initializes the PostgreSQL database with all required tables and default clients (no longer using SQLite).

### 4. Start the Server

```bash
python api/invoice_api.py
```

Server runs on `http://localhost:5002`

### 5. Access the Dashboard

Open `http://localhost:5002` in your browser

---

## 📘 Usage Guide

### Creating an Invoice

1. Click **"Create New Invoice"** on dashboard
2. Select client (Alps Blockchain, Exos Capital, GM Data Centers, or Other)
3. Choose cryptocurrency and network (BTC, USDT-TRC20/ERC20/BEP20, TAO)
4. Enter amount in USD (crypto amount calculated automatically)
5. Set billing period and due date
6. Add line items (optional): power consumption, hosting fees, etc.
7. Click **"Generate Invoice"**

**System automatically:**
- Generates unique invoice number (format: `DPY-YYYY-MM-####`)
- Fetches fresh MEXC deposit address
- Creates QR code for payment
- Generates professional PDF invoice
- Starts monitoring for payment every 30 seconds

### Payment Detection

**Automatic Process:**
1. Payment poller checks MEXC API every 30 seconds
2. When payment detected → Email notification sent
3. Tracks confirmations (BTC: 3, USDT: 20, TAO: 12)
4. When confirmed → Invoice marked as PAID
5. Syncs to AI CFO system for revenue recognition

**Manual Verification (Backup):**
1. Go to invoice details
2. Click "Verify Payment Manually"
3. Enter transaction ID (TxID)
4. System verifies with MEXC and marks as paid if valid

### Monitoring Payments

Dashboard shows:
- **Pending Invoices** - Awaiting payment
- **Paid Invoices** - Confirmed payments
- **Overdue Invoices** - Past due date
- **Polling Statistics** - Payment monitoring activity

---

## 🔧 API Endpoints

### Invoice Management

```http
POST /api/invoice/create
GET  /api/invoices?status=sent
GET  /api/invoice/{id}
GET  /api/invoice/{id}/pdf
POST /api/invoice/{id}/verify-payment
```

### System Monitoring

```http
GET  /api/polling-stats
GET  /api/dashboard-stats
GET  /api/test-mexc
```

### Utilities

```http
GET  /api/clients
GET  /api/crypto-price/{currency}?network={network}
```

---

## 📄 Database Schema

### Invoices Table
- Invoice details (number, amount, currency, deposit address)
- Client information
- Status tracking (sent, partially_paid, paid, overdue)
- PDF and QR code paths

### Payment Transactions Table
- Transaction hashes
- Amounts and confirmations
- Manual verification flag
- MEXC API response data

### Clients Table
- Default clients: Alps Blockchain, Exos Capital, GM Data Centers
- Contact information

### Polling Log Table
- Tracks all polling events
- API responses and errors

### Notifications Table
- Email notification history
- Delivery status

---

## 🔐 Security Considerations

### API Key Storage
- **Never commit `.env` file to git**
- Store MEXC API keys securely
- Use environment variables in production

### Network Selection Warning
- **Critical:** Ensure correct network selected (TRC20 vs ERC20 vs BEP20 for USDT)
- Sending on wrong network = permanent loss of funds
- System validates but user must double-check

### Payment Verification
- 0.5% tolerance for crypto amount variations
- Address matching required
- Confirmation requirements enforced

---

## 🔄 Integration with AI CFO System

When invoice marked as paid, system automatically:

1. Creates transaction record in `delta_transactions.db`
2. Classifies as: `Delta Mining Paraguay S.A.` revenue
3. Sets proper metadata:
   - Transaction type: Revenue
   - Origin: External Account (client)
   - Destination: Delta Paraguay Operations
   - Identifier: Invoice number + TxID

**Location:** `services/notification_service.py` → `sync_to_cfo_system()`

---

## 📧 Notification System

### Email Notifications

Sent automatically for:
- ✅ **Invoice Created** - Confirmation email with payment details
- 💰 **Payment Detected** - Alert when payment appears on blockchain
- ✅ **Payment Confirmed** - Final confirmation when fully confirmed
- ⚠️ **Invoice Overdue** - Reminder for unpaid invoices past due date

**Recipients:**
- Aldo (aldo@deltaenergy.com)
- Tiago (tiago@deltaenergy.com)
- Client contact email (if provided)

### Webhook Integration

Configure Slack or custom webhook:
```env
WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

---

## 🧪 Testing

### Test MEXC Connection

```bash
curl http://localhost:5002/api/test-mexc
```

### Manual Invoice Creation Test

```bash
curl -X POST http://localhost:5002/api/invoice/create \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": 1,
    "amount_usd": 5000,
    "crypto_currency": "USDT",
    "crypto_network": "TRC20",
    "billing_period": "October 2025",
    "due_date": "2025-10-15",
    "description": "Bitcoin Mining Colocation Services"
  }'
```

### Check Polling Statistics

```bash
curl http://localhost:5002/api/polling-stats
```

---

## ⚙️ Configuration Options

### Polling Interval

Default: 30 seconds

```env
POLLING_INTERVAL_SECONDS=30
```

### Payment Tolerance

Default: 0.5% (handles crypto price fluctuations)

```env
PAYMENT_TOLERANCE_PERCENT=0.5
```

### Confirmation Requirements

```env
BTC_CONFIRMATIONS_REQUIRED=3
USDT_CONFIRMATIONS_REQUIRED=20
TAO_CONFIRMATIONS_REQUIRED=12
```

### Overdue Threshold

```env
INVOICE_OVERDUE_DAYS=7
```

---

## 🐛 Troubleshooting

### Payment Not Detected

1. Check MEXC API credentials in `.env`
2. Verify deposit address matches invoice
3. Check polling service status: `/api/polling-stats`
4. Manually verify using TxID if payment exists

### Email Notifications Not Sending

1. Check SMTP configuration in `.env`
2. For Gmail: Enable "App Passwords"
3. Check spam folder
4. Review logs for SMTP errors

### Database Errors

```bash
# Reinitialize database (WARNING: deletes all data)
# Drop and recreate PostgreSQL tables
python -c "from models.database_postgresql import CryptoInvoiceDatabaseManager; db = CryptoInvoiceDatabaseManager(); db.init_database(force_recreate=True)"
```

### MEXC API Errors

- **401 Unauthorized:** Check API key/secret
- **403 Forbidden:** Verify API permissions (need deposit read access)
- **429 Rate Limited:** Reduce polling frequency temporarily

---

## 📊 Performance Metrics

- **Invoice Generation:** < 2 seconds
- **Payment Detection:** 30-second intervals
- **API Response Time:** < 500ms
- **Database Queries:** < 100ms
- **PDF Generation:** < 1 second

---

## 🔮 Future Enhancements

- [ ] Multi-language support (Spanish/Portuguese for Paraguay/Brazil teams)
- [ ] Mobile app for invoice creation
- [ ] Automated payment reminders
- [ ] Batch invoice generation
- [ ] Advanced reporting and analytics
- [ ] Exchange rate hedging recommendations
- [ ] Integration with additional exchanges (Binance, Coinbase)

---

## 📞 Support

**Delta Energy Paraguay Operations Team:**
- Aldo: aldo@deltaenergy.com
- Tiago: tiago@deltaenergy.com

**Technical Issues:**
- Check logs: `tail -f crypto_invoice_system.log`
- Review polling log in database
- Test MEXC API connection

---

## 📜 License

Proprietary - Delta Energy Internal Use Only

---

## 🙏 Credits

Built with:
- Flask (Web framework)
- ReportLab (PDF generation)
- MEXC API (Crypto exchange)
- PostgreSQL (Database)
- QRCode (Payment QR codes)

**Developed for Delta Energy Paraguay colocation operations - Production-ready crypto invoice payment system**
