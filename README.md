# Maily

Django Girls Colombia automated email script for workshop notifications and certificates.

## Features

This script supports sending 5 different types of workshop-related emails:

1. **`certificate`** - Post-workshop certificates for attendees
2. **`accepted-participants`** - Acceptance notifications for workshop participants  
3. **`waitlist-participants`** - Waitlist notifications for participants
4. **`accepted-mentors`** - Acceptance notifications for mentors/guides
5. **`waitlist-mentors`** - Waitlist notifications for mentors

### Local Testing Mode

The script includes a `--local` flag that generates HTML preview files instead of sending emails, perfect for testing templates and data before sending actual emails.

## Setup

### 1. Google API Credentials

Create an OAuth2.0 token here: [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)

Copy the example file and fill in your real credentials:

```bash
cp credentials.example.json credentials.json
# Edit credentials.json with your Google OAuth client_id and client_secret
```

### 2. Environment Setup

Create and activate a virtual environment:

```bash
# Create virtual environment
python3 -m venv env

# Activate the environment
# Unix/macOS
source env/bin/activate

# Windows
env\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update the values for your workshop:

```bash
cp .env.example .env
# Edit .env with your workshop-specific values
```

The script validates that all required environment variables are set at startup. If any are missing, it exits with a clear error listing them. See `.env.example` for the full list of configurable values.

### 5. Prepare Data Files

Ensure your data files are properly formatted:

- `data/attendees.csv` - Contains columns: `email`, `name`, `certificate_url`
- `data/mentors.csv` - Contains columns: `email`, `name`

## Usage

### Basic Syntax

```bash
python main.py --type <message_type> [--local] [--yes]
```

### Message Types

- `certificate` - Uses `data/attendees.csv`
- `accepted-participants` - Uses `data/attendees.csv`
- `waitlist-participants` - Uses `data/attendees.csv`
- `accepted-mentors` - Uses `data/mentors.csv`
- `waitlist-mentors` - Uses `data/mentors.csv`

### Local Testing (Recommended)

Test your templates and data before sending emails:

```bash
# Test certificate emails
python main.py --type certificate --local

# Test mentor acceptance emails  
python main.py --type accepted-mentors --local

# Test participant waitlist emails
python main.py --type waitlist-participants --local
```

HTML preview files will be generated in the `output/` directory with names like:
- `certificate_John_Doe.html`
- `accepted_mentors_Maria_Garcia.html`
- `waitlist_participants_Ana_Rodriguez.html`

### Sending Actual Emails

Remove the `--local` flag to send real emails. The script will show a summary of recipients and ask for confirmation before sending:

```bash
# Send certificate emails to all attendees (will prompt for confirmation)
python main.py --type certificate

# Send acceptance emails to all mentors (will prompt for confirmation)
python main.py --type accepted-mentors

# Skip the confirmation prompt with --yes / -y
python main.py --type accepted-mentors --yes
```

### Help

```bash
python main.py --help
```

## Templates

Templates are stored in the `templates/` directory:

- `certificate_template.html` - Certificate email template
- `accepted_participants.html` - Accepted participants template
- `waitlist_participants.html` - Participants waitlist template
- `accepted_mentors.html` - Accepted mentors template
- `waitlist_mentors.html` - Mentors waitlist template

Templates use variables like `{participant_name}`, `{workshop_date}`, `{workshop_city}`, `{workshop_website_url}`, `{whatsapp_group_link}`, `{linktree_url}`, etc., which are automatically replaced with values from the constants in `main.py`.

## Configuration

Workshop details and email settings are configured via environment variables (loaded from a `.env` file using [python-dotenv](https://github.com/theskumar/python-dotenv)). The script validates all required variables at startup and exits with an error if any are missing.

Copy `.env.example` to `.env` and customize the values. Only `IMAGE_PATH` and `EMAIL_DELAY` are optional:

- **Email:** `SENDER_EMAIL`, `EMAIL_DELAY`, `IMAGE_PATH`
- **Workshop details:** `WORKSHOP_DATE`, `WORKSHOP_TIME`, `WORKSHOP_PLACE`, `WORKSHOP_CITY`, `WORKSHOP_YEAR`, `WORKSHOP_WEBSITE_URL`
- **Mentor logistics:** `MENTOR_MEETING_DATE`, `MENTOR_MEETING_TIME`, `WORKSHOP_DAY_MENTOR_MEETING_TIME`, `MENTOR_CONFIRMATION_DEADLINE`, `MENTOR_CONFIRMATION_DATE`
- **Participant logistics:** `PARTICIPANT_CONFIRMATION_DEADLINE`, `PARTICIPANT_CONFIRMATION_DATE`
- **Links:** `SURVEY_LINK`, `PHOTOS_LINK`, `CERTIFICATE_BASE_URL`, `EMAIL_HEADER_URL`, `LINKTREE_URL`, `WHATSAPP_PARTICIPANTS_LINK`, `WHATSAPP_MENTORS_LINK`

## Security Note

Never commit `credentials.json`, `token.json`, `.env`, or `data/*.csv` files to version control. These files contain sensitive authentication information and personal data. They are included in `.gitignore` by default. Use `.env.example` as a reference template.