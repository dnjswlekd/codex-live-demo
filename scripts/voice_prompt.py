#!/usr/bin/env python3
"""
Record or transcribe a spoken prompt with OpenAI speech-to-text.

Examples:
    python3 scripts/voice_prompt.py
    python3 scripts/voice_prompt.py --duration 15
    python3 scripts/voice_prompt.py --file ./prompt.wav --model gpt-4o-mini-transcribe
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_MODEL = "whisper-1"
DEFAULT_LANGUAGE = "ko"
DEFAULT_OUTPUT = Path(".voice-prompt.txt")
DEFAULT_SAMPLE_RATE = 16_000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="마이크로 말한 내용을 OpenAI speech-to-text로 텍스트 프롬프트로 변환합니다."
    )
    parser.add_argument("--file", type=Path, help="이미 녹음된 오디오 파일을 전사합니다.")
    parser.add_argument(
        "--duration",
        type=float,
        default=8.0,
        help="마이크 녹음 시간(초). 0 이하로 주면 Enter를 누를 때까지 녹음합니다.",
    )
    parser.add_argument(
        "--audio-out",
        type=Path,
        help="녹음 wav 파일을 남길 경로입니다. 생략하면 임시 파일을 사용합니다.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="전사 텍스트 저장 경로입니다.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="전사 모델입니다. 기본값: whisper-1")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="입력 언어 코드입니다. 기본값: ko")
    parser.add_argument("--prompt", help="전사 정확도 개선용 힌트 문장입니다.")
    parser.add_argument("--device", help="sounddevice 입력 장치명 또는 ID입니다.")
    parser.add_argument("--no-copy", action="store_true", help="클립보드 복사를 건너뜁니다.")
    return parser


def get_openai_client():
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY 환경변수가 필요합니다.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다. .venv/bin/pip install -r requirements-voice.txt") from exc

    return OpenAI()


def write_wav(path: Path, frames: Iterable[bytes], *, samplerate: int, channels: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(samplerate)
        wav.writeframes(b"".join(frames))


def record_audio_file(
    path: Path,
    *,
    duration: float,
    samplerate: int = DEFAULT_SAMPLE_RATE,
    channels: int = 1,
    device: Optional[str] = None,
) -> Path:
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError(
            "sounddevice 패키지가 설치되어 있지 않습니다. .venv/bin/pip install -r requirements-voice.txt"
        ) from exc

    frames = []

    def callback(indata, frame_count, time_info, status):
        if status:
            print(f"recording status: {status}", file=sys.stderr)
        frames.append(bytes(indata))

    print("녹음 시작. 프롬프트를 말하세요.", file=sys.stderr)
    with sd.RawInputStream(
        samplerate=samplerate,
        channels=channels,
        dtype="int16",
        device=device,
        callback=callback,
    ):
        if duration > 0:
            time.sleep(duration)
        else:
            input("녹음을 끝내려면 Enter를 누르세요...")

    write_wav(path, frames, samplerate=samplerate, channels=channels)
    print(f"녹음 저장: {path}", file=sys.stderr)
    return path


def transcribe_audio_file(
    audio_path: Path,
    *,
    model: str,
    language: Optional[str],
    prompt: Optional[str],
    client=None,
) -> str:
    if not audio_path.exists():
        raise FileNotFoundError(audio_path)

    client = client or get_openai_client()
    request = {"model": model, "file": None}
    if language:
        request["language"] = language
    if prompt:
        request["prompt"] = prompt

    with audio_path.open("rb") as audio_file:
        request["file"] = audio_file
        result = client.audio.transcriptions.create(**request)

    if isinstance(result, str):
        return result.strip()
    return getattr(result, "text", str(result)).strip()


def copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        pass

    try:
        subprocess.run(["pbcopy"], input=text, text=True, check=True)
        return True
    except Exception:
        return False


def write_prompt_text(text: str, output: Path, *, copy: bool) -> None:
    cleaned = text.strip()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(cleaned + "\n", encoding="utf-8")

    if copy and cleaned:
        if copy_to_clipboard(cleaned):
            print("클립보드에 복사했습니다.", file=sys.stderr)
        else:
            print("WARN: 클립보드 복사에 실패했습니다.", file=sys.stderr)


def choose_audio_source(args: argparse.Namespace) -> tuple[Path, bool]:
    if args.file:
        return args.file, False

    if args.audio_out:
        return args.audio_out, False

    fd, name = tempfile.mkstemp(prefix="voice-prompt-", suffix=".wav")
    os.close(fd)
    return Path(name), True


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    audio_path, should_delete = choose_audio_source(args)

    try:
        if not args.file:
            record_audio_file(audio_path, duration=args.duration, device=args.device)

        text = transcribe_audio_file(
            audio_path,
            model=args.model,
            language=args.language,
            prompt=args.prompt,
        )
        write_prompt_text(text, args.output, copy=not args.no_copy)
        print(text)
        print(f"\n저장됨: {args.output}", file=sys.stderr)
        return 0
    finally:
        if should_delete:
            audio_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
