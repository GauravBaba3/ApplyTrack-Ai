# Welcome to ApplyTrack AI!

Your complete job application tracker has been built and is ready for setup.

## Quick Start

### 1. Set Up Google OAuth

The backend .env file has placeholders for Google OAuth credentials. You need to:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Web Application type)
5. Add authorized redirect URI: `http://localhost:8000/api/auth/google/callback/`
6. Copy the Client ID and Client Secret to `backend/.env`

### 2. Install Backend Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run Database Migrations

```bash
python manage.py migrate
```

### 4. Start Backend Server

```bash
python manage.py runserver
```

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 6. Start Frontend Server

```bash
npm run dev
```

### 7. Access the Application

Open your browser to: http://localhost:5173

## What You Get

✅ **Automatic Email Detection** - AI identifies job-related emails in your Gmail
✅ **Smart Matching** - Matches emails to existing applications or creates new ones
✅ **Status Tracking** - Automatic updates for Applied, Assessment, Interview, Offer, Rejected
✅ **Dashboard** - Real-time overview of all your applications
✅ **Analytics** - Insights into your job search performance
✅ **Follow-up Drafts** - AI-generated follow-up email suggestions
✅ **Privacy** - Read-only Gmail access, your data is secure

## Important Notes

1. **Credentials**: The backend .env already contains:
   - ✅ Groq API Key
   - ✅ Neon PostgreSQL URL
   - ❌ Google OAuth credentials (you need to add these)

2. **First Run**: After setting up Google OAuth, visit http://localhost:5173 and click "Connect Gmail"

3. **Sync**: After connecting Gmail, click "Sync Gmail" to process your emails

4. **Review**: Check the "Needs Review" section for uncertain classifications

## Project Structure

```
job-application-tracker/
├── backend/          # Django backend
│   ├── config/       # Django configuration
│   ├── apps/         # Django applications
│   ├── services/     # Business logic services
│   └── manage.py     # Django management
│
└── frontend/         # React frontend
    ├── src/          # Source code
    │   ├── components/  # Reusable components
    │   ├── pages/       # Page components
    │   ├── layouts/     # Layouts
    │   ├── services/    # API client
    │   └── App.tsx      # Main app
    └── package.json   # Dependencies
```

## Documentation

- [Full Documentation](README.md)
- [Project Summary](PROJECT_SUMMARY.md)

## Support

If you have any issues or questions:
1. Check the .env files for missing credentials
2. Verify Google OAuth is properly configured
3. Check the console logs for errors
4. Review the documentation files

Enjoy your automated job application tracking! 🎉
