#!/usr/bin/env python3
"""
Simple validation script for Cloud Run + Cloud SQL setup
"""
import subprocess
import requests
import sys

def run_command(cmd):
    """Execute command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def main():
    print("=" * 60)
    print("DELTA CFO AGENT - VALIDATION SCRIPT")
    print("=" * 60)
    print()

    # Get service URL
    print("1. Getting Cloud Run service URL...")
    cmd = "gcloud run services describe deltacfoagent --region southamerica-east1 --project aicfo-473816 --format='value(status.url)'"
    stdout, stderr, code = run_command(cmd)

    if code == 0 and stdout:
        service_url = stdout
        print(f"   OK: {service_url}")
    else:
        print(f"   FAIL: {stderr}")
        return 1

    # Test health endpoint
    print("\n2. Testing health endpoint...")
    try:
        response = requests.get(f"{service_url}/health", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"   OK: Status = {data.get('status')}")
            print(f"   Database: {data.get('database')}")
        else:
            print(f"   FAIL: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return 1
    except Exception as e:
        print(f"   FAIL: {e}")
        return 1

    # Test dashboard
    print("\n3. Testing main dashboard...")
    try:
        response = requests.get(service_url, timeout=30)
        if response.status_code == 200:
            print(f"   OK: Dashboard loaded ({len(response.content)} bytes)")
        else:
            print(f"   FAIL: HTTP {response.status_code}")
            return 1
    except Exception as e:
        print(f"   FAIL: {e}")
        return 1

    print("\n" + "=" * 60)
    print("SUCCESS: All tests passed!")
    print(f"Dashboard URL: {service_url}")
    print(f"Health Check: {service_url}/health")
    print("=" * 60)

    return 0

if __name__ == "__main__":
    sys.exit(main())