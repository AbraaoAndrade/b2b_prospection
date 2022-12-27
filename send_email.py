import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.mime.application import MIMEApplication
import os

def send_email(smtp_server, smtp_port, email_message, subject, attachment=None):
    sender, password = os.environ.get("EMAIL"), os.environ.get("EMAIL_KEY")
    receiver = sender 

    message = MIMEMultipart()
    message['To'] = Header(receiver)
    message['From']  = Header(sender)
    message['Subject'] = Header(subject)
    message.attach(MIMEText(email_message,'plain', 'utf-8'))
    if attachment:
        att = MIMEApplication(attachment.read(), _subtype="txt")
        att.add_header('Content-Disposition', 'attachment', filename=attachment.name)
        message.attach(att)

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.ehlo()
    server.login(sender, password)
    text = message.as_string()
    server.sendmail(sender, receiver, text)
    server.quit()