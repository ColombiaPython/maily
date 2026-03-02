import os.path
import base64
import csv
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

WORKSHOP_DATE = "20 de julio de 2024"
WORKSHOP_TIME = "9:00 a.m. - 5:00 p.m."
WORKSHOP_PLACE = "Bogotá, Colombia"
MENTOR_MEETING_DATE = "15 de julio de 2024"
MENTOR_MEETING_TIME = "6:00 p.m. - 7:00 p.m."
WORKSHOP_DAY_MENTOR_MEETING_TIME = "12:00 p.m."
MENTOR_CONFIRMATION_DEADLINE = "30 de junio de 2024"
PARTICIPANT_CONFIRMATION_DEADLINE = "5 de julio de 2024"
PARTICIPANT_CONFIRMATION_DATE = "10 de julio de 2024"
MENTOR_CONFIRMATION_DATE = "5 de julio de 2024"
WORKSHOP_YEAR = "2024"

# Email configuration constants
DEFAULT_SUBJECT = "Django Girls Colombia - Información del Taller"
IMAGE_PATH = None  # No local image file available, will embed when sending emails
EMAIL_DELAY = 1  # Delay in seconds between emails

# Template variable constants
SURVEY_LINK = "https://forms.gle/mwjZZtbEaZRabbZ4A"
PHOTOS_LINK = "https://drive.google.com/drive/folders/1g4EvKQsUqqzwVOtTNzM1M5ziGSHWzOEw?usp=sharing"
CERTIFICATE_BASE_URL = "https://drive.google.com/file/"
EMAIL_HEADER_URL = "https://i.imgur.com/866NcGI.png"


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
    try:
        message = (
            service.users().messages().send(userId=user_id, body=message).execute()
        )
        print(f"Message Id: {message['id']}")
        return message
    except Exception as error:
        print(f"An error occurred: {error}")
        return None


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
        data = [row for row in csv_reader]
    return data

def get_recipients(file_name):
    try:
        return read_csv(file_name)
    except FileNotFoundError:
        print(f"Error: CSV file '{file_name}' not found")
        return []
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

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


def certificate_message(service, template, local_mode=False):
    file_name = "data/attendees.csv"
    subject = "Django Girls Colombia - Tu Certificado del Taller"

    # Load recipients data
    try:
        recipients = get_recipients(file_name)
    except FileNotFoundError:
        print(f"Error: CSV file '{file_name}' not found")
        return 0
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return 0

    # Ensure output directory exists for local mode
    if local_mode:
        os.makedirs("output", exist_ok=True)
    
    sent_count = 0
    # Send an email to each recipient
    for attendee in recipients:
        receiver_email = attendee.get("email")
        name = attendee.get("name")
        certificate_url = attendee.get("certificate_url")

        # Load HTML template with proper variable names
        context = {
            "participant_name": name,  # Templates use {participant_name}
            "survey_link": SURVEY_LINK,
            "photos_link": PHOTOS_LINK,
            "certificate_url": certificate_url,
            "email_header_url": EMAIL_HEADER_URL,
        }
        html_content = load_html_template(template, context)

        if local_mode:
            # Save to local HTML file for testing
            safe_name = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            output_file = f"output/certificate_{safe_name}.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved certificate preview: {output_file}")
        else:
            # Send actual email
            message = create_message(
                SENDER_EMAIL, receiver_email, subject, html_content, IMAGE_PATH
            )
            send_email(service, "me", message)
            sleep(EMAIL_DELAY)
        
        sent_count += 1
    
    return sent_count


