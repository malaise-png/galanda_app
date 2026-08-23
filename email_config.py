# email_config.py
#
# SMTP credentials used by email_sender.py to send the finished picture.
# Fill these in with a real account before sending will work -- until then,
# tapping POSLAŤ / confirming an email address will show a clear "not
# configured" error in the app instead of crashing.
#
# For Gmail: SMTP_HOST = "smtp.gmail.com", SMTP_PORT = 465,
# SMTP_USERNAME = your full Gmail address, and SMTP_PASSWORD must be a
# 16-character *App Password* (Google Account -> Security -> 2-Step
# Verification -> App Passwords) -- your normal Gmail password will NOT
# work here. Other providers: use their SMTP-over-SSL host/port instead.
#
# Keep any real credentials you put here out of version control.

SMTP_HOST = None
SMTP_PORT = 465
SMTP_USERNAME = None
SMTP_PASSWORD = None

# Shown as the "From" address. Leave as None to just use SMTP_USERNAME.
FROM_ADDRESS = None

EMAIL_SUBJECT = "Your Galanda picture"
EMAIL_BODY = "Here's the picture you made at the Galanda kiosk!"
