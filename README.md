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

### 4. Prepare Data Files

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
- `participantes_aceptados.html` - Accepted participants template
- `participantes_lista_espera.html` - Participants waitlist template
- `guias_aceptados.html` - Accepted mentors template
- `guias_lista_espera.html` - Mentors waitlist template

Templates use variables like `{participant_name}`, `{workshop_date}`, `{workshop_city}`, `{workshop_website_url}`, `{whatsapp_group_link}`, `{linktree_url}`, etc., which are automatically replaced with values from the constants in `main.py`.

## Configuration

Workshop details and email settings are configured as constants at the top of `main.py`:

- **Workshop details:** date, time, location, city, year, website URL
- **Mentor logistics:** meeting date/time, confirmation deadlines
- **Participant logistics:** confirmation deadlines and dates
- **Links:** survey, photos, email header image, Linktree, WhatsApp groups (separate for participants and mentors)
- **Email settings:** sender email, delay between emails

## Security Note

Never commit `credentials.json`, `token.json`, or `data/*.csv` files to version control. These files contain sensitive authentication information and personal data. They are included in `.gitignore` by default.