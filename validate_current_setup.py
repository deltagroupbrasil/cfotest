#!/usr/bin/env python3
"""
Validar configuração atual - verificar se Cloud Run está conectado ao Cloud SQL
"""
import subprocess
import requests
import json
import sys

def run_command(cmd):
    """Execute command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def validate_gcloud_auth():
    """Check if gcloud is authenticated"""
    print("Checking gcloud authentication...")
    stdout, stderr, code = run_command("gcloud auth list --format='value(account)' --filter='status:ACTIVE'")

    if code == 0 and stdout:
        print(f"OK: Authenticated as: {stdout}")
        return True
    else:
        print(f"FAIL: Not authenticated. Run: gcloud auth login")
        return False

def get_service_url():
    """Get Cloud Run service URL"""
    print("🔍 Getting Cloud Run service URL...")
    cmd = "gcloud run services describe deltacfoagent --region southamerica-east1 --project aicfo-473816 --format='value(status.url)'"
    stdout, stderr, code = run_command(cmd)

    if code == 0 and stdout:
        print(f"✅ Service URL: {stdout}")
        return stdout
    else:
        print(f"❌ Could not get service URL: {stderr}")
        return None

def test_health_endpoint(url):
    """Test the /health endpoint"""
    print(f"🔍 Testing health endpoint: {url}/health")
    try:
        response = requests.get(f"{url}/health", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check OK")
            print(f"   📊 Status: {data.get('status')}")
            print(f"   🗄️  Database: {data.get('database')}")
            print(f"   🕒 Timestamp: {data.get('timestamp')}")
            print(f"   📦 Version: {data.get('version')}")
            return True, data.get('database')
        else:
            print(f"❌ Health check failed: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False, None
    except requests.exceptions.Timeout:
        print("❌ Health check timeout (>30s)")
        return False, None
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False, None

def test_main_dashboard(url):
    """Test the main dashboard"""
    print(f"🔍 Testing main dashboard: {url}/")
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            print(f"✅ Dashboard OK (loaded {len(response.content)} bytes)")
            return True
        else:
            print(f"❌ Dashboard failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return False

def check_cloud_sql_connection():
    """Check Cloud SQL instance"""
    print("🔍 Checking Cloud SQL instance...")
    cmd = "gcloud sql instances describe delta-cfo-db --format='value(connectionName,ipAddresses[0].ipAddress,state)'"
    stdout, stderr, code = run_command(cmd)

    if code == 0 and stdout:
        parts = stdout.split('\t')
        connection_name = parts[0] if len(parts) > 0 else 'unknown'
        ip_address = parts[1] if len(parts) > 1 else 'unknown'
        state = parts[2] if len(parts) > 2 else 'unknown'

        print(f"✅ Cloud SQL instance found")
        print(f"   🔗 Connection: {connection_name}")
        print(f"   🌐 IP: {ip_address}")
        print(f"   📊 State: {state}")
        return True, ip_address
    else:
        print(f"❌ Could not describe Cloud SQL instance: {stderr}")
        return False, None

def main():
    print("=" * 50)
    print("DELTA CFO AGENT - VALIDATION SCRIPT")
    print("=" * 50)
    print()

    all_good = True

    # 1. Check authentication
    if not validate_gcloud_auth():
        all_good = False
    print()

    # 2. Check Cloud SQL
    sql_ok, sql_ip = check_cloud_sql_connection()
    if not sql_ok:
        all_good = False
    print()

    # 3. Get service URL
    service_url = get_service_url()
    if not service_url:
        all_good = False
    print()

    # 4. Test health endpoint
    if service_url:
        health_ok, db_type = test_health_endpoint(service_url)
        if not health_ok:
            all_good = False
        print()

        # 5. Test dashboard
        dashboard_ok = test_main_dashboard(service_url)
        if not dashboard_ok:
            all_good = False
        print()

    # Summary
    print("=" * 50)
    if all_good:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Your Delta CFO Agent is running correctly")
        if service_url:
            print(f"🌐 Access your dashboard: {service_url}")
            print(f"🏥 Health check: {service_url}/health")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("❌ Your setup needs attention")
        print("💡 Run the setup script: setup_cloud_complete.bat")

    print("=" * 50)
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())