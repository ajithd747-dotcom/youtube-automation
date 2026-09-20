# YouTube API credentials setup

The upload bot uses the official **YouTube Data API v3** via OAuth2. You authorize it yourself through a Google consent screen — no password is ever shared with this project.

## One-time setup

1. Go to https://console.cloud.google.com/ and create a project (or use an existing one).
2. Enable the **YouTube Data API v3** (APIs & Services → Library → search "YouTube Data API v3" → Enable).
3. Go to APIs & Services → Credentials → Create Credentials → OAuth client ID.
   - Application type: **Desktop app**
4. Download the JSON and save it here as `config/client_secret.json` (this file is git-ignored / must not be shared).
5. Run `python upload/youtube_upload.py <video_file> "<title>" "<description>"` once — it will open a browser for you to log in and approve access, then cache a token in `config/token.json` for future runs (no repeated login needed).

## Notes
- Uploads via unverified OAuth apps default to **private** visibility until the app passes Google's verification, or you keep it in "Testing" mode with your own account added as a test user (fine for personal use).
- Daily quota: 10,000 units/day by default; a single video upload costs ~1600 units (~6 uploads/day) unless you request a quota increase.
- YouTube rejects descriptions containing `->` (and possibly other raw symbol sequences) with an `invalidDescription` error -- keep descriptions to plain text/punctuation.
- Shorts are auto-detected by YouTube from aspect ratio (vertical/square) + duration (<=3 min) -- no special upload flag needed for videos rendered with `video_format="shorts"`. Adding "#Shorts" in the title/description helps ensure correct classification.
