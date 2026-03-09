import os
import os.path
import base64
import csv
import re
import sys
import argparse
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from time import sleep
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()


def _validate_env():
    """Validate that all required environment variables are set."""
    required = [
        "SENDER_EMAIL",
        "WORKSHOP_DATE", "WORKSHOP_TIME", "WORKSHOP_PLACE", "WORKSHOP_CITY",
        "WORKSHOP_WEBSITE_URL", "WORKSHOP_YEAR",
        "MENTOR_MEETING_DATE", "MENTOR_MEETING_TIME",
        "WORKSHOP_DAY_MENTOR_MEETING_TIME",
        "MENTOR_CONFIRMATION_DEADLINE", "MENTOR_CONFIRMATION_DATE",
        "PARTICIPANT_CONFIRMATION_DEADLINE", "PARTICIPANT_CONFIRMATION_DATE",
        "SURVEY_LINK", "PHOTOS_LINK", "CERTIFICATE_BASE_URL",
        "EMAIL_HEADER_URL", "LINKTREE_URL",
        "WHATSAPP_PARTICIPANTS_LINK", "WHATSAPP_MENTORS_LINK",
    ]
    missing = [v for v in required if os.getenv(v) is None]
    if missing:
        sys.exit(f"Missing required environment variables: {', '.join(missing)}")


_validate_env()

# If modifying these SCOPES, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# Workshop details constants
WORKSHOP_DATE = os.getenv("WORKSHOP_DATE")
WORKSHOP_TIME = os.getenv("WORKSHOP_TIME")
WORKSHOP_PLACE = os.getenv("WORKSHOP_PLACE")
WORKSHOP_CITY = os.getenv("WORKSHOP_CITY")
WORKSHOP_WEBSITE_URL = os.getenv("WORKSHOP_WEBSITE_URL")
MENTOR_MEETING_DATE = os.getenv("MENTOR_MEETING_DATE")
MENTOR_MEETING_TIME = os.getenv("MENTOR_MEETING_TIME")
WORKSHOP_DAY_MENTOR_MEETING_TIME = os.getenv("WORKSHOP_DAY_MENTOR_MEETING_TIME")
MENTOR_CONFIRMATION_DEADLINE = os.getenv("MENTOR_CONFIRMATION_DEADLINE")
PARTICIPANT_CONFIRMATION_DEADLINE = os.getenv("PARTICIPANT_CONFIRMATION_DEADLINE")
PARTICIPANT_CONFIRMATION_DATE = os.getenv("PARTICIPANT_CONFIRMATION_DATE")
MENTOR_CONFIRMATION_DATE = os.getenv("MENTOR_CONFIRMATION_DATE")
WORKSHOP_YEAR = os.getenv("WORKSHOP_YEAR")

# Email configuration constants (optional, with defaults)
IMAGE_PATH = os.getenv("IMAGE_PATH")  # Set to a file path to embed a local image as <embedded_image>; None skips attachment
EMAIL_DELAY = int(os.getenv("EMAIL_DELAY", "1"))  # Delay in seconds between emails

# Template variable constants
SURVEY_LINK = os.getenv("SURVEY_LINK")
PHOTOS_LINK = os.getenv("PHOTOS_LINK")
CERTIFICATE_BASE_URL = os.getenv("CERTIFICATE_BASE_URL")
EMAIL_HEADER_URL = os.getenv("EMAIL_HEADER_URL")
LINKTREE_URL = os.getenv("LINKTREE_URL")
WHATSAPP_PARTICIPANTS_LINK = os.getenv("WHATSAPP_PARTICIPANTS_LINK")
WHATSAPP_MENTORS_LINK = os.getenv("WHATSAPP_MENTORS_LINK")


def authenticate_gmail():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def send_email(service, user_id, message):
    message = (
        service.users().messages().send(userId=user_id, body=message).execute()
    )
    print(f"Message Id: {message['id']}")
    return message


def create_message(sender, to, subject, message_text, image_path):
    message = MIMEMultipart("related")
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject

    msg_alternative = MIMEMultipart("alternative")
    msg = MIMEText(message_text, "html")

    msg_alternative.attach(msg)
    message.attach(msg_alternative)

    # Attach the image if provided
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            img = MIMEImage(img_file.read())
            img.add_header("Content-ID", "<embedded_image>")
            img.add_header(
                "Content-Disposition", "inline", filename=os.path.basename(image_path)
            )
            message.attach(img)

    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    return {"raw": raw}


