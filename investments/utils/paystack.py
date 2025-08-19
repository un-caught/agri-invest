import requests
from django.conf import settings

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
BASE_URL = "https://api.paystack.co"

def create_transfer_recipient(user):
    """Create a transfer recipient for the user's bank account."""
    account = user.bank_account
    url = f"{BASE_URL}/transferrecipient"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    data = {
        "type": "nuban",
        "name": account.account_name or user.get_full_name(),
        "account_number": account.account_number,
        "bank_code": account.bank_code,
        "currency": "NGN"
    }
    response = requests.post(url, json=data, headers=headers).json()
    if not response.get("status"):
        raise Exception(f"Paystack error: {response.get('message')}")
    return response["data"]["recipient_code"]

def initiate_transfer(amount, recipient_code, reason="Withdrawal Payout"):
    """Send money to a recipient via Paystack."""
    url = f"{BASE_URL}/transfer"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    data = {
        "source": "balance",
        "amount": int(amount * 100),  # Convert to kobo
        "recipient": recipient_code,
        "reason": reason
    }
    response = requests.post(url, json=data, headers=headers).json()
    if not response.get("status"):
        raise Exception(f"Paystack error: {response.get('message')}")
    return response["data"]
