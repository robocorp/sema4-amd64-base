from robocorp import browser, vault
from robocorp.tasks import task
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload


from pathlib import Path
import os
import pyotp
import time


OUTPUT_DIR = Path(os.environ.get("ROBOT_ARTIFACTS"))
# Google folder ID where you want the files stored
DRIVE_FOLDER_ID = "1M-sCLrbD4K21sONsPqn0lQFhuEUlW0K1"
SCOPES = ["https://www.googleapis.com/auth/drive"]
# json for Google API authentication for storing files
TOKEN_FILE = "token.json"


@task
def controlroom_logs():
    # login_download in vault has 3 arguments
    # user = google user name
    # password = user's google password
    # otp = the One-Time Password code for MFA
    secret = vault.get_secret("login_download")
    creds = authenticate_token()
    drive_service = build("drive", "v3", credentials=creds)

    # chromium as the browser engine was giving me a timeout error, switched to firefox and everything worked as designed
    browser.configure(
        browser_engine="firefox",
        screenshot="on",
        headless=True,
    )

    try:
        page = browser.goto("https://cloud.robocorp.com")

        page.get_by_role("button", name="Sign in with Google").click()
        page.locator("#identifierId").fill(secret["user"])
        page.get_by_text("Next").click()

        page.locator("[name=Passwd]").fill(secret["password"])
        page.locator("[name=Passwd]").press("Enter")

        # Had an issue with automation thinking it clicked the button but didn't
        # to fix it used an older workaround of trying to click it 5 times quickly then move on
        # not elegant but another way to work around a stubborn button
        for _ in range(5):
            try:
                page.get_by_role("button", name="Try another way").click(timeout=5000)
            except:
                pass

        page.get_by_text("Google Authenticator").click()
        otp = authenticate_user(secret["otp"])
        page.locator("[name=totpPin]").fill(otp)
        page.get_by_role("button", name="Next").click()

        page.get_by_alt_text("User picture").wait_for()

        # typically you do not want to use a sleep, however a popup in the browser happens shortly after logging in
        # because it isn't immediate the automation will wait 4 seconds, then check if the popup is there, if so it closes it
        time.sleep(4)
        if page.get_by_text("Latest Updates from Robocorp").is_visible():
            page.get_by_role("button", name="Close dialog").click()

        get_logs(page, "Playground", drive_service)
        get_logs(page, "Robocorp Oy", drive_service)
        get_logs(page, "Robocorp certificates", drive_service)
        get_logs(page, "Solution Demos (STABLE)", drive_service)

    except Exception as e:
        print(e)

    finally:
        # Place for teardown and cleanups
        # Playwright handles browser closing
        print("Done")


def authenticate_user(code):
    # utilizes OTP to authenticate the user
    totp = pyotp.TOTP(code)
    result = totp.now()
    return result


def get_logs(page, workspace, drive_service):
    page = browser.goto(
        "https://cloud.robocorp.com/orgrobocorp/robocorpworkforceagenttesting/activity"
    )

    first = page.get_by_test_id("workspace__nav-accordion-title").get_by_text(workspace)

    second = first.locator("xpath=/ancestor::button[1]/following-sibling::div[1]")
    if first.wait_for() and first.is_visible():
        second.get_by_text("Configuration").click()
    else:
        first.click()
        second.get_by_text("Configuration").click()

    page.get_by_role("tab", name="Audit Log").click()
    page.get_by_role("button", name="All time").click()
    page.get_by_role("option", name="Last 7 days").click()

    with page.expect_download() as download_info:
        page.get_by_role("button", name="Download CSV").click()
    download = download_info.value
    download.save_as(f"{OUTPUT_DIR}/{download.suggested_filename}")
    upload_file_to_drive(
        drive_service, f"{OUTPUT_DIR}/{download.suggested_filename}", DRIVE_FOLDER_ID
    )


def authenticate_token():
    # in my example google authentication for the API to allow the automation to connect for uploading
    # there are other methods as well that can be used
    creds = None
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return creds
    except Exception as e:
        Exception(e)
        exit(1)


def upload_file_to_drive(service, file_path, folder_id):
    """Upload file to Google Drive and return the file ID."""
    file_metadata = {"name": os.path.basename(file_path), "parents": [folder_id]}
    media = MediaFileUpload(file_path, mimetype="application/csv")
    file = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )

