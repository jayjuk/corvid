import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv("../common/.env", override=True)

def send_mail(subject: str, body: str):
    fromaddr = "me@jayjoseph.com"
    toaddr = "me@jayjoseph.com"
    
    msg = MIMEText(body, 'plain')
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = subject

    server = smtplib.SMTP('smtp.zoho.com', 587)
    server.starttls()
    server.login(fromaddr, os.environ["MONITOR_EMAIL_PASSWORD"])
    text = msg.as_string()

    server.sendmail(fromaddr, toaddr, text)
    print(f"Sent email with {subject=} and {body=}")
    server.quit()

if __name__ == "__main__":
    send_mail("test", "this is a test")
