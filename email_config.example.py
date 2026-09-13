# email_config.example.py
#
# Copy this file to email_config.py and fill in real values there.
# email_config.py itself is gitignored (see .gitignore) so real credentials
# never get committed -- this example file is what's actually tracked, as
# a template/reference.
#
# SMTP credentials used by email_sender.py to send the finished picture.
# Until email_config.py exists with real values filled in, tapping POSLAŤ /
# confirming an email address will show a clear "not configured" error in
# the app instead of crashing.
#
# For Gmail: SMTP_HOST = "smtp.gmail.com", SMTP_PORT = 465,
# SMTP_USERNAME = your full Gmail address, and SMTP_PASSWORD must be a
# 16-character *App Password* (Google Account -> Security -> 2-Step
# Verification -> App Passwords) -- your normal Gmail password will NOT
# work here. Other providers: use their SMTP-over-SSL host/port instead.

SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 465
SMTP_USERNAME = "your-login@smtp-brevo.com"
SMTP_PASSWORD = "your-smtp-api-key-here"

# Shown as the "From" address. Leave as None to just use SMTP_USERNAME.
FROM_ADDRESS = None

EMAIL_SUBJECT = "Your Galanda picture"
EMAIL_BODY = "Here's the picture you made at the Galanda kiosk!"
