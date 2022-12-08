#!/usr/bin/env python3

# Original implementation - @DavidStrauss (2014-2020)
# https://github.com/davidstrauss/google-drive-recursive-ownership
#
# Adaptation - @KOliver94 (2022)
# https://github.com/BSStudio/google-drive-recursive-ownership-transfer
#
# Improvement - @tonejito (2022)
# https://github.com/tonejito/google-drive-recursive-ownership-transfer

# Library documentation
# https://developers.google.com/drive/api/guides/performance#overview
# https://developers.google.com/drive/api/v3/reference/permissions/create
# https://googleapis.github.io/google-api-python-client/docs/epy/index.html
# https://github.com/googleapis/google-api-python-client/blob/main/docs/README.md
# https://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html

import argparse
import logging
import math
import pickle
import json
import os

from math import pow
from time import sleep
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SLEEP_TIME = 0
SLEEP_FACTOR = 1
SLEEP_EXPONENT = 2

SCOPES = ["https://www.googleapis.com/auth/drive"]
BATCH = None
BATCH_SIZE = 0
MAXIMUM_BATCH_SIZE = 100
PICKLE_FILE="client_secrets.pkl"

# FIXME: Error handling / Rate limit
#
# <HttpError 500 when requesting https://www.googleapis.com/drive/v3/files/FILE_ID/permissions?transferOwnership=true&alt=json
# returned "Internal Error". Details: "[{'domain': 'global', 'reason': 'internalError', 'message': 'Internal Error'}]">
#
# <HttpError 403 when requesting https://www.googleapis.com/drive/v3/files/FILE_ID/permissions?transferOwnership=true&alt=json
# returned "Rate limit exceeded. User message: "Sorry, you have exceeded your sharing quota."".
# Details: "[{'domain': 'global', 'reason': 'sharingRateLimitExceeded',
#   'message': 'Rate limit exceeded. User message: "Sorry, you have exceeded your sharing quota."'}]">
#
# <HttpError 403 when requesting https://www.googleapis.com/drive/v3/files/FILE_ID/permissions?sendNotificationEmail=false&transferOwnership=true&alt=json
# returned "The sendNotificationEmail parameter is only applicable for permissions of type 'user' or 'group', and must not be disabled for ownership transfers.".
# Details: "[{'domain': 'global', 'reason': 'forbidden',
#   'message': "The sendNotificationEmail parameter is only applicable for permissions of type 'user' or 'group', and must not be disabled for ownership transfers.",
#   'locationType': 'parameter', 'location': 'sendNotificationEmail'}]">


# TODO: Give option to avoid running a local web browser to get the OAUTH
def get_drive_service(host="localhost", port=65535):
    if os.path.exists(PICKLE_FILE):
      try:
        with open(PICKLE_FILE, 'rb') as input_file:
          creds = pickle.load(input_file)
      except Exception as e:
          exception_name = e.__class__.__name__
          logging.warning({"name": exception_name, "message": str(e)})
          raise
    else:
      flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
      creds = flow.run_local_server(host=host, port=port)
      try:
        with open(PICKLE_FILE, 'wb') as output_file:
          pickle.dump(creds, output_file)
      except Exception as e:
          exception_name = e.__class__.__name__
          logging.warning({"name": exception_name, "message": str(e)})
          pass
    service = build("drive", "v3", credentials=creds)
    return service


def callback(request_id, response, exception):
    global SLEEP_TIME
    global SLEEP_FACTOR
    global SLEEP_EXPONENT

    if exception:
        exception_name = exception.__class__.__name__
        logging.warning({"name": exception_name, "message": str(exception)})
        # TODO: Select if the exponential backoff is enabled or
        # if the script should exit after receiving an HttpError
        SLEEP_FACTOR = SLEEP_FACTOR + 1
        SLEEP_TIME = pow(SLEEP_FACTOR,SLEEP_EXPONENT)
        logging.debug(f"Exponential backoff: sleep({SLEEP_TIME}) : {SLEEP_FACTOR}")
        sleep(SLEEP_TIME)
        # raise RuntimeError("Something happened") from exception
    else:
        logging.info("[✓]", end="")


def create_batch(service):
    global BATCH
    BATCH = service.new_batch_http_request(callback=callback)
    global BATCH_SIZE
    BATCH_SIZE = 0


def batch_add(service, file_id, new_owner):
    if not BATCH:
        create_batch(service)
    BATCH.add(service.permissions().create(
        fileId=file_id,
        body={
            "type": "user",
            "role": "owner",
            "emailAddress": new_owner,
        },
        transferOwnership=True,
        # Can't be disabled when transferring ownership
        sendNotificationEmail=True,
    ))
    global BATCH_SIZE
    BATCH_SIZE += 1
    if BATCH_SIZE == MAXIMUM_BATCH_SIZE:
        logging.info("Maximum batch size reached. Executing batch…")
        BATCH.execute()
        logging.info("Batch execution finished.")
        create_batch(service)


def process_all_files(service, new_owner, folder_id, folder_name=None):
    if not folder_name:
        folder_name = service.files().get(fileId=folder_id).execute().get("name")
    logging.info(f"Gathering files in folder '{folder_name}'…")

    next_page_token = None
    # TODO: Refactor to fetch all files, save them to a key-value store, then execute in batch
    while True:
        try:
            items = service.files().list(
                q=f"'{folder_id}' in parents and not trashed",
                fields="files(id, name, mimeType, owners), nextPageToken",
                pageToken=next_page_token
            ).execute()
            for item in items["files"]:
                if item["mimeType"] == "application/vnd.google-apps.folder":
                    process_all_files(service, new_owner, item["id"], item["name"])
                    # pass
                if item["owners"][0]["me"]:
                    batch_add(service, item["id"], new_owner)
            next_page_token = items.get("nextPageToken")
            if not next_page_token:
                break

        except HttpError as e:
            exception_name = e.__class__.__name__
            logging.warning({"name": exception_name, "message": str(e)})
            raise

def main():
    msg = """
    This script transfers ownership of all files and folders recursively of a given Google Drive folder.

    Environment variables:
    - OAUTH_HOST: Host name for the local authentication server (default: localhost)
    - OAUTH_PORT: Port number for the local authentication server (default: 65535)
                  Specify 0 as port number to get the authentication server in a random port.
    """
    logging.getLogger().setLevel(logging.INFO)
    OAUTH_HOST = os.environ.get("OAUTH_HOST","localhost")
    OAUTH_PORT = os.environ.get("OAUTH_PORT",65535)
    parser = argparse.ArgumentParser(description=msg)
    parser.add_argument("-o", "--owner", required=True,
        help="E-mail address of the new owner.")
    parser.add_argument("-f", "--folder", default="root",
        help="ID of the Google Drive folder. The user's root directory will be used if left empty.")
    parser.add_argument("-H", "--host", default=OAUTH_HOST, required=False,
        help="Host name for the local authentication server. This can also be specified from the OAUTH_HOST environment variable (default 'localhost')")
    parser.add_argument("-P", "--port", default=OAUTH_PORT, required=False,
        help="Port number for the local authentication server. This can also be specified from the OAUTH_PORT environment variable (default 65535)")
    args = parser.parse_args()
    logging.info(f"Changing all files to owner '{args.owner}'")
    service = get_drive_service()
    try:
        process_all_files(service, args.owner, args.folder)
        if BATCH:
            logging.info("Executing final batch…")
            BATCH.execute()
            logging.info("Batch execution finished.")
    except HttpError as e:
        exception_name = e.__class__.__name__
        logging.warning({"name": exception_name, "message": str(e)})


if __name__ == "__main__":
    main()
