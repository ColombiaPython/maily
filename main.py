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
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

SENDER_EMAIL = "djangogirlscolombia@gmail.com"

# Workshop details constants
WORKSHOP_DATE = "28 de marzo de 2026"
WORKSHOP_TIME = "9:00 a.m. - 4:00 p.m."
WORKSHOP_PLACE = "Evento Virtual"
WORKSHOP_CITY = "Bogotá"
WORKSHOP_WEBSITE_URL = "https://djangogirls.org/en/bogota/"
MENTOR_MEETING_DATE = "15 de julio de 2024" # Date to meet with mentors before the workshop
MENTOR_MEETING_TIME = "6:00 p.m. - 7:00 p.m." # Time for mentor meeting on the workshop day (e.g. for final instructions, Q&A, etc.)
WORKSHOP_DAY_MENTOR_MEETING_TIME = "12:00 p.m." # Time for mentor meeting on the workshop day (e.g. for final instructions, Q&A, etc.)
MENTOR_CONFIRMATION_DEADLINE = "30 de junio de 2024" # Deadline for mentors to confirm their participation before we finalize the list of accepted mentors and send out acceptance emails to participants
PARTICIPANT_CONFIRMATION_DEADLINE = "5 de julio de 2024" # Deadline for participants to confirm their participation before we finalize the list of accepted participants and send out acceptance emails to mentors
PARTICIPANT_CONFIRMATION_DATE = "10 de julio de 2024" # Date when we will send acceptance emails to participants after confirming the final list of accepted mentors
MENTOR_CONFIRMATION_DATE = "5 de julio de 2024" # Date when we will send acceptance emails to mentors after confirming the final list of accepted mentors
WORKSHOP_YEAR = "2026" # Year of the workshop, used in email templates and certificate generation

# Email configuration constants
IMAGE_PATH = None  # Set to a file path to embed a local image as <embedded_image>; None skips attachment
EMAIL_DELAY = 1  # Delay in seconds between emails

# Template variable constants
SURVEY_LINK = "https://forms.gle/mwjZZtbEaZRabbZ4A"
PHOTOS_LINK = "https://drive.google.com/drive/folders/1g4EvKQsUqqzwVOtTNzM1M5ziGSHWzOEw?usp=sharing"
CERTIFICATE_BASE_URL = "https://drive.google.com/file/"
EMAIL_HEADER_URL = "https://i.imgur.com/866NcGI.png"
LINKTREE_URL = "https://linktr.ee/djangogirlsco"
WHATSAPP_PARTICIPANTS_LINK = "https://chat.whatsapp.com/KwhazS6HFXnEmvyaaHc349?mode=wwc"
WHATSAPP_MENTORS_LINK = "https://chat.whatsapp.com/Gg99SDifbw9Ijo9OF2E5ME?mode=wwc"


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
        "accepted-participants": "templates/participantes_aceptados.html",
        "waitlist-participants": "templates/participantes_lista_espera.html",
        "accepted-mentors": "templates/guias_aceptados.html",
        "waitlist-mentors": "templates/guias_lista_espera.html"
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
