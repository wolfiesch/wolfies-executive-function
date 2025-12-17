#!/usr/bin/env python3
"""
Google Calendar OAuth2 Setup Script

This script helps you set up OAuth2 credentials for the Google Calendar MCP server.

Steps:
1. Create a Google Cloud Console project
2. Enable Google Calendar API
3. Create OAuth2 credentials
4. Download credentials.json
5. Run this script to complete authentication

Usage:
    python scripts/setup_google_oauth.py
"""

import sys
import json
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_DIR = PROJECT_ROOT / "config" / "google_credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "credentials.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"


def print_instructions():
    """Print setup instructions."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║         Google Calendar MCP Server - OAuth2 Setup Instructions           ║
╚═══════════════════════════════════════════════════════════════════════════╝

To use the Google Calendar MCP server, you need to set up OAuth2 credentials.

STEP 1: Create a Google Cloud Console Project
──────────────────────────────────────────────
1. Go to: https://console.cloud.google.com/
2. Click "Select a project" → "New Project"
3. Name it "Life Planner Calendar" (or any name you prefer)
4. Click "Create"

STEP 2: Enable Google Calendar API
────────────────────────────────────
1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Calendar API"
3. Click on it and click "Enable"

STEP 3: Create OAuth2 Credentials
──────────────────────────────────
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External (unless you have a Google Workspace)
   - App name: "Life Planner Calendar"
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add "Google Calendar API" → "../auth/calendar"
   - Test users: Add your Gmail address
   - Click "Save and Continue" through the rest
4. Back to "Create OAuth client ID":
   - Application type: "Desktop app"
   - Name: "Life Planner MCP"
   - Click "Create"
5. Click "Download JSON" on the credentials you just created

STEP 4: Save Credentials File
──────────────────────────────
1. Rename the downloaded file to "credentials.json"
2. Move it to: {credentials_dir}

STEP 5: Run Authentication
───────────────────────────
After placing credentials.json, run this script again to complete setup.

═══════════════════════════════════════════════════════════════════════════

""".format(credentials_dir=CREDENTIALS_DIR))


def check_credentials():
    """Check if credentials.json exists."""
    if not CREDENTIALS_FILE.exists():
        print(f"❌ Credentials file not found: {CREDENTIALS_FILE}\n")
        return False

    # Validate JSON format
    try:
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)

        # Check for required fields
        if "installed" not in creds and "web" not in creds:
            print("❌ Invalid credentials.json format")
            print("   Expected 'installed' or 'web' key not found\n")
            return False

        print(f"✓ Found credentials.json: {CREDENTIALS_FILE}\n")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in credentials.json: {e}\n")
        return False


def run_authentication():
    """Run OAuth flow to get token."""
    print("Starting OAuth2 authentication flow...\n")

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        SCOPES = ['https://www.googleapis.com/auth/calendar']

        creds = None

        # Check if token already exists
        if TOKEN_FILE.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
                print("✓ Found existing token.json")
            except Exception as e:
                print(f"⚠ Existing token.json is invalid: {e}")
                creds = None

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired token...")
                try:
                    creds.refresh(Request())
                    print("✓ Token refreshed successfully")
                except Exception as e:
                    print(f"❌ Failed to refresh token: {e}")
                    print("Will obtain new credentials...\n")
                    creds = None

            if not creds:
                print("Opening browser for OAuth2 authentication...")
                print("Please sign in with your Google account and grant permissions.\n")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)

                print("\n✓ Authentication successful!")

        # Save credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

        print(f"✓ Saved token to: {TOKEN_FILE}\n")

        # Test the credentials
        print("Testing Google Calendar API access...")
        from googleapiclient.discovery import build

        service = build('calendar', 'v3', credentials=creds)

        # Try to fetch calendar list
        calendars_result = service.calendarList().list(maxResults=5).execute()
        calendars = calendars_result.get('items', [])

        print(f"✓ Successfully accessed Google Calendar API")
        print(f"✓ Found {len(calendars)} calendar(s) in your account\n")

        if calendars:
            print("Available calendars:")
            for cal in calendars:
                cal_id = cal['id']
                cal_name = cal.get('summary', 'No name')
                is_primary = " (PRIMARY)" if cal.get('primary') else ""
                print(f"  - {cal_name}{is_primary}")
                print(f"    ID: {cal_id}")
            print()

        return True

    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("\nPlease install dependencies:")
        print("  cd src/integrations/google_calendar/")
        print("  pip install -r requirements.txt\n")
        return False

    except Exception as e:
        print(f"❌ Authentication failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main setup flow."""
    print_instructions()

    # Ensure credentials directory exists
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if credentials.json exists
    if not check_credentials():
        print("Please complete the steps above to obtain credentials.json")
        print(f"Then save it to: {CREDENTIALS_FILE}\n")
        return 1

    # Run authentication
    if not run_authentication():
        print("Setup failed. Please check the error messages above.\n")
        return 1

    # Success
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                          Setup Complete! ✓                                ║
╚═══════════════════════════════════════════════════════════════════════════╝

Your Google Calendar MCP server is now configured.

Next Steps:
───────────
1. Register the MCP server with Claude Code:

   claude mcp add -t stdio google-calendar -- \\
     python3 {server_path}

2. Restart Claude Code to load the new MCP server

3. Test the server:
   - "Show my calendar for this week"
   - "Find free time for a 30 minute meeting"
   - "Create an event tomorrow at 2pm called Team Sync"

Credentials stored in:
  {credentials_dir}

Note: Keep credentials.json and token.json private!
They are already in .gitignore and won't be committed.

═══════════════════════════════════════════════════════════════════════════
""".format(
        server_path=PROJECT_ROOT / "src/integrations/google_calendar/server.py",
        credentials_dir=CREDENTIALS_DIR
    ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