def read_csv(file_name):
    with open(file_name, mode="r", newline="", encoding="utf-8") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        data = list(csv_reader)
    return data


def get_recipients(file_name):
    try:
        return read_csv(file_name)
    except FileNotFoundError:
        print(f"Error: CSV file '{file_name}' not found")
        return []
    except csv.Error as e:
        print(f"Error reading CSV file: {e}")
        return []


def load_and_validate_recipients(message_type):
    is_mentor = "mentors" in message_type
    file_name = "data/mentors.csv" if is_mentor else "data/attendees.csv"

    recipients = get_recipients(file_name)
    if not recipients:
        print(f"No recipients found in '{file_name}'")
        return [], []

    # Validate required CSV columns
    required_fields = {"email", "name"}
    if message_type == "certificate":
        required_fields.add("certificate_url")
    missing = required_fields - recipients[0].keys()
    if missing:
        print(f"Error: CSV missing required columns: {missing}")
        return [], []

    valid, skipped = [], []
    for row in recipients:
        email = row.get("email", "").strip()
        name = row.get("name", "").strip()
        if not email or not name:
            skipped.append(row)
            continue
        if message_type == "certificate" and not row.get("certificate_url", "").strip():
            skipped.append(row)
            continue
        valid.append(row)

    for s in skipped:
        print(f"Warning: Skipping invalid row: {s}")

    return valid, skipped


def load_html_template(template_path, context):
    # Read template as-is. We intentionally avoid using str.format on the
    # full HTML because the file contains CSS/JS with curly braces which
    # would be interpreted as format fields and cause errors.
    with open(template_path, "r", encoding="utf-8") as file:
        template = file.read()

    # Safely replace only the placeholders that match our context keys,
    # e.g. {name}, {survey_link}, etc. This avoids touching other braces
    # used in CSS or HTML attributes.
    for key, value in context.items():
        placeholder = "{" + key + "}"
        template = template.replace(placeholder, str(value) if value is not None else "")

    return template


def send_bulk_message(service, template, message_type, subject, context_extras,
                      local_mode=False, preloaded_recipients=None):
    is_mentor = "mentors" in message_type
    name_key = "mentor_name" if is_mentor else "participant_name"

    if preloaded_recipients is not None:
        recipients = preloaded_recipients
    else:
        recipients, _ = load_and_validate_recipients(message_type)
        if not recipients:
            return 0, []

    if local_mode:
        os.makedirs("output", exist_ok=True)

    sent_count = 0
    failures = []
    safe_name_counts = {}
    for recipient in recipients:
        receiver_email = recipient.get("email", "").strip()
        name = recipient.get("name", "").strip()

        context = {
            name_key: name,
            "workshop_date": WORKSHOP_DATE,
            "workshop_time": WORKSHOP_TIME,
            "workshop_place": WORKSHOP_PLACE,
            "workshop_year": WORKSHOP_YEAR,
            "workshop_city": WORKSHOP_CITY,
            "workshop_website_url": WORKSHOP_WEBSITE_URL,
            "email_header_url": EMAIL_HEADER_URL,
            "sender_email": SENDER_EMAIL,
            "linktree_url": LINKTREE_URL,
            **context_extras,
        }

        # Add per-recipient fields (e.g. certificate_url)
        if message_type == "certificate":
            context["survey_link"] = SURVEY_LINK
            context["photos_link"] = PHOTOS_LINK
            context["certificate_url"] = recipient.get("certificate_url")

        # Add mentor-specific variables
        if is_mentor:
            context.update({
                "mentor_meeting_date": MENTOR_MEETING_DATE,
                "mentor_meeting_time": MENTOR_MEETING_TIME,
                "workshop_day_mentor_meeting_time": WORKSHOP_DAY_MENTOR_MEETING_TIME,
            })

        html_content = load_html_template(template, context)

        if local_mode:
            safe_name = re.sub(r'[^\w\-]', '_', name)
            safe_name_counts[safe_name] = safe_name_counts.get(safe_name, 0) + 1
            if safe_name_counts[safe_name] > 1:
                safe_name = f"{safe_name}_{safe_name_counts[safe_name]}"
            output_file = f"output/{message_type.replace('-', '_')}_{safe_name}.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved preview: {output_file}")
            sent_count += 1
        else:
            try:
                message = create_message(
                    SENDER_EMAIL, receiver_email, subject, html_content, IMAGE_PATH
                )
                send_email(service, "me", message)
                sent_count += 1
            except Exception as e:
                print(f"Failed to send to {receiver_email}: {e}")
                failures.append({"email": receiver_email, "name": name, "error": str(e)})
            sleep(EMAIL_DELAY)

    return sent_count, failures


