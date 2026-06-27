import os
from moviepy.editor import *
from PIL import Image
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Pillow >=10 removed Image.ANTIALIAS; MoviePy still references it internally.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Flags to control which parts of the script to run
process_image_flag = False
create_video_flag = True
upload_video_flag = True

# Paths to the input files
audio_file = "Teys Worldy - Slime.wav"
cover_image_file = "artwork.png"
background_image_file = "IMG_1100.png"
output_video_file = audio_file[:-4] + "_short.mp4"
def load_metadata(filepath="description.md"):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if "### title" in content and "### description" in content:
            try:
                parts = content.split("### description")
                title = parts[0].replace("### title", "").strip()
                description = parts[1].strip()
                return title, description
            except Exception:
                pass
    return "[ERROR READING DESCRIPTION.MD]", "[ERROR READING DESCRIPTION.MD]"

title_text, description_text = load_metadata()


# 1 private (default)
# 2 public
# 3 unlisted
privacy_choice = "2"
made_for_kids = False

# OAuth 2.0 settings
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]

# Audio segment (seconds). Set end_time to None to use until the end of the file.
start_time = 59.0
end_time = 67.0  # e.g. first minute; use None for full track from start_time

# Vertical mobile / Shorts frame (9:16)
video_width = 1080
video_height = 1920
fps = 24

# Cover art: longest side in pixels, centered on the frame
cover_max_size = 1080
# Background: same cover scaled to fill the frame, with a dark overlay (0–1)
background_darken_opacity = 0.45


def process_image():
    if not os.path.exists(cover_image_file):
        print(
            f"Image file {cover_image_file} not found. Skipping image processing.")
        return False

    cover_image = Image.open(cover_image_file)
    width, height = cover_image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    cover_image = cover_image.crop((left, top, left + side, top + side))
    cover_image = cover_image.resize(
        (cover_max_size, cover_max_size), Image.LANCZOS
    )
    cover_image.save(resized_image_file)
    print("Image processing completed.")
    return True


def _load_audio_segment():
    audio_clip = AudioFileClip(audio_file)
    segment_end = audio_clip.duration if end_time is None else end_time
    if start_time < 0 or segment_end <= start_time:
        raise ValueError(
            f"Invalid time range: start_time={start_time}, end_time={segment_end}"
        )
    if segment_end > audio_clip.duration:
        raise ValueError(
            f"end_time ({segment_end}) exceeds audio duration ({audio_clip.duration})"
        )
    return audio_clip.subclip(start_time, segment_end)


def _make_background_clip(image_path, duration):
    bg = ImageClip(image_path, duration=duration)
    scale = max(video_width / bg.w, video_height / bg.h)
    bg = bg.resize(scale)
    bg = bg.crop(
        x_center=bg.w / 2,
        y_center=bg.h / 2,
        width=video_width,
        height=video_height,
    )
    darken = ColorClip(
        size=(video_width, video_height),
        color=(0, 0, 0),
        duration=duration,
    ).set_opacity(background_darken_opacity)
    return bg, darken


def create_video():
    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        return False
    if not os.path.exists(background_image_file):
        print(f"Image file not found: {background_image_file}")
        return False

    audio_clip = _load_audio_segment()
    duration = audio_clip.duration

    background, darken = _make_background_clip(background_image_file, duration)

    cover = ImageClip(cover_image_file, duration=duration)
    cover_side = min(cover_max_size, video_width, video_height)
    cover = cover.resize(width=cover_side).set_position("center")

    video = CompositeVideoClip(
        [background, darken, cover],
        size=(video_width, video_height),
    ).set_audio(audio_clip)

    video.write_videofile(
        output_video_file,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
    )
    print(f"Short video saved: {output_video_file}")
    return True


def get_authenticated_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, YOUTUBE_UPLOAD_SCOPE)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"\n[ERROR] '{CLIENT_SECRETS_FILE}' not found.")
                print("To upload videos to YouTube, please:")
                print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
                print("2. Enable 'YouTube Data API v3' for your project.")
                print("3. Configure the OAuth consent screen and add your email as a test user.")
                print("4. Go to Credentials -> Create Credentials -> OAuth Client ID (Application type: Desktop).")
                print(f"5. Download the JSON and save it as '{CLIENT_SECRETS_FILE}' in this directory.\n")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, YOUTUBE_UPLOAD_SCOPE)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return build("youtube", "v3", credentials=creds)


def upload_video_to_youtube(video_path, title, description, privacy_status, made_for_kids):
    if not os.path.exists(video_path):
        print(f"Video file {video_path} not found. Cannot upload.")
        return False

    print("Authenticating with YouTube API...")
    youtube = get_authenticated_service()
    if not youtube:
        print("Authentication failed or was not configured. Skipping upload.")
        return False

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'categoryId': '10'  # 10 is Music. Feel free to adjust.
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': made_for_kids
        }
    }

    # 1MB chunk size for resumable upload
    media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)
    request = youtube.videos().insert(
        part='snippet,status',
        body=body,
        media_body=media
    )

    print(f"Starting upload for: {video_path}")
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%...")
        except Exception as e:
            print(f"An error occurred during upload: {e}")
            return False

    print(f"\nVideo uploaded successfully!")
    print(f"Video ID: {response['id']}")
    print(f"URL: https://www.youtube.com/watch?v={response['id']}")
    return True


if process_image_flag:
    process_image()

if create_video_flag:
    create_video()

if upload_video_flag:
    if title_text == "[ERROR READING DESCRIPTION.MD]" or description_text == "[ERROR READING DESCRIPTION.MD]":
        raise ValueError("Title and description could not be read from description.md. Upload aborted.")
    if os.path.exists(output_video_file):
        print("\n--- YouTube Upload Configuration ---")
        
        # Get default title from file name without extension
        default_title = os.path.splitext(os.path.basename(output_video_file))[0]
        title = title_text
        if not title:
            title = default_title
            
        description = description_text
        
        # Privacy status selection
        privacy_status = "private"
        if privacy_choice == "2":
            privacy_status = "public"
        elif privacy_choice == "3":
            privacy_status = "unlisted"
            
        print(f"\nTitle: {title}")
        print(f"Description: {description}")
        print(f"Privacy: {privacy_status}")
        print(f"Made for kids: {made_for_kids}")
        confirm = input("Confirm upload? (y/N): ").strip().lower()
        
        if confirm == 'y':
            upload_video_to_youtube(output_video_file, title, description, privacy_status, made_for_kids)
        else:
            print("Upload cancelled by user.")
    else:
        print(f"Output video file {output_video_file} not found. Cannot proceed with upload.")

