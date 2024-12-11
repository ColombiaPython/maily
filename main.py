import os.path
import base64
import csv
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


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


def load_html_template(template_path, context):
    with open(template_path, "r") as file:
        template = file.read()
    return template.format(**context)


def main():
    # Authenticate and build the service
    creds = authenticate_gmail()
    service = build("gmail", "v1", credentials=creds)
    file_name = "attendees.csv"
    attendees_info = read_csv(file_name)

    # Email details
    sender_email = ""
    subject = "🎓 Certificado Taller Django Girls + Encuesta"

    # Send an email to each recipient
    for attendee in attendees_info:
        receiver_email = attendee.get("email")
        name = attendee.get("name")
        certificate_url = attendee.get("certificate_url")
        survey_link = "https://forms.gle/"
        photos_link = "https://drive.google.com/drive/folders/?usp=sharing"

        # Load HTML template
        template_path = "email_template.html"  # Update with your template file path
        context = {
            "name": name,
            "survey_link": survey_link,
            "photos_link": photos_link,
            "certificate_url": certificate_url,
        }
        html_content = load_html_template(template_path, context)

        image_path = "picture.jpg"
        message = create_message(
            sender_email, receiver_email, subject, html_content, image_path
        )

        send_email(service, "me", message)


if __name__ == "__main__":
    main()
