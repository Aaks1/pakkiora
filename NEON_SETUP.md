# Neon PostgreSQL Setup for Django

This guide shows how to connect your Django project to Neon PostgreSQL with minimal configuration.

## Step 1: Create Neon Database

1. Go to [https://neon.tech](https://neon.tech)
2. Sign up for a free account
3. Create a new project:
   - Click "New Project"
   - Choose a project name
   - Select a region (closest to your users)
   - Click "Create Project"
4. Get your connection string:
   - Go to your project dashboard
   - Click "Connection Details"
   - Copy the connection string (looks like: `postgresql://username:password@host:5432/database_name?sslmode=require`)

## Step 2: Install Required Packages

Your project already has the necessary packages. If you need to install them:

```bash
pip install psycopg2-binary dj-database-url python-dotenv
```

## Step 3: Configure Environment Variables

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` file with your Neon database URL:
```env
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=False

# Neon PostgreSQL Database (paste your connection string here)
DATABASE_URL=postgresql://your_username:your_password@your_host:5432/your_database?sslmode=require
```

## Step 4: Apply Database Migrations

1. Activate your virtual environment:
```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Apply migrations to create database tables:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Create a superuser (optional):
```bash
python manage.py createsuperuser
```

## Step 5: Test the Connection

Run the development server to verify everything works:
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` to test the database connection.

## Environment Variables Explained

- `DATABASE_URL`: Your Neon PostgreSQL connection string with SSL enabled
- `SECRET_KEY`: Your Django secret key (generate with `python generate_secret_key.py`)
- `DEBUG`: Set to `False` in production

## How It Works

The Django settings automatically detect if `DATABASE_URL` is set:
- **If DATABASE_URL exists**: Uses Neon PostgreSQL
- **If DATABASE_URL is missing**: Falls back to SQLite for development

This allows seamless development with SQLite and production deployment with Neon.

## SSL Configuration

Neon requires SSL connections. The `sslmode=require` parameter in your connection string ensures secure connections automatically.

## Deployment

When deploying to Vercel or other platforms:
1. Set `DATABASE_URL` as an environment variable in your deployment platform
2. Set `DEBUG=False`
3. Set `SECRET_KEY` to a secure value
4. Deploy your application

The application will automatically use Neon when `DATABASE_URL` is configured.

## Troubleshooting

### Connection Issues
- Verify your `DATABASE_URL` is correct
- Check that SSL is enabled (`sslmode=require`)
- Ensure your Neon project is active

### Migration Issues
- Run `python manage.py migrate` after setting up the database
- If switching from SQLite, you may need to reset migrations

### Performance
- Neon handles connection pooling automatically
- No additional configuration needed for basic use
