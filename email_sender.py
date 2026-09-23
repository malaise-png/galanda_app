# email_sender.py
#
# Sends the finished composition by email. SMTP credentials live in
# email_config.py, not here or in theme.py, so real secrets stay in one
# easy-to-gitignore place.

import smtplib
from email.message import EmailMessage

import email_config


class EmailSendError(Exception):
    """Raised when the picture couldn't be emailed -- missing SMTP
    configuration, or a network/auth failure. Callers should catch this and
    show the user a friendly message instead of crashing the kiosk."""


def send_image(to_address, image_path):
    if not email_config.SMTP_HOST or not email_config.SMTP_USERNAME or not email_config.SMTP_PASSWORD:
        raise EmailSendError(
            "Email isn't configured yet -- fill in SMTP_HOST / SMTP_USERNAME / "
            "SMTP_PASSWORD in email_config.py."
        )

    message = EmailMessage()
    message["Subject"] = email_config.EMAIL_SUBJECT
    message["From"] = email_config.FROM_ADDRESS or email_config.SMTP_USERNAME
    message["To"] = to_address
    message.set_content(email_config.EMAIL_BODY)

    with open(image_path, "rb") as image_file:
        message.add_attachment(image_file.read(), maintype="image", subtype="png", filename="galanda.png")

    try:
        with smtplib.SMTP(email_config.SMTP_HOST, email_config.SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(email_config.SMTP_USERNAME, email_config.SMTP_PASSWORD)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        raise EmailSendError(f"Couldn't send the email: {error}") from error
