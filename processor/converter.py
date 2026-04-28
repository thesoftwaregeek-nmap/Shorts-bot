import subprocess
import json
import os
import random
from pathlib import Path


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except FileNotFoundError:
        return False


def get_video_info(path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    return {
        "duration": float(data["format"].get("duration", 0)),
        "width": int(video.get("width", 1920)),
        "height": int(video.get("height", 1080)),
    }


def process_video(
    input_path: str,
    output_dir: str,
    add_caption: bool = True,
    progress_callback=None
) -> dict:
    info = get_video_info(input_path)
    duration = min(58, info["duration"])
    start = 0
    if info["duration"] > 58:
        start = random.uniform(0, info["duration"] * 0.3)

    title = Path(input_path).stem.split("_")[0]
    title = title.replace("-", " ").title()

    output_name = Path(input_path).stem + "_short.mp4"
    output_path = str(Path(output_dir) / output_name)

    vf = "crop=ih*9/16:ih,scale=1080:1920"
    if add_caption and title:
        safe = title.replace("'", "\\'").replace(":", "\\:")
        vf += (
            f",drawtext=text='{safe}':fontsize=48:fontcolor=white"
            f":x=(w-text_w)/2:y=h-130:box=1:boxcolor=black@0.5:boxborderw=10"
        )

    if progress_callback:
        progress_callback(10, "Starting conversion...")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", input_path,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"Processing failed: {result.stderr[-300:]}")

    if progress_callback:
        progress_callback(95, "Finalizing...")

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    hashtags = "#Shorts #Viral #Trending #FYP #ReelsViral"
    caption_text = f"{title}\n\n{hashtags}"

    return {
        "output": output_path,
        "title": title,
        "caption_text": caption_text,
        "size_mb": round(size_mb, 1)
  }
