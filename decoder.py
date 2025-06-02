import imaplib
import email
from email.header import decode_header
from openai import OpenAI
import os
import smtplib
from email.mime.text import MIMEText

client = OpenAI()

# Config
EMAIL_USER = os.getenv("GMAIL_EMAIL")
EMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client.api_key = OPENAI_API_KEY
deleted_ids = []

# connection to gmail
imap = imaplib.IMAP4_SSL("imap.gmail.com")
imap.login(EMAIL_USER, EMAIL_PASS)
imap.select("inbox")

# unseen emails
status, messages = imap.search(None, '(UNSEEN)')
email_ids = messages[0].split()

def classify_email_with_gpt(subject, body):
    prompt = f"""Classify the following email as one of: Important, Spam, Email Subject: {subject}
Email Body: {body}
Category:"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0
    )
    return response.choices[0].message['content'].strip()

def send_auto_reply(to_email, subject, body):
    reply_subject = f"RE: {subject}"
    reply_body = f"""Hello,
    Thanks for this message. This is an automated reply to let you know that your email has been recieved. May I please get the details for this please.locals

    Kind regards,
    Caroline Ho"""

    msg = MIMEText(reply_body)
    msg['Subject'] = reply_subject
    msg['From'] = EMAIL_USER
    msg['To'] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

# process emails
for email_id in email_ids[:5]:
    res, msg = imap.fetch(email_id, "(RFC822)")
    for response in msg:
        if isinstance(response, tuple):
            msg = email.message_from_bytes(response[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else "utf-8")
            from_ = msg.get("From")
            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()

            print(f"\nFrom: {from_}")
            print(f"Subject: {subject}")
            print("Classifying...")
            category = classify_email_with_gpt(subject, body[:1000])
            print(f"AI Classification: {category}")

    if category.lower() == "important":
        send_auto_reply(from_, subject, body)
    #mark to delete
    if category.lower() in ["spam", "promotional", "newsletter"]:
        print("Deleting email...")
        imap.store(email_id, '+FLAGS', '\\Deleted')
        deleted_ids.append(email_id)
    # delete for real
    if deleted_ids:
        imap.expunge()
        print(f"Deleted {len(deleted_ids)} email(s)")
            

imap.logout()


