# ApplyTrack AI - Job Application Tracker

A smart, AI-powered job application tracker that automatically monitors your Gmail inbox, detects job-related emails, and keeps your application status updated without manual intervention.

## Features

- **Automatic Email Detection**: Uses AI to identify job-related emails in your Gmail
- **Smart Matching**: Matches emails to existing applications or creates new ones
- **Status Tracking**: Automatically updates application status (Applied, Assessment, Interview, Offer, Rejected, etc.)
- **Stale Detection**: Identifies applications with no recent activity
- **Follow-up Drafts**: AI-generated follow-up email drafts
- **Analytics**: Insights into your job search performance
- **Privacy First**: Read-only Gmail access - we never send emails on your behalf

## Architecture

```
frontend/ (React + Vite + TypeScript)
  |
  |-- src/
  |   |-- components/   # Reusable UI components
  |   |-- pages/        # Page components
  |   |-- layouts/      # Layout components
  |   |-- services/     # API services
  |   |-- types/        # TypeScript types
  |   |-- utils/        # Utility functions
  |   |-- App.tsx       # Main app
  |   |-- main.tsx     # Entry point
  |
  backend/ (Django + PostgreSQL)
  |
  |-- config/         # Django configuration
  |-- apps/           # Django apps
  |   |-- accounts/    # User authentication & Gmail OAuth
  |   |-- applications/# Job application tracking
  |   |-- gmail_integration/ # Gmail API integration
  |   |-- ai_processing/   # AI classification
  |   |-- analytics/   # Analytics & insights
  |-- services/       # Business logic services
  |   |-- gmail_service.py
  |   |-- groq_service.py
  |   |-- email_classifier.py
  |   |-- application_matcher.py
  |   |-- sync_service.py
  |-- manage.py
  |-- requirements.txt
  |-- .env
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (Neon recommended)
- Google OAuth credentials
- Groq API key

### Backend Setup

1. Navigate to backend directory:
   ```bash
   cd backend
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create .env file (copy from .env.example):
   ```bash
   cp .env.example .env
   ```

5. Configure environment variables in .env:
   ```env
   DJANGO_SECRET_KEY=your-secret-key
   DEBUG=True
   DATABASE_URL=your-neon-postgresql-url
   GROQ_API_KEY=your-groq-api-key
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback/
   ALLOWED_HOSTS=localhost,127.0.0.1
   CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

6. Run migrations:
   ```bash
   python manage.py migrate
   ```

7. Start development server:
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create .env file (copy from .env.example):
   ```bash
   cp .env.example .env
   ```

4. Configure environment variables in .env:
   ```env
   VITE_API_BASE_URL=http://localhost:8000/api
   ```

5. Start development server:
   ```bash
   npm run dev
   ```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API:
   - Go to APIs & Services > Library
   - Search for "Gmail API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > OAuth client ID
   - Select "Web application"
   - Add authorized redirect URI: `http://localhost:8000/api/auth/google/callback/`
5. Copy Client ID and Client Secret to backend .env

## Usage

1. Open frontend at http://localhost:5173
2. Click "Connect Gmail" to authenticate with Google
3. Grant read-only access to your Gmail
4. Click "Sync Gmail" to fetch and process emails
5. View your applications and their status in the dashboard

## API Endpoints

### Authentication
- `POST /api/auth/google/` - Initiate Google OAuth
- `GET /api/auth/google/callback/` - Handle OAuth callback
- `GET /api/auth/me/` - Get current user
- `POST /api/auth/logout/` - Logout
- `POST /api/auth/disconnect-gmail/` - Disconnect Gmail
- `GET /api/auth/settings/` - Get user settings
- `PATCH /api/auth/settings/` - Update user settings

### Applications
- `GET /api/applications/` - List applications
- `POST /api/applications/` - Create application
- `GET /api/applications/:id/` - Get application
- `PATCH /api/applications/:id/` - Update application
- `DELETE /api/applications/:id/` - Delete application
- `GET /api/applications/stats/` - Get application stats
- `GET /api/applications/:id/history/` - Get status history
- `GET /api/applications/:id/followups/` - List follow-ups
- `POST /api/applications/:id/followups/` - Create follow-up
- `POST /api/applications/:id/followups/draft/` - Generate follow-up draft

### Emails
- `GET /api/emails/` - List processed emails
- `GET /api/emails/:id/` - Get processed email
- `POST /api/emails/:id/review/` - Mark email as reviewed
- `POST /api/emails/:id/ignore/` - Ignore email
- `GET /api/emails/sync-logs/` - List sync logs

### Gmail
- `POST /api/gmail/sync/` - Trigger Gmail sync

### Analytics
- `GET /api/analytics/` - Get user analytics

## Project Structure

### Backend Models

- **CustomUser**: User model with Gmail OAuth tokens
- **UserSettings**: Extended user preferences
- **Application**: Job application tracking
- **StatusHistory**: Application status change history
- **FollowUp**: Follow-up email drafts
- **ProcessedEmail**: Processed Gmail messages
- **SyncLog**: Gmail sync operation logs
- **AIRequestLog**: AI API request logs
- **UserAnalytics**: Aggregated analytics data

### Services

- **GmailService**: Gmail API integration
- **GroqService**: Groq AI API integration
- **EmailClassifier**: Rule-based email filtering
- **ApplicationMatcher**: Email to application matching
- **SyncService**: Email processing pipeline

## Technology Stack

- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons
- **Backend**: Django 4.2, Django REST Framework, PostgreSQL
- **AI**: Groq API (Llama 3.1)
- **Authentication**: Google OAuth 2.0
- **Database**: Neon PostgreSQL

## Privacy & Security

- Read-only Gmail access (no send/delete/modify permissions)
- All sensitive data stored in environment variables
- OAuth tokens stored securely in database
- No full email bodies stored permanently
- User data isolated by user ID

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License
