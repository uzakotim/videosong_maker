import os
from moviepy.editor import *
from PIL import Image

# Flags to control which parts of the script to run
process_image_flag = True
create_video_flag = True

# Paths to the input files
audio_file = "Teys Worldy - The Hidden Pattern.wav"
cover_image_file = "The Hidden Pattern.jpg"
resized_image_file = "cover_resized.jpg"
output_video_file = audio_file[:-4] + ".mp4"


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


# Run the respective parts of the script based on flags
if process_image_flag:
    process_image()

if create_video_flag:
    create_video()
