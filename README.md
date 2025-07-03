# Gmail Package Tracker

A comprehensive Python application that automatically scans your Gmail for package tracking information using AI-powered email parsing. The system supports multiple users, provides an admin panel, and runs as a persistent service in Docker.

## Features

- **AI-Powered Email Parsing**: Uses OpenAI GPT-4 to intelligently extract package information from emails
- **Multi-User Support**: Google OAuth authentication with user management
- **Admin Panel**: Comprehensive admin interface for user and system management
- **Incremental Processing**: Initial 7-day scan, then only processes new emails
- **Background Scheduler**: Automatic email checking every 30 minutes
- **Docker Ready**: Fully containerized for easy deployment
- **Modern Web UI**: Responsive Bootstrap interface
- **Comprehensive Testing**: Full test suite with >90% coverage

## Architecture

```
Gmail Package Tracker
├── FastAPI Backend (Python 3.11)
├── SQLite Database (upgradeable to PostgreSQL)
├── Google OAuth2 Authentication
├── Gmail API Integration
├── OpenAI GPT-4 Integration
├── Background Task Scheduler
├── Modern Web Interface
└── Docker Containerization
```

## Prerequisites

1. **Google Cloud Console Setup**:
   - Create a new project in Google Cloud Console
   - Enable Gmail API and Google+ API
   - Create OAuth 2.0 credentials (Web application)
   - Add `http://localhost:8000/auth/callback` to authorized redirect URIs

2. **OpenAI API Key**:
   - Sign up at https://platform.openai.com/
   - Generate an API key from the API keys section

3. **Docker** (recommended) or Python 3.11+

## Quick Start

### Option 1: Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd gmail-package-tracker
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Configure .env file**:
   ```env
   # Google OAuth (from Google Cloud Console)
   GOOGLE_CLIENT_ID=your_google_client_id_here
   GOOGLE_CLIENT_SECRET=your_google_client_secret_here

   # OpenAI API
   OPENAI_API_KEY=your_openai_api_key_here

   # Security (generate with: openssl rand -base64 32)
   SECRET_KEY=your-super-secret-key-here

   # Admin emails (comma-separated)
   ADMIN_EMAILS=admin@example.com
   ```

4. **Start the application**:
   ```bash
   docker-compose up -d
   ```

5. **Access the application**:
   - Web Interface: http://localhost:8000
   - Health Check: http://localhost:8000/health

### Option 2: Local Development

1. **Set up Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Create necessary directories**:
   ```bash
   mkdir -p app/static app/templates
   ```

4. **Run the application**:
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Yes |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Yes |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 | Yes |
| `SECRET_KEY` | JWT signing secret | Yes |
| `ADMIN_EMAILS` | Comma-separated admin emails | Yes |
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `INITIAL_DAYS_TO_SCAN` | Days to scan on first run | No (default: 7) |
| `CHECK_INTERVAL_MINUTES` | Background check interval | No (default: 30) |

### Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Gmail API
   - Google+ API (for user info)
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Web application"
6. Add authorized redirect URIs:
   - `http://localhost:8000/auth/callback` (development)
   - `https://yourdomain.com/auth/callback` (production)

## Usage

### First Time Setup

1. **Login**: Visit the application and click "Sign in with Google"
2. **Grant Permissions**: Allow access to Gmail (read-only)
3. **Initial Scan**: The system will automatically scan the last 7 days of emails
4. **View Packages**: Check your dashboard for discovered packages

### Daily Usage

- **Automatic Processing**: The system checks for new emails every 30 minutes
- **Manual Refresh**: Click "Check for New Packages" on the dashboard
- **Package Management**: View, edit, or delete packages from the dashboard

### Admin Features

Admins can access `/admin` to:
- View all users and their status
- Activate/deactivate users
- Monitor system scheduler
- Trigger email processing for all users
- View system statistics

## API Endpoints

### Public Endpoints
- `GET /` - Redirect to dashboard
- `GET /auth/login` - Login page
- `GET /auth/google` - Google OAuth redirect
- `GET /auth/callback` - OAuth callback
- `GET /health` - Health check

### User Endpoints (Authentication Required)
- `GET /dashboard` - User dashboard
- `GET /api/packages` - Get user packages
- `POST /api/process-emails` - Trigger email processing
- `DELETE /api/packages/{id}` - Delete package

### Admin Endpoints (Admin Authentication Required)
- `GET /admin` - Admin panel
- `GET /admin/api/users` - Get all users
- `POST /admin/api/users/{id}/toggle-active` - Toggle user status
- `POST /admin/api/process-all-emails` - Process all users
- `GET /admin/api/scheduler-status` - Get scheduler status

## Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_models.py -v
```

### Test Coverage
The application includes comprehensive tests covering:
- Database models and relationships
- AI parsing functionality
- Gmail API integration
- Email processing logic
- Authentication and authorization
- API endpoints
- Error handling

## Deployment

### Production Docker Deployment

1. **Use PostgreSQL** (recommended for production):
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   services:
     package-tracker:
       build: .
       environment:
         - DATABASE_URL=postgresql://user:password@postgres:5432/package_tracker
       depends_on:
         - postgres
     
     postgres:
       image: postgres:15
       environment:
         POSTGRES_DB: package_tracker
         POSTGRES_USER: postgres
         POSTGRES_PASSWORD: your_secure_password
       volumes:
         - postgres_data:/var/lib/postgresql/data
   
   volumes:
     postgres_data:
   ```

2. **Set production environment variables**:
   ```env
   DATABASE_URL=postgresql://user:password@postgres:5432/package_tracker
   GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback
   ```

3. **Deploy**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Cloud Deployment Options

- **AWS ECS/Fargate**: Use the provided Dockerfile
- **Google Cloud Run**: Compatible with container deployment
- **DigitalOcean App Platform**: Deploy directly from repository
- **Heroku**: Use container registry deployment

## Security Considerations

- **OAuth Scopes**: Uses minimal Gmail read-only scope
- **Credential Storage**: Gmail credentials encrypted in database
- **JWT Tokens**: Secure token-based authentication
- **Admin Access**: Email-based admin authorization
- **HTTPS**: Use HTTPS in production (configure reverse proxy)

## Troubleshooting

### Common Issues

1. **"Invalid client" error**:
   - Check Google OAuth credentials
   - Verify redirect URI in Google Console

2. **"OpenAI API error"**:
   - Verify API key is correct
   - Check OpenAI account has credits

3. **No emails being processed**:
   - Check Gmail API permissions
   - Verify user credentials haven't expired
   - Check application logs

4. **Scheduler not running**:
   - Check `/admin` panel for scheduler status
   - Restart the application

### Logs

- **Docker**: `docker-compose logs -f package-tracker`
- **Local**: Application logs printed to console

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and feature requests, please create an issue in the repository.

## Acknowledgments

- FastAPI for the excellent web framework
- OpenAI for AI-powered email parsing
- Google for Gmail API access
- Bootstrap for the responsive UI
