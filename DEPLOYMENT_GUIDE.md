# 🚀 Deployment Guide - Google Cloud Run

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **Google Cloud SDK** installed ([Install Guide](https://cloud.google.com/sdk/docs/install))
3. **Docker** installed (for local testing)
4. **GitHub repository** configured

---

## Option 1: Quick Deploy (Manual) ⚡

### Step 1: Setup Google Cloud CLI

```bash
# Login to Google Cloud
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### Step 2: Store API Keys Securely

```bash
# Create secret for Anthropic API Key
echo -n "your-anthropic-api-key-here" | \
  gcloud secrets create ANTHROPIC_API_KEY \
    --data-file=- \
    --replication-policy="automatic"

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding ANTHROPIC_API_KEY \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 3: Deploy to Cloud Run

```bash
cd DeltaCFOAgent

# Deploy from source
gcloud run deploy delta-cfo-agent \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-secrets ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest \
  --set-env-vars PYTHONPATH=/app
```

**Expected output:**
```
Service [delta-cfo-agent] revision [delta-cfo-agent-00001-xyz] has been deployed
and is serving 100 percent of traffic.
Service URL: https://delta-cfo-agent-xxxx-uc.a.run.app
```

---

## Option 2: Automated Deploy with Cloud Build (CI/CD) 🤖

### Step 1: Connect GitHub Repository

```bash
# Connect your GitHub repo to Cloud Build
gcloud beta builds triggers create github \
  --name="deploy-delta-cfo-agent" \
  --repo-name="DeltaCFOAgent" \
  --repo-owner="DeltaCompute24" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml"
```

### Step 2: Grant Permissions

```bash
# Get Cloud Build service account
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/run.admin"

# Grant Service Account User role
gcloud iam service-accounts add-iam-policy-binding \
  ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com \
  --member="serviceAccount:${CLOUD_BUILD_SA}" \
  --role="roles/iam.serviceAccountUser"
```

### Step 3: Push to GitHub

```bash
git add .
git commit -m "feat: Add Cloud Run deployment configuration"
git push origin main
```

**Cloud Build will automatically:**
1. Build the Docker image
2. Push to Container Registry
3. Deploy to Cloud Run
4. Serve at your Cloud Run URL

---

## Option 3: Firebase Hosting + Cloud Run 🔥

Use Firebase Hosting for static assets and Cloud Run for backend.

### Step 1: Install Firebase CLI

```bash
npm install -g firebase-tools
firebase login
```

### Step 2: Initialize Firebase

```bash
cd DeltaCFOAgent
firebase init hosting

# Select:
# - Use existing project (or create new)
# - Public directory: web_ui/static
# - Configure as single-page app: No
# - Set up automatic builds: Yes
```

### Step 3: Configure Firebase to Proxy to Cloud Run

Create `firebase.json`:

```json
{
  "hosting": {
    "public": "web_ui/static",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "delta-cfo-agent",
          "region": "us-central1"
        }
      },
      {
        "source": "**",
        "run": {
          "serviceId": "delta-cfo-agent",
          "region": "us-central1"
        }
      }
    ]
  }
}
```

### Step 4: Deploy

```bash
firebase deploy --only hosting
```

---

## Database Considerations 🗄️

**Current:** SQLite (file-based) - **NOT RECOMMENDED FOR PRODUCTION**

**Recommended Solutions:**

### Option A: Cloud SQL (PostgreSQL)

```bash
# Create Cloud SQL instance
gcloud sql instances create delta-cfo-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create delta_transactions \
  --instance=delta-cfo-db

# Connect Cloud Run to Cloud SQL
gcloud run services update delta-cfo-agent \
  --add-cloudsql-instances=YOUR_PROJECT_ID:us-central1:delta-cfo-db \
  --set-env-vars DATABASE_URL=postgresql://user:password@/delta_transactions?host=/cloudsql/YOUR_PROJECT_ID:us-central1:delta-cfo-db
```

### Option B: Firestore (NoSQL)

```bash
# Enable Firestore
gcloud services enable firestore.googleapis.com

# Update code to use Firestore SDK
# pip install google-cloud-firestore
```

### Option C: Cloud Storage + SQLite (Simple)

For small-scale use:
- Store SQLite file in Cloud Storage bucket
- Mount as read-only volume
- Use Cloud Storage Fuse for file access

---

## Environment Variables 🔧

Required variables for production:

```bash
ANTHROPIC_API_KEY=<your-key>    # Required for AI features
DATABASE_URL=<db-connection>     # If using Cloud SQL
PYTHONPATH=/app                  # Python module path
PORT=8080                        # Cloud Run default port
```

Set via Cloud Run:
```bash
gcloud run services update delta-cfo-agent \
  --set-env-vars KEY1=VALUE1,KEY2=VALUE2
```

---

## Monitoring & Logging 📊

### View Logs

```bash
# Real-time logs
gcloud run services logs tail delta-cfo-agent --region us-central1

# Recent logs in Cloud Console
https://console.cloud.google.com/run/detail/us-central1/delta-cfo-agent/logs
```

### Set Up Monitoring

1. Go to **Cloud Console** → **Monitoring**
2. Create alerts for:
   - High error rates
   - Slow response times (>5s)
   - Memory usage (>80%)
   - High costs

---

## Cost Optimization 💰

**Cloud Run Pricing:**
- **Free tier:** 2 million requests/month
- **Compute:** ~$0.00002400 per vCPU-second
- **Memory:** ~$0.00000250 per GiB-second
- **Requests:** $0.40 per million

**Estimated costs for low traffic:**
- ~100 requests/day: **FREE**
- ~1000 requests/day: **~$5-10/month**
- ~10000 requests/day: **~$50-100/month**

**Optimization tips:**
1. Set `--max-instances=10` to control costs
2. Use `--cpu-throttling` when idle
3. Set `--min-instances=0` for serverless cold starts
4. Use Cloud Storage for static files
5. Enable caching for API responses

---

## Security Checklist ✅

- [ ] API keys stored in Secret Manager (not in code)
- [ ] Database uses private IP (no public access)
- [ ] Cloud Run requires authentication for sensitive endpoints
- [ ] HTTPS enforced (automatic with Cloud Run)
- [ ] CORS configured properly
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] Regular security audits

---

## Testing Production Deployment 🧪

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe delta-cfo-agent \
  --region us-central1 \
  --format="value(status.url)")

