import sys
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import voice_prompt


def test_audio_file_must_exist(tmp_path):
    missing = tmp_path / "missing.wav"

    with pytest.raises(FileNotFoundError):
        voice_prompt.transcribe_audio_file(missing, model="whisper-1", language="ko", prompt=None)


def test_transcribe_audio_file_passes_expected_openai_args(tmp_path):
    audio = tmp_path / "prompt.wav"
    audio.write_bytes(b"fake audio")
    client = MagicMock()
    client.audio.transcriptions.create.return_value = MagicMock(text="테스트 프롬프트")

    result = voice_prompt.transcribe_audio_file(
        audio,
        model="whisper-1",
        language="ko",
        prompt="개발 작업 프롬프트",
        client=client,
    )

    assert result == "테스트 프롬프트"
    kwargs = client.audio.transcriptions.create.call_args.kwargs
    assert kwargs["model"] == "whisper-1"
    assert kwargs["language"] == "ko"
    assert kwargs["prompt"] == "개발 작업 프롬프트"


def test_write_wav_writes_mono_16bit_file(tmp_path):
    wav_path = tmp_path / "recording.wav"

    voice_prompt.write_wav(wav_path, [b"\x00\x00\x01\x00"], samplerate=16000, channels=1)

    with wave.open(str(wav_path), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16000
        assert wav.readframes(2) == b"\x00\x00\x01\x00"


def test_output_text_is_copied_when_pyperclip_exists(tmp_path):
    output = tmp_path / "prompt.txt"
    clipboard = MagicMock()

    with patch.dict(sys.modules, {"pyperclip": clipboard}):
        voice_prompt.write_prompt_text("  hello  ", output, copy=True)

    assert output.read_text(encoding="utf-8") == "hello\n"
    clipboard.copy.assert_called_once_with("hello")
