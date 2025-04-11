import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_gmail_service():
    load_dotenv()
    creds = None
    client_secrets_file = os.getenv("CLIENT_SECRETS_PATH")
    token_pickle_file = os.getenv("TOKEN_PICKLE_PATH")
    if os.path.exists(token_pickle_file):
        with open(token_pickle_file, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_pickle_file, "wb") as token:
            pickle.dump(creds, token)
    service = build("gmail", "v1", credentials=creds)
    return service
    

