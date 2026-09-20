"""Upload a video to YouTube using the official Data API v3 (OAuth2)."""
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CLIENT_SECRET_FILE = CONFIG_DIR / "client_secret.json"
TOKEN_FILE = CONFIG_DIR / "token.json"


def get_credentials() -> Credentials:
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_FILE.exists():
                raise FileNotFoundError(
                    f"Missing {CLIENT_SECRET_FILE}. See config/README.md for setup steps."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def upload_video(video_path: str, title: str, description: str, privacy_status: str = "private") -> str:
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {"title": title, "description": description, "categoryId": "22"},
        "status": {"privacyStatus": privacy_status},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Upload complete: https://youtu.be/{video_id}")
    return video_id


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print('Usage: python youtube_upload.py <video_file> "<title>" "<description>" [privacy_status]')
        raise SystemExit(1)

    video_file, title_arg, description_arg = sys.argv[1:4]
    privacy = sys.argv[4] if len(sys.argv) > 4 else "private"
    upload_video(video_file, title_arg, description_arg, privacy)
