import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

from logger.logger import get_logger

logger = get_logger(__name__,"logs/gmail_client")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_gmail_service():
    try:
        load_dotenv()

        creds = None
        client_secrets_file = os.getenv("CLIENT_SECRETS_PATH")
        token_pickle_file = os.getenv("TOKEN_PICKLE_PATH")

        if os.path.exists(token_pickle_file):
            logger.debug("[get_gmail_service] Token file found at %s, loading credentials", token_pickle_file)
            with open(token_pickle_file, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            logger.debug("[get_gmail_service] Credentials are missing or invalid")
            if creds and creds.expired and creds.refresh_token:
                logger.debug("Refreshing expired credentials")
                creds.refresh(Request())
            else:
                logger.debug("[get_gmail_service] Creating new credentials via InstalledAppFlow")
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            logger.debug("[get_gmail_service] Saving credentials to token file")
            with open(token_pickle_file, "wb") as token:
                pickle.dump(creds, token)

        service = build("gmail", "v1", credentials=creds)
        return service
    except Exception as e:
        logger.error("[get_gmail_service] Error occurred while creating Gmail service: %s", e, exc_info=True)
        return None
