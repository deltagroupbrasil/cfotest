#!/usr/bin/env python3
"""
Vercel entry point for Delta CFO Agent
"""
import sys
import os

# Add the parent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the Flask app from web_ui
from web_ui.app_db import app

# For Vercel, we need to export the app
if __name__ == "__main__":
    app.run()