#!/usr/bin/env python3
"""
Delta CFO Agent Setup Script
Quick setup for new developers
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Ensure Python 3.9+ is being used"""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")

def setup_environment():
    """Create .env file from example if it doesn't exist"""
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from example...")
        with open(env_example) as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("⚠️  Please edit .env file and add your ANTHROPIC_API_KEY")
        return False
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def check_api_key():
    """Check if API key is configured"""
    api_key_file = Path(".anthropic_api_key")
    env_file = Path(".env")

    if api_key_file.exists():
        print("✅ API key found in .anthropic_api_key")
        return True
    elif env_file.exists():
        with open(env_file) as f:
            if "ANTHROPIC_API_KEY=" in f.read():
                print("✅ API key found in .env file")
                return True

    print("⚠️  No API key found. Please:")
    print("   1. Add your key to .env file, OR")
    print("   2. Create .anthropic_api_key file with your key")
    return False

def main():
    """Main setup function"""
    print("🚀 Delta CFO Agent Setup")
    print("=" * 30)

    check_python_version()

    if not install_dependencies():
        sys.exit(1)

    env_ready = setup_environment()
    api_ready = check_api_key()

    print("\n" + "=" * 30)
    if env_ready and api_ready:
        print("✅ Setup complete! Ready to start development.")
        print("\n🎯 Next steps:")
        print("   cd web_ui && python app_db.py")
        print("   Open: http://localhost:5002")
    else:
        print("⚠️  Setup incomplete. Please configure your API key.")

    print("\n📚 Documentation:")
    print("   PROJECT_VISION.md - Project roadmap")
    print("   CONTRIBUTING.md - Development guide")

if __name__ == "__main__":
    main()