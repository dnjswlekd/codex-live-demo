# codex-live-demo

## Voice prompt

OpenAI speech-to-text로 마이크에 말한 내용을 텍스트 프롬프트로 저장할 수 있습니다.

```bash
export OPENAI_API_KEY="sk-..."
bin/voice-prompt
```

기본 동작:

- 8초 동안 마이크를 녹음합니다.
- `whisper-1` 모델로 한국어 음성을 텍스트로 변환합니다.
- 결과를 `.voice-prompt.txt`에 저장하고 클립보드에 복사합니다.

자주 쓰는 옵션:

```bash
# 15초 녹음
bin/voice-prompt --duration 15

# Enter를 누를 때까지 녹음
bin/voice-prompt --duration 0

# 이미 녹음된 파일 전사
bin/voice-prompt --file ./prompt.wav

# 더 최신 전사 모델 사용
bin/voice-prompt --model gpt-4o-mini-transcribe
```
