import imaplib
import email
from email.header import decode_header
import re
import os
import requests
from datetime import datetime, timedelta, timezone  
from email.utils import parsedate_to_datetime 


IMAP_SERVER    = "imap.gmail.com"
IMAP_PORT      = 993

#IMAP GMAIL / PASSWORD FILL IN
USERNAME       = ""
PASSWORD       = ""
WEBHOOK_URL    = ""

#(MM/DD/YY) PULL FROM DATE RANGE (GMAIL DOES RATE LIMIT TRY TO KEEP IT MAX 5,000 EMAILS)
START_DATE     = "05/27/25"
END_DATE       = "05/29/25"

FROM_ADDRESS   = "help@walmart.com"
REPLY_TO       = "donotreply@walmart.com"
MAILED_BY      = "eforward.registrar-servers.com"  
SIGNED_BY      = "walmart.com"                     

DEBUG          = True     #Default you can change to false


def to_imap_date(mdy):
    return datetime.strptime(mdy, "%m/%d/%y").strftime("%d-%b-%Y")

since  = to_imap_date(START_DATE)
before = (datetime.strptime(END_DATE, "%m/%d/%y") + timedelta(days=1)).strftime("%d-%b-%Y")

# connect & login
mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
mail.login(USERNAME, PASSWORD)
mail.select("INBOX")

def imap_search(token):
    st, dat = mail.search(None,
        "FROM",   f'"{FROM_ADDRESS}"',
        "SINCE",  since,
        "BEFORE", before,
        "SUBJECT", f'"{token}"'
    )
    if st != "OK":
        raise RuntimeError(f"Search failed for {token}")
    ids = dat[0].split()
    if DEBUG:
        print(f"Found {len(ids)} msgs for «{token}»")
    return ids

# get raw ID lists
confirm_ids = imap_search("thanks for your")
cancel_ids  = imap_search("Canceled: delivery from order")

def count_valid(ids):
    cnt = 0
    for mid in ids:
        st, data = mail.fetch(mid, "(RFC822)")
        if st != "OK":
            continue

        msg = email.message_from_bytes(data[0][1])

        # only check that reply-to matches
        if msg.get("Reply-To", "").lower().strip() != REPLY_TO:
            continue

        cnt += 1
    return cnt

confirmed = count_valid(confirm_ids)
canceled  = count_valid(cancel_ids)
mail.logout()

total = confirmed + canceled

embed = {
    "title": "Built by FLCLXO",
    "description": (
        f"**Total Orders**: {total}\n"
        f"**Confirmed**: {confirmed}\n"
        f"**Canceled**: {canceled}"
    ),
    "fields": [
        {"name": "Date Range",   "value": f"{START_DATE} → {END_DATE}", "inline": False},
        {"name": "IMAP Used", "value": USERNAME,                     "inline": False},
    ],
    "timestamp": datetime.now(timezone.utc).isoformat()
}

payload = {
    "username": "Walmart Order Bot",
    "embeds":   [embed]
}

resp = requests.post(WEBHOOK_URL, json=payload)
if resp.status_code == 204:
    print("Report sent to Discord!")
else:
    print(f"Webhook error {resp.status_code}: {resp.text}")
