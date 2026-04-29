# Vercel + Django Deployment Guide

## 🚨 Required Environment Variables

Set these in Vercel Dashboard → Project Settings → Environment Variables:

```
DJANGO_SETTINGS_MODULE=DoctorX.settings
DEBUG=false
SECRET_KEY=your-actual-secret-key-here
DATABASE_URL=postgresql://neondb_owner:npg_T0YBXCPNQ3Hk@ep-misty-surf-a7k9k9ds-pooler.ap-southeast-2.aws.neon.tech/neondb?channel_binding=require&sslmode=require
```

## ✅ Two Valid Vercel Configurations

### OPTION A: Minimal Safe Setup (Recommended)
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "installCommand": "pip install -r requirements.txt"
}
```

**When to use**: API-heavy apps, avoid build failures, serverless-first approach

### OPTION B: With Static Files (Use with caution)
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "installCommand": "pip install -r requirements.txt",
  "buildCommand": "python manage.py collectstatic --noinput"
}
```

**When to use**: Django admin panel, heavy template usage, static assets critical

## ⚠️ Critical Truth About Vercel + Django

### buildCommand is NOT Required
- ❌ Django can run without `collectstatic` on Vercel
- ❌ Serverless functions don't need pre-collected static files
- ❌ `buildCommand` can cause deployment failures

### Static Files on Vercel
- ⚠️ No guaranteed filesystem persistence
- ⚠️ May fail if environment variables missing
- ⚠️ Consider CDN/external hosting for production

### Serverless Reality
- 🔄 Cold starts are normal
- 🔄 Each request spins up new function
- 🔄 Traditional server assumptions don't apply

## 🚀 Deployment Steps

1. Set environment variables in Vercel Dashboard
2. Choose OPTION A or B configuration
3. Deploy to Vercel
4. Run migrations manually (Neon DB)
5. Test the application

## 🐛 Common Issues & Solutions

| Issue | Cause | Solution |
|-------|--------|----------|
| 500 Errors | Missing env vars | Check Vercel Dashboard settings |
| Static 404s | WhiteNoise not configured | Ensure STATIC_URL/STATIC_ROOT set |
| Build Failures | collectstatic errors | Use OPTION A (no buildCommand) |
| Cold Starts | Serverless nature | Normal, improves after first request |
| DB Issues | DATABASE_URL wrong | Verify Neon connection string |

## 🧠 Final Recommendation

Start with **OPTION A** (minimal setup). Only add `buildCommand` if you specifically need Django admin panel or heavy static file serving.

## 🚨 Server Validation Issues - Neon Database

### If you're getting server validation errors:

**1. Check Vercel Environment Variables**
- Go to Vercel Dashboard → Project Settings → Environment Variables
- Ensure these are set exactly:
```
DJANGO_SETTINGS_MODULE=DoctorX.settings
DATABASE_URL=postgresql://neondb_owner:npg_T0YBXCPNQ3Hk@ep-misty-surf-a7k9k9ds-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
SECRET_KEY=django-insecure-h%w_r)+r4_dp4$20+^cu=70k$miegazaf44dwr*t2_hfsk3m+q
DEBUG=false
```

**2. Common Neon Issues**
- Connection timeout: Check if Neon database is active
- SSL errors: Ensure `sslmode=require` is in DATABASE_URL
- Pooler vs Direct: Try removing `&channel_binding=require` if issues persist

**3. Test Connection Locally First**
```bash
python -c "import psycopg2; psycopg2.connect('your_database_url'); print('Connection works')"
```

**4. Vercel Deployment Logs**
- Check Vercel Dashboard → Functions → Logs
- Look for database connection errors
- Verify environment variables are loaded correctly
