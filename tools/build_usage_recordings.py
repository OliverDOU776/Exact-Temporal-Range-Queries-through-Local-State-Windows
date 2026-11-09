#!/usr/bin/env python3
"""Encode real application-use captures, without drawing or simulating the UI.

Actual browser capture; idle pauses trimmed; reading holds added.

Input: --capture-root contains csv-session, public-session and masked-session.
Each directory contains capture.json with ordered frames (file, stage, timeMs)
and the corresponding genuine browser PNGs. Capture timestamps establish order;
long pauses between browser operations are intentionally not playback timings.
Every captured frame is retained. Short transitions and CSV typing use 4/30 s;
the last frame of each stage receives a reading hold. The only added pixels are
an 80-pixel white caption area below the complete, unscaled browser viewport
(plus at most one pixel to make the encoded canvas dimensions even).

Requires Python 3, Pillow, ffmpeg, ffprobe and DejaVu Sans. For example:
  python tools/build_usage_recordings.py --capture-root captures --output-dir docs/demos

Captures are supplied separately: this script neither launches a browser nor
substitutes a recreated interface. MP4 uses H.264/yuv420p with faststart at 30 fps;
GIF is a 1120-pixel-wide loop. PNG posters use actual final result frames.
WebVTT cues match the two burned-in caption lines. Optional --audit-dir stores
source hashes, exact timing, ffprobe reports and a five-stage contact sheet.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FPS = 30
TRANSITION_FRAMES = 4
CAPTION_HEIGHT = 80
PROVENANCE = "Actual browser capture; idle pauses trimmed; reading holds added."

# These captions describe the named capture stages. Numerical statements are
# visible in the captured application's result tables; no values are inferred.
CAPTIONS = {
    "Start with your ordered data": (
        "Enter your ordered data", "Start with a CSV header and two readings."),
    "Paste or type your CSV readings": (
        "Type the CSV into the application", "Two original readings: 70 and 141; both have weight 1."),
    "Choose the allowed integer offsets": (
        "Set the allowed offsets", "Use integer offsets from 0 to 1; keep the count range at 70 to 140."),
    "Request more than one shared movement budget": (
        "Compare two shared movement budgets", "Request budgets 0 and 1 in the same query."),
    "Run the actual exact query": (
        "Click Compute exact bounds", "The algorithm runs locally on the entered readings and settings."),
    "Read the result: budget 0 gives [1,1]; budget 1 gives [0,2]": (
        "Read the exact result table", "Budget 0 gives [1, 1]; budget 1 gives [0, 2]."),
    "Change one reading: 141 becomes 140": (
        "Edit one reading", "Change 141 to 140 in the same CSV input."),
    "Changing input clears the old answer": (
        "The input change clears the previous answer", "Recompute to obtain results for the edited readings."),
    "Recompute with the edited reading": (
        "Click Compute exact bounds again", "Run the same budgets with the edited input."),
    "The answer changes to [1,2] at both budgets": (
        "The edited reading changes the answer", "Budgets 0 and 1 now both give [1, 2]."),
    "Download inputs, settings and exact answers together": (
        "Download the query and results as JSON", "Keep the entered readings, settings and exact answers together."),
    "Load a real public sequence without preparing a file": (
        "Start with the built-in public example", "Load real BIG001 readings directly in the application."),
    "Load the 96 original BIG001 readings": (
        "Click Real BIG001 · 96 readings", "The application loads the original ordered sequence and computes five budgets."),
    "The uncorrected count is 84 of 96; compare all five exact bounds": (
        "Inspect the public-data result", "Nominal count: 84 of 96. With offsets -30 to +30, budget 4 gives [63, 92]."),
    "Keep the readings fixed; narrow the allowed offsets": (
        "Narrow the allowed offsets", "Keep all 96 readings fixed; change the lower offset from -30 to -10."),
    "Set the upper offset to +10": (
        "Set the upper offset to +10", "Compare a narrower offset scenario using the same readings and budgets."),
    "The same data, now offsets from -10 to +10": (
        "Review the revised settings", "Allowed integer offsets are now -10 to +10."),
    "Recompute under the revised sensitivity scenario": (
        "Recompute the revised scenario", "Click Compute exact bounds with the narrower offset range."),
    "Budget 4 now gives [82,89], compared with [63,92] before": (
        "Compare the exact sensitivity bounds", "Budget 4 now gives [82, 89], compared with [63, 92] before."),
    "Export the chosen scenario; report sensitivity rather than a calibrated error estimate": (
        "Export the chosen scenario as JSON", "These are exact sensitivity bounds under the settings, not a calibrated error estimate."),
    "Import a CSV with selected and masked observations": (
        "Import a CSV with masked observations", "Use the file picker to load the local masked-period.csv example."),
    "Choose the local masked-period.csv file": (
        "Choose masked-period.csv", "The application imports five rows with a 0/1 weight column."),
    "Weight 0 excludes a reading from the count, not from temporal order": (
        "Inspect the imported mask", "Weight 0 excludes a row from the count; the row stays in temporal order."),
    "Keep the masked rows in temporal order": (
        "Keep the full sequence in order", "Three rows have weight 1; two masked rows remain between them."),
    "Compute only the three selected observations": (
        "Compute the masked query", "Click Compute exact bounds for budgets 0 and 1."),
    "Three observations count; budgets 0 and 1 both give [1,2]": (
        "Read the count over the selected observations", "Three observations count; budgets 0 and 1 both give [1, 2]."),
    "Add budget 2 to the same query": (
        "Add budget 2", "Request budgets 0, 1 and 2 without changing the sequence or its mask."),
    "One shared budget still spans the masked readings": (
        "Review the shared budget request", "The same budget spans the full ordered sequence, including masked rows."),
    "Recompute the requested budget bank": (
        "Recompute all three requested budgets", "Click Compute exact bounds after adding budget 2."),
    "Only budget 2 reaches [0,3]; masking does not reset the budget": (
        "Compare the masked-query result table", "Budgets 0 and 1 give [1, 2]; budget 2 reaches [0, 3]."),
    "Save the mask, settings and exact results together": (
        "Download the masked query and results", "Save the original row order, the mask, settings and exact answers together."),
}

RESULT_STAGES = {
    "Read the result: budget 0 gives [1,1]; budget 1 gives [0,2]",
    "The answer changes to [1,2] at both budgets",
    "The uncorrected count is 84 of 96; compare all five exact bounds",
    "Budget 4 now gives [82,89], compared with [63,92] before",
    "Three observations count; budgets 0 and 1 both give [1,2]",
    "Only budget 2 reaches [0,3]; masking does not reset the budget",
}

SESSIONS = {
    "csv-session": {"hold": 54, "poster": "The answer changes to [1,2] at both budgets"},
    "public-session": {"hold": 66, "poster": "Budget 4 now gives [82,89], compared with [63,92] before"},
    "masked-session": {"hold": 54, "poster": "Only budget 2 reaches [0,3]; masking does not reset the budget"},
}


def run(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def timestamp(frame: int) -> str:
    milliseconds = round(frame * 1000 / FPS)
    seconds, ms = divmod(milliseconds, 1000)
    minutes, sec = divmod(seconds, 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour:02}:{minute:02}:{sec:02}.{ms:03}"


def font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.truetype("DejaVuSans.ttf", size)


def caption_frame(source: Path, width: int, viewport_height: int, lines: tuple[str, str]) -> Image.Image:
    image = Image.open(source).convert("RGB")
    canvas = Image.new("RGB", (width, viewport_height + CAPTION_HEIGHT), "white")
    canvas.paste(image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    for line, size, y, color in zip(lines, (22, 20), (viewport_height + 11, viewport_height + 43), ("#20282d", "#485660")):
        face = font(size)
        if draw.textlength(line, font=face) > width - 52:
            raise ValueError(f"Caption does not fit: {line}")
        draw.text((26, y), line, fill=color, font=face)
    return canvas


def make_gif(images: list[Image.Image], durations: list[int], target: Path, colors: int = 64) -> None:
    # A shared palette keeps static application text stable through the loop.
    gif_width = 1120
    gif_height = round(images[0].height * gif_width / images[0].width)
    resized = [im.resize((gif_width, gif_height), Image.Resampling.LANCZOS) for im in images]
    sample = Image.new("RGB", (gif_width, gif_height * min(8, len(images))), "white")
    for index in range(min(8, len(images))):
        source_index = round(index * (len(images) - 1) / max(1, min(8, len(images)) - 1))
        sample.paste(resized[source_index], (0, index * gif_height))
    palette = sample.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    frames = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in resized]
    # GIF delays have 10 ms precision. Round cumulative boundaries to avoid
    # accumulated drift; typing transitions remain 130 or 140 milliseconds.
    delays = []
    elapsed_frames = elapsed_centiseconds = 0
    for frame_count in durations:
        elapsed_frames += frame_count
        next_boundary = round(elapsed_frames * 100 / FPS)
        delays.append((next_boundary - elapsed_centiseconds) * 10)
        elapsed_centiseconds = next_boundary
    frames[0].save(target, save_all=True, append_images=frames[1:], duration=delays,
                   loop=0, optimize=True, disposal=1)


def build_session(name: str, capture_root: Path, output_dir: Path, audit_dir: Path | None) -> dict:
    capture_dir = capture_root / name
    metadata = json.loads((capture_dir / "capture.json").read_text())
    frames = metadata["frames"]
    if not frames or any(frame["stage"] not in CAPTIONS for frame in frames):
        raise ValueError(f"Missing frames or unrecognized stage in {name}")
    if any(a["timeMs"] > b["timeMs"] for a, b in zip(frames, frames[1:])):
        raise ValueError(f"Capture timestamps are not ordered in {name}")
    sources = [(capture_dir / frame["file"]).resolve() for frame in frames]
    for source in sources:
        if source.parent != capture_dir.resolve():
            raise ValueError("Capture frame must be inside its session directory")
    sizes = [Image.open(source).size for source in sources]
    width = max(size[0] for size in sizes)
    viewport_height = max(size[1] for size in sizes)
    width += width % 2
    viewport_height += viewport_height % 2
    config = SESSIONS[name]
    durations = [TRANSITION_FRAMES] * len(frames)
    stage_ranges = []
    first = 0
    for stage, group in itertools.groupby(frames, key=lambda frame: frame["stage"]):
        count = len(list(group))
        last = first + count - 1
        durations[last] = 90 if stage in RESULT_STAGES else config["hold"]
        stage_ranges.append((stage, first, last))
        first = last + 1
    total_frames = sum(durations)
    if not 25 <= total_frames / FPS <= 40:
        raise ValueError(f"Unexpected playback duration for {name}: {total_frames / FPS}")
    padded_images = [caption_frame(source, width, viewport_height, CAPTIONS[frame["stage"]])
                     for source, frame in zip(sources, frames)]
    poster_index = next(last for stage, _, last in stage_ranges if stage == config["poster"])
    padded_images[poster_index].save(output_dir / f"{name}.png", optimize=True)
    make_gif(padded_images, durations, output_dir / f"{name}.gif", colors=40 if name == "masked-session" else 64)
    with tempfile.TemporaryDirectory(prefix=f"{name}-encoding-") as temporary:
        temporary = Path(temporary)
        concat = []
        for index, (image, frame_count) in enumerate(zip(padded_images, durations)):
            path = temporary / f"{index:04}.png"
            image.save(path)
            escaped = str(path).replace("'", "'\\''")
            concat.extend((f"file '{escaped}'", f"option framerate {FPS}", f"duration {frame_count / FPS:.9f}"))
        concat.extend((f"file '{str(path)}'", f"option framerate {FPS}"))
        manifest = temporary / "frames.txt"
        manifest.write_text("\n".join(concat) + "\n")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(manifest), "-vf", f"fps={FPS}", "-frames:v", str(total_frames),
             "-c:v", "libx264", "-preset", "slower", "-tune", "stillimage", "-crf", "26", "-g", "900",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
             "-metadata", f"comment={PROVENANCE}", str(output_dir / f"{name}.mp4")])
    cue_lines = ["WEBVTT", "", f"NOTE {PROVENANCE}", ""]
    elapsed = 0
    stage_audit = []
    for index, (stage, first, last) in enumerate(stage_ranges, 1):
        start = elapsed
        elapsed += sum(durations[first:last + 1])
        cue_lines.extend((str(index), f"{timestamp(start)} --> {timestamp(elapsed)}",
                          *CAPTIONS[stage], ""))
        stage_audit.append({"stage": stage, "first_capture": frames[first]["file"],
                            "last_capture": frames[last]["file"], "start_frame": start,
                            "end_frame": elapsed, "captions": CAPTIONS[stage]})
    (output_dir / f"{name}.vtt").write_text("\n".join(cue_lines), encoding="utf-8")
    probe = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                            str(output_dir / f"{name}.mp4")]).stdout)
    stream = probe["streams"][0]
    if (stream["codec_name"], stream["pix_fmt"], stream["r_frame_rate"]) != ("h264", "yuv420p", "30/1"):
        raise ValueError(f"Unexpected MP4 encoding: {name}")
    if int(stream["nb_frames"]) != total_frames:
        raise ValueError(f"Incorrect MP4 frame count: {name}")
    run(["ffmpeg", "-v", "error", "-i", str(output_dir / f"{name}.mp4"), "-f", "null", "-"])
    gif = Image.open(output_dir / f"{name}.gif")
    gif_duration = 0
    for frame_index in range(gif.n_frames):
        gif.seek(frame_index)
        gif.load()
        gif_duration += gif.info.get("duration", 0)
    report = {"name": name, "provenance": PROVENANCE, "source_frames": len(frames),
              "dimensions": [width, viewport_height + CAPTION_HEIGHT], "fps": FPS,
              "mp4_frames": total_frames, "mp4_seconds": total_frames / FPS,
              "gif_seconds": gif_duration / 1000, "gif_frames": gif.n_frames,
              "bytes": {extension: (output_dir / f"{name}.{extension}").stat().st_size
                        for extension in ("mp4", "gif", "png", "vtt")}}
    if audit_dir:
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit = dict(report, stages=stage_audit, ffprobe=probe,
                     source_sha256={frame["file"]: hashlib.sha256(source.read_bytes()).hexdigest()
                                    for frame, source in zip(frames, sources)})
        (audit_dir / f"{name}-encoding.json").write_text(json.dumps(audit, indent=2) + "\n")
        # Five distinct action/result stages from the output, without altering UI.
        selected = [round(index * (len(stage_ranges) - 1) / 4) for index in range(5)]
        thumbnail_width = 682
        thumbnail_height = round(padded_images[0].height * thumbnail_width / width)
        sheet = Image.new("RGB", (thumbnail_width * 2, (thumbnail_height + 30) * 3), "#eef0f2")
        draw = ImageDraw.Draw(sheet)
        for index, stage_index in enumerate(selected):
            stage, _, last = stage_ranges[stage_index]
            image = padded_images[last].resize((thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS)
            x, y = (index % 2) * thumbnail_width, (index // 2) * (thumbnail_height + 30)
            sheet.paste(image, (x, y))
            draw.text((x + 10, y + thumbnail_height + 5), f"Stage {stage_index + 1}: capture {frames[last]['file']}", fill="#20282d", font=font(16))
        sheet.save(audit_dir / f"{name}-contact.png")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capture-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--audit-dir", type=Path)
    arguments = parser.parse_args()
    for executable in ("ffmpeg", "ffprobe"):
        if not shutil.which(executable):
            parser.error(f"Required executable not found: {executable}")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    reports = [build_session(name, arguments.capture_root, arguments.output_dir, arguments.audit_dir)
               for name in SESSIONS]
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
