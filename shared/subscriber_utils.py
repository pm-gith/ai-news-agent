import json, os, imaplib, email, datetime

SUBSCRIBER_FILE = os.path.join("data", "subscribers.json")

def load_subscribers():
    """Load subscribers from a JSON file."""
    with open(SUBSCRIBER_FILE, 'r') as f:
        return json.load(f)

def save_subscribers(emails):
    """Save subscribers to a JSON file."""
    with open(SUBSCRIBER_FILE, 'w') as f:
        json.dump(emails, f, indent=2)

def add_subscriber(email):
    """Add a new subscriber."""
    subscribers = load_subscribers()
    if email not in subscribers:
        subscribers.append(email)
        save_subscribers(subscribers)
        return True
    return False

def remove_subscriber(email_addr):
    """Remove a subscriber."""
    with open(SUBSCRIBER_FILE, 'r+') as f:
        data = json.load(f)
        if email_addr in data:
            data.remove(email_addr)
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2)
            print(f"Removed {email_addr} from subscribers.")
        else:
            print(f"{email_addr} not found in subscribers.")

def check_unsubscribers():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
    mail.select("inbox")

    since_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'(UNSEEN SINCE {since_date})')

    for num in messages[0].split():
        _, msg_data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        sender = email.utils.parseaddr(msg['From'])[1]
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors="ignore")
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        if "unsubscribe" in body.lower():
            remove_subscriber(sender)
            print(f"{sender} has been unsubscribed.")

    mail.logout()