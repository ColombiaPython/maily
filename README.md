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

Store the credentials in a file called: `credentials.json`

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

### 4. Prepare Data Files

Ensure your data files are properly formatted:

- `data/attendees.csv` - Contains columns: `email`, `name`, `certificate_url`
- `data/mentors.csv` - Contains columns: `email`, `name`

## Usage

### Basic Syntax

```bash
python main.py --type <message_type> [--local]
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

Remove the `--local` flag to send real emails:

```bash
# Send certificate emails to all attendees
python main.py --type certificate

# Send acceptance emails to all mentors
python main.py --type accepted-mentors
```

### Help

```bash
python main.py --help
```

## Templates

Templates are stored in the `templates/` directory:

- `certificate_template.html` - Certificate email template
- `participantes_aceptados.html` - Accepted participants template
- `participantes_lista_espera.html` - Participants waitlist template
- `guias_aceptados.html` - Accepted mentors template
- `guias_lista_espera.html` - Mentors waitlist template

Templates use variables like `{participant_name}`, `{mentor_name}`, `{workshop_date}`, `{email_header_url}`, etc., which are automatically replaced with actual data.

## Configuration

Workshop details and email settings are configured as constants in `main.py`:

- Workshop date, time, and location
- Survey and photo links  
- Email header image URL (`EMAIL_HEADER_URL`)
- Confirmation deadlines
- Email delay settings

## Security Note

Never commit `credentials.json` or `token.json` to version control. These files contain sensitive authentication information.