def accepted_message(service, template, message_type, local_mode=False):
    # Determine data source and context based on message type
    if "participants" in message_type:
        file_name = "data/attendees.csv"
        subject = "Django Girls Colombia - ¡Has sido aceptada!"
        name_key = "participant_name"
        deadline_key = "participant_confirmation_deadline"
        deadline_value = PARTICIPANT_CONFIRMATION_DEADLINE
    else:  # mentors
        file_name = "data/mentors.csv"
        subject = "Django Girls Colombia - ¡Has sido aceptada como guía!"
        name_key = "mentor_name"
        deadline_key = "mentor_confirmation_deadline"
        deadline_value = MENTOR_CONFIRMATION_DEADLINE

    # Load recipients data
    try:
        recipients = get_recipients(file_name)
    except FileNotFoundError:
        print(f"Error: CSV file '{file_name}' not found")
        return 0
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return 0

    # Ensure output directory exists for local mode
    if local_mode:
        os.makedirs("output", exist_ok=True)
    
    sent_count = 0
    for recipient in recipients:
        receiver_email = recipient.get("email")
        name = recipient.get("name")

        # Build context with proper variable names for templates
        context = {
            name_key: name,  # participant_name or mentor_name
            "workshop_date": WORKSHOP_DATE,
            "workshop_time": WORKSHOP_TIME,
            "workshop_place": WORKSHOP_PLACE,
            "workshop_year": WORKSHOP_YEAR,
            "email_header_url": EMAIL_HEADER_URL,
            deadline_key: deadline_value
        }
        
        # Add mentor-specific variables if needed
        if "mentors" in message_type:
            context.update({
                "mentor_meeting_date": MENTOR_MEETING_DATE,
                "mentor_meeting_time": MENTOR_MEETING_TIME,
                "workshop_day_mentor_meeting_time": WORKSHOP_DAY_MENTOR_MEETING_TIME
            })
        
        html_content = load_html_template(template, context)

        if local_mode:
            # Save to local HTML file for testing
            safe_name = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            output_file = f"output/{message_type.replace('-', '_')}_{safe_name}.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved preview: {output_file}")
        else:
            # Send actual email
            message = create_message(
                SENDER_EMAIL, receiver_email, subject, html_content, IMAGE_PATH
            )
            send_email(service, "me", message)
            sleep(EMAIL_DELAY)
        
        sent_count += 1
    
    return sent_count


def waitlist_message(service, template, message_type, local_mode=False):
    """Send waitlist notification emails"""
    # Determine data source and context based on message type
    if "participants" in message_type:
        file_name = "data/attendees.csv"
        subject = "Django Girls Colombia - Lista de Espera"
        name_key = "participant_name"
        confirmation_key = "participant_confirmation_date"
        confirmation_value = PARTICIPANT_CONFIRMATION_DATE
    else:  # mentors
        file_name = "data/mentors.csv"
        subject = "Django Girls Colombia - Lista de Espera para Guías"
        name_key = "mentor_name"
        confirmation_key = "mentor_confirmation_date"
        confirmation_value = MENTOR_CONFIRMATION_DATE

    # Load recipients data
    try:
        recipients = get_recipients(file_name)
    except FileNotFoundError:
        print(f"Error: CSV file '{file_name}' not found")
        return 0
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return 0

    # Ensure output directory exists for local mode
    if local_mode:
        os.makedirs("output", exist_ok=True)
    
    sent_count = 0
    for recipient in recipients:
        receiver_email = recipient.get("email")
        name = recipient.get("name")

        # Build context with proper variable names for templates
        context = {
            name_key: name,  # participant_name or mentor_name
            "workshop_date": WORKSHOP_DATE,
            "workshop_time": WORKSHOP_TIME,
            "workshop_place": WORKSHOP_PLACE,
            "workshop_year": WORKSHOP_YEAR,
            "email_header_url": EMAIL_HEADER_URL,
            confirmation_key: confirmation_value
        }
        
        # Add mentor-specific variables if needed
        if "mentors" in message_type:
            context.update({
                "mentor_meeting_date": MENTOR_MEETING_DATE,
                "mentor_meeting_time": MENTOR_MEETING_TIME,
                "workshop_day_mentor_meeting_time": WORKSHOP_DAY_MENTOR_MEETING_TIME
            })
        
        html_content = load_html_template(template, context)

        if local_mode:
            # Save to local HTML file for testing
            safe_name = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
            output_file = f"output/{message_type.replace('-', '_')}_{safe_name}.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"Saved preview: {output_file}")
        else:
            # Send actual email
            message = create_message(
                SENDER_EMAIL, receiver_email, subject, html_content, IMAGE_PATH
            )
            send_email(service, "me", message)
            sleep(EMAIL_DELAY)
        
        sent_count += 1
    
    return sent_count


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
        return
    
    # Authenticate and build the service (only if not in local mode)
    service = None
    if not args.local:
        creds = authenticate_gmail()
        service = build("gmail", "v1", credentials=creds)
    
    # Send emails based on type
    sent_msgs = 0
    try:
        if args.type == "certificate":
            sent_msgs = certificate_message(service, template, args.local)
        elif args.type in ["accepted-participants", "accepted-mentors"]:
            sent_msgs = accepted_message(service, template, args.type, args.local)
        elif args.type in ["waitlist-participants", "waitlist-mentors"]:
            sent_msgs = waitlist_message(service, template, args.type, args.local)
        else:
            print(f"Unknown message type: {args.type}")
            return
    except Exception as e:
        print(f"Error processing messages: {e}")
        return
    
    if args.local:
        print(f"✅ Finished generating {sent_msgs} preview HTML files of type '{args.type}'")
    else:
        print(f"✅ Finished sending {sent_msgs} emails of type '{args.type}'")


if __name__ == "__main__":
    main()
