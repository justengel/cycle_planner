# Cycle Planner

A web application for cycle instructors to create AI-powered lesson plans with Spotify music integration.

## Features

- AI-generated lesson plans using Claude
- Spotify integration for music playback
- Customizable workout segments with tempo-matched songs
- Supabase authentication and database storage

## Requirements

- Python 3.11+
- A Supabase project
- Spotify Developer account
- Anthropic API key

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd cycle-planner
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

5. Configure environment variables (see below)

6. Run database migrations:
   ```bash
   alembic upgrade head
   ```

## Environment Variables

Create a `.env` file with the following variables:

### Claude API
- `ANTHROPIC_API_KEY` - Your Anthropic API key from https://console.anthropic.com/

### Supabase
- `SUPABASE_URL` - Your Supabase project URL (found in Settings > API)
- `SUPABASE_KEY` - Your Supabase anon/public key
- `SUPABASE_SERVICE_KEY` - Your Supabase service role key
- `DATABASE_URL` - PostgreSQL connection string (found in Settings > Database > Connection string > URI)

### App
- `APP_ENV` - Environment mode (`development` or `production`)
- `APP_SECRET_KEY` - Secret key for session management (use a random string)
- `CORS_ORIGINS` - Comma-separated list of allowed origins (e.g., `http://localhost:8000,https://yourdomain.com`)

### Spotify
Get these from https://developer.spotify.com/dashboard:
- `SPOTIFY_CLIENT_ID` - Your Spotify app client ID
- `SPOTIFY_CLIENT_SECRET` - Your Spotify app client secret
- `SPOTIFY_REDIRECT_URI` - OAuth callback URL (e.g., `http://localhost:8000/api/spotify/callback`)

### GetSongBPM (Optional)
- `GETSONGBPM_API_KEY` - API key from https://getsongbpm.com/api (used as fallback for tempo data)

## Running the Application

Start the development server:
```bash
uvicorn main:app --reload
```

The application will be available at http://localhost:8000

## Spotify Setup

1. Create an app at https://developer.spotify.com/dashboard
2. Add your redirect URI to the app settings (e.g., `http://localhost:8000/api/spotify/callback`)
3. Copy the Client ID and Client Secret to your `.env` file

## Supabase Setup

1. Create a new project at https://supabase.com
2. Copy the project URL, anon key, and service role key to your `.env` file
3. Get the database connection string from Settings > Database > Connection string > URI
4. Run migrations with `alembic upgrade head` to create the required tables
