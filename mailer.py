import smtplib
from email.mime.text import MIMEText


def send_signup_email(email):
    subject = "You have been invited to sign up"
    body = f"""
    You have been invited to sign up for NUB.

    Use this email when signing up to gain access.
    """
    sender = "{SENDER_EMAIL}"
    password = "{PASSWORD}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, [email], msg.as_string())


def send_event_email(email, body):
    subject = "Event reminder"

    sender = "[EMAIL]"
    password = "[PASSWORD]"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp_server:
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, [email], msg.as_string())

