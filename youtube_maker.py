import os
from moviepy.editor import *
from PIL import Image
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Flags to control which parts of the script to run
process_image_flag = False
create_video_flag = True
upload_video_flag = True

# Paths to the input files
audio_file = "Teys Worldy - Slime.wav"
cover_image_file = "artwork.png"
resized_image_file = "artwork.png"
output_video_file = audio_file[:-4] + ".mp4"
title_text = " Slime [testing upload]"
description_text = "Teys Worldy - Slime\n\nFollow Teys Worldy TESTING YOUTUBE"
privacy_choice = "1"
made_for_kids = False

# OAuth 2.0 settings
CLIENT_SECRETS_FILE = "client_secrets.json"
TOKEN_FILE = "token.json"
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]


def process_image():
    # Process image file
    if os.path.exists(cover_image_file):
        # Load the image and ensure it is 3000x3000
        cover_image = Image.open(cover_image_file)
        cover_image = cover_image.resize((3000, 3000))
        # Save the resized cover image if needed
        cover_image.save(resized_image_file)
        print("Image processing completed.")
    else:
        print(
            f"Image file {cover_image_file} not found. Skipping image processing.")
        return False
    return True


def create_video():
    if os.path.exists(audio_file) and os.path.exists(resized_image_file):
        # Load the audio with MoviePy
        audio_clip = AudioFileClip(audio_file)

        # Create a video clip from the image
        image_clip = ImageClip(
            resized_image_file, duration=audio_clip.duration)

        # Set the audio to the video clip
        video = image_clip.set_audio(audio_clip)

        # Write the video file with explicit codec settings
        video.write_videofile(output_video_file, fps=24,
                              codec='libx264', audio_codec='aac')
        print("Video creation completed successfully!")
    else:
        print(
            f"Required files not found. Audio: {audio_file}, Image: {resized_image_file}")
        return False
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


# Run the respective parts of the script based on flags
if process_image_flag:
    process_image()

if create_video_flag:
    create_video()

if upload_video_flag:
    if os.path.exists(output_video_file):
        print("\n--- YouTube Upload Configuration ---")
        
        # Get default title from file name without extension
        default_title = os.path.splitext(os.path.basename(output_video_file))[0]
        title = title_text
        if not title:
            title = default_title
            
        description = description_text
        
        # Privacy status selection
        print("Select privacy status:")
        print("1. private (default)")
        print("2. public")
        print("3. unlisted")
        privacy_status = "private"
        if privacy_choice == "2":
            privacy_status = "public"
        elif privacy_choice == "3":
            privacy_status = "unlisted"
            
        # Made for kids selection
        kids_choice = input("Is this video made for kids? (y/N): ").strip().lower()
        made_for_kids = True if kids_choice == 'y' else False
        
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

