from pydub import AudioSegment
from moviepy.editor import *
from PIL import Image

# Load the audio file
audio = AudioSegment.from_wav("song.wav")

# Load the image and ensure it is 3000x3000
cover_image = Image.open("cover.jpg")
cover_image = cover_image.resize((3000, 3000))

# Save the resized cover image if needed
cover_image.save("cover_resized.jpg")

# Convert audio to an appropriate format for MoviePy (wav or mp3)
audio.export("song_converted.mp3", format="mp3")

# Load the audio with MoviePy
audio_clip = AudioFileClip("song_converted.mp3")

# Create a video clip from the image
image_clip = ImageClip("cover_resized.jpg", duration=audio_clip.duration)

# Set the audio to the video clip
video = image_clip.set_audio(audio_clip)

# Write the video file
video.write_videofile("output_video.mp4", fps=24)

print("Video creation completed successfully!")
