import os
from moviepy.editor import *
from PIL import Image
# Pillow >=10 removed Image.ANTIALIAS; MoviePy still references it internally.
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# Flags to control which parts of the script to run
process_image_flag = False
create_video_flag = True

# Paths to the input files
audio_file = "Teys Worldy - Wylder.wav"
cover_image_file = "IMG_0044.PNG"
resized_image_file = "IMG_0044.PNG"
output_video_file = audio_file[:-4] + "_short.mp4"

# Audio segment (seconds). Set end_time to None to use until the end of the file.
start_time = 73.0
end_time = 88.0  # e.g. first minute; use None for full track from start_time

# Vertical mobile / Shorts frame (9:16)
video_width = 1080
video_height = 1920
fps = 24

# Cover art: longest side in pixels, centered on the frame
cover_max_size = 1080
background_color = (0, 0, 0)


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


def create_video():
    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        return False
    if not os.path.exists(resized_image_file):
        print(f"Image file not found: {resized_image_file}")
        return False

    audio_clip = _load_audio_segment()
    duration = audio_clip.duration

    background = ColorClip(
        size=(video_width, video_height),
        color=background_color,
        duration=duration,
    )

    cover = ImageClip(resized_image_file, duration=duration)
    cover_side = min(cover_max_size, video_width, video_height)
    cover = cover.resize(width=cover_side).set_position("center")

    video = CompositeVideoClip(
        [background, cover],
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


if process_image_flag:
    process_image()

if create_video_flag:
    create_video()