def setup_argument_parser():
    """Set up command line argument parser"""
    parser = argparse.ArgumentParser(description="Send automated emails via Gmail")
    
    parser.add_argument(
        "--type", 
        choices=["certificate", "accepted-participants", "waitlist-participants", "accepted-mentors", "waitlist-mentors"],
        required=True,
        help="Type of email to send"
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help="Run the script in local mode so it can be tested without sending emails"
    )

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt and send emails immediately"
    )

    return parser


def get_default_template(msg_type):
    """Get default template based on message type"""
    templates = {
        "certificate": "templates/certificate_template.html",
        "accepted-participants": "templates/accepted_participants.html",
        "waitlist-participants": "templates/waitlist_participants.html",
        "accepted-mentors": "templates/accepted_mentors.html",
        "waitlist-mentors": "templates/waitlist_mentors.html"
    }
    return templates.get(msg_type)


def main():
    # Parse command line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()

    print(f"Running script with type: {args.type}")

    if args.local:
        print("Running in local mode. No emails will be sent.")
        print("HTML preview files will be saved to the 'output/' directory.")
    else:
        print("Running in email mode. Emails will be sent via Gmail.")
    
    # Set template
    template = get_default_template(args.type)
    if not template or not os.path.exists(template):
        print(f"Error: Template file '{template}' not found")
        sys.exit(1)
    
    # Authenticate and build the service (only if not in local mode)
    service = None
    if not args.local:
        creds = authenticate_gmail()
        service = build("gmail", "v1", credentials=creds)
    
    # Map message types to subjects and extra context variables
    subject_map = {
        "certificate": "Django Girls Colombia - Tu Certificado del Taller",
        "accepted-participants": "Django Girls Colombia - ¡Has sido aceptada!",
        "accepted-mentors": "Django Girls Colombia - ¡Has sido aceptada como guía!",
        "waitlist-participants": "Django Girls Colombia - Lista de Espera",
        "waitlist-mentors": "Django Girls Colombia - Lista de Espera para Guías",
    }
    extras_map = {
        "certificate": {},
        "accepted-participants": {
            "participant_confirmation_deadline": PARTICIPANT_CONFIRMATION_DEADLINE,
            "whatsapp_group_link": WHATSAPP_PARTICIPANTS_LINK,
        },
        "accepted-mentors": {
            "mentor_confirmation_deadline": MENTOR_CONFIRMATION_DEADLINE,
            "whatsapp_group_link": WHATSAPP_MENTORS_LINK,
        },
        "waitlist-participants": {"participant_confirmation_date": PARTICIPANT_CONFIRMATION_DATE},
        "waitlist-mentors": {"mentor_confirmation_date": MENTOR_CONFIRMATION_DATE},
    }

    # Load and validate recipients
    recipients, skipped = load_and_validate_recipients(args.type)
    if not recipients:
        print("No valid recipients found. Exiting.")
        sys.exit(1)

    # Pre-send summary and confirmation (email mode only)
    if not args.local:
        print(f"\n--- Pre-send Summary ---")
        print(f"Email type: {args.type}")
        print(f"Recipients: {len(recipients)}")
        if skipped:
            print(f"Skipped rows: {len(skipped)}")
        print("Addresses:")
        for r in recipients:
            print(f"  - {r.get('name')} <{r.get('email')}>")

        if not args.yes:
            confirm = input(f"\nSend {len(recipients)} emails? [y/N]: ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                sys.exit(0)

    sent_msgs = 0
    failures = []
    try:
        sent_msgs, failures = send_bulk_message(
            service, template, args.type,
            subject_map[args.type], extras_map[args.type],
            args.local, preloaded_recipients=recipients,
        )
    except Exception as e:
        print(f"Error processing messages: {e}")
        sys.exit(1)

    if failures:
        print(f"\n--- {len(failures)} FAILED recipients ---")
        for f in failures:
            print(f"  {f['email']} ({f['name']}): {f['error']}")

    if args.local:
        print(f"\nFinished generating {sent_msgs} preview HTML files of type '{args.type}'")
    else:
        print(f"\nFinished sending {sent_msgs} emails of type '{args.type}'")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
