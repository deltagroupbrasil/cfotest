#!/bin/bash
# Start Crypto Invoice System with environment variables

cd "$(dirname "$0")"

# Export environment variables
export MEXC_API_KEY="mx0vglFBKknNUwIGuR"
export MEXC_API_SECRET="c4eeba8fd03f4132bb34b48e30e84872"
export FLASK_PORT=5003
export FLASK_ENV=production
export FLASK_DEBUG=False

# Start server
python3 api/invoice_api.py
