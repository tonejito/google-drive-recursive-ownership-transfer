# Google Drive Recursive Mover & Ownership Transfer Tool

Original implementation - @DavidStrauss (2014-2020)
- <https://github.com/davidstrauss/google-drive-recursive-ownership>

Adaptation - @KOliver94 (2022)
- <https://github.com/BSStudio/google-drive-recursive-ownership-transfer>

Improvement - @tonejito (2022)
- <https://github.com/tonejito/google-drive-recursive-ownership-transfer>

These scripts use Google Drive API v3. The `transfer.py` can recursively give the ownership of all files and folders to a given user while the `move.py` can move all files to a new place which is useful for moving files to a shared drive because moving folders is not supported.

## Supported Files

G Suite for Government and G Suite for Education accounts can change ownership of any file owned by the current user, including uploaded/synced files suchs as PDFs.

Other Google Accounts such as G Suite for Business or Personal Google Accounts can only transfer ownership of Google files (Docs, Sheets, Sildes, Forms, Drawings, My Maps, and folders).

NOTE: Ownership can only be transferred to members of the same G Suite or Google domain. Ex. `@gmail.com` can only transfer to other `@gmail.com` addresses.

NOTE: The Google Drive API does not allow suppressing notifications for change of ownership.

## Setup

```commandline
git clone https://github.com/BSStudio/google-drive-recursive-ownership-transfer
pip install -r requirements.txt
```

## Usage

First, replace the sample `client_secrets.json` with your own [client secrets](https://github.com/googleapis/google-api-python-client/blob/master/docs/client-secrets.md). Don't forget to enable Drive API for your project.

<!--
TODO: Running on headless machine (ssh LocalForward?)
-->


### Transferring ownership

CURRENT LIMITATION: Due to e-mail sending the script can only process ~2500 files before Google rejects the requests.

```commandline
./transfer.py [-h] -o OWNER [-f FOLDER]
```

```
options:
  -h, --help            show this help message and exit
  -o OWNER, --owner OWNER
                        E-mail address of the new owner.
  -f FOLDER, --folder FOLDER
                        ID of the Google Drive folder. The user's root directory will be used if left empty.
```

### Moving files/folders

```commandline
./move.py [-h] -d DESTINATION [-f FOLDER]
```

```
options:
  -h, --help            show this help message and exit
  -d DESTINATION, --destination DESTINATION
                        ID of the destination folder where the files should be moved to.
  -f FOLDER, --folder FOLDER
                        ID of the Google Drive folder. The user's root directory will be used if left empty.
```

### Listing owners with number of files owned by them

```commandline
./count.py [-h] [-f FOLDER]

options:
  -h, --help            show this help message and exit
  -f FOLDER, --folder FOLDER
                        ID of the Google Drive folder. The user's root directory will be used if left empty.
```