# Test health endpoint
curl $SERVICE_URL/

# Test invoices API
curl $SERVICE_URL/api/invoices/stats

# Load test (optional)
ab -n 1000 -c 10 $SERVICE_URL/
```

---

## Rollback 🔄

If deployment fails or has issues:

```bash
# List revisions
gcloud run revisions list --service delta-cfo-agent --region us-central1

# Rollback to previous revision
gcloud run services update-traffic delta-cfo-agent \
  --to-revisions PREVIOUS_REVISION=100 \
  --region us-central1
```

---

## Custom Domain 🌐

### Option 1: Cloud Run Domain Mapping

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service delta-cfo-agent \
  --domain cfo.yourdomain.com \
  --region us-central1
```

### Option 2: Firebase Hosting + Custom Domain

```bash
firebase hosting:channel:deploy production
```

---

## Troubleshooting 🔧

### Common Issues:

**1. Secret not found:**
```bash
# Verify secret exists
gcloud secrets describe ANTHROPIC_API_KEY

# Re-grant permissions
gcloud secrets add-iam-policy-binding ANTHROPIC_API_KEY \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

**2. Database locked (SQLite):**
- Migrate to Cloud SQL or Firestore
- Use persistent storage volume

**3. Cold starts slow:**
```bash
# Set minimum instances
gcloud run services update delta-cfo-agent \
  --min-instances=1 \
  --region us-central1
```

**4. Memory issues:**
```bash
# Increase memory
gcloud run services update delta-cfo-agent \
  --memory=4Gi \
  --region us-central1
```

---

## Next Steps 🎯

1. ✅ Deploy to Cloud Run (test environment)
2. ✅ Configure custom domain
3. ✅ Migrate to Cloud SQL/Firestore
4. ✅ Set up CI/CD with Cloud Build
5. ✅ Configure monitoring and alerts
6. ✅ Enable authentication for admin endpoints
7. ✅ Set up backup strategy
8. ✅ Load test and optimize

---

## Support & Documentation

- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Cloud Build Docs](https://cloud.google.com/build/docs)
- [Firebase Hosting](https://firebase.google.com/docs/hosting)
- [Cloud SQL](https://cloud.google.com/sql/docs)

---

**Need help?** Open an issue on GitHub or contact the development team.
