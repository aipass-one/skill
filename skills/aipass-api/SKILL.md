---
name: aipass-api
description: Complete AI Pass API skill for text generation, image generation, image editing, text-to-speech, transcription, and video generation. Uses API key auth — no browser needed.
version: 2.0.0
---

# AI Pass API — Complete Skill

All AI features via `$AIPASS_API_KEY`. No browser, no SDK, no OAuth needed.

## Auth
All endpoints: `Authorization: Bearer $AIPASS_API_KEY`
Get your key: https://aipass.one/panel/developer.html → API Keys

## Base URL
`https://aipass.one/apikey/v1`

## List Available Models
```bash
curl -s https://aipass.one/apikey/v1/models -H "Authorization: Bearer $AIPASS_API_KEY"
```

---

## Available Models (as of 2026-02-14)

### Text Generation (Chat Completions)
| Model | Notes |
|-------|-------|
| `gpt-5-nano` | Cheapest, simple tasks |
| `gpt-5-mini` | Good balance, recommended default |
| `gpt-5` | Premium OpenAI |
| `gpt-5.1` | Latest OpenAI |
| `gpt-5.1-codex` | Code-optimized |
| `gpt-5.1-codex-mini` | Code-optimized, cheaper |
| `claude-opus-4-6` | Anthropic best (reasoning, code) |
| `claude-sonnet-4-5` | Anthropic premium |
| `claude-haiku-4-5` | Anthropic fast/cheap |
| `gemini/gemini-2.5-flash` | Google fast |
| `gemini/gemini-2.5-flash-lite` | Google cheapest |
| `gemini/gemini-2.5-pro` | Google premium |
| `gemini/gemini-3-pro-preview` | Google latest |
| `gemini/gemini-3-flash-preview` | Google latest fast |
| `gemini/gemma-3-27b-it` | Google open model |
| `cerebras/qwen-3-32b` | Fast inference |
| `cerebras/gpt-oss-120b` | Large open model |

### Image Generation
| Model | Notes |
|-------|-------|
| `flux-pro/v1.1` | Fast, good quality (~$0.05) |
| `flux-pro/v1.1-ultra` | High quality |
| `imagen4/preview/ultra` | Google's best |
| `standard/1024-x-1024/dall-e-3` | DALL-E 3 |
| `gpt-image-1` | OpenAI native image gen |
| `gpt-image-1-mini` | OpenAI image gen, cheaper |
| `recraft/v3` | Design-focused |
| `seedream/v3` | ByteDance |
| `dreamina/v3.1` | ByteDance |

### Image Editing
| Model | Notes |
|-------|-------|
| `gemini/gemini-3-pro-image-preview` | Best for editing (via chat completions) |
| `gemini/gemini-2.5-flash-image-preview` | Faster, cheaper editing |

### Text-to-Speech
| Model | Notes |
|-------|-------|
| `tts-1` | Standard quality |
| `tts-1-hd` | High quality |
| `gpt-4o-mini-tts` | OpenAI mini TTS |

### Text Embeddings
| Model | Notes |
|-------|-------|
| `text-embedding-3-small` | Fast, cheap, 1536 dimensions |
| `text-embedding-3-large` | Higher quality, 3072 dimensions |

### Audio (Speech-to-Text + Audio Understanding)
| Model | Notes |
|-------|-------|
| `whisper-1` | Transcription |
| `gpt-4o-audio-preview` | Audio understanding |

### Video Generation
| Model | Notes |
|-------|-------|
| `gemini/veo-3.0-fast-generate-preview` | Fast video |
| `gemini/veo-3.0-generate-preview` | Quality video |
| `gemini/veo-3.1-fast-generate-preview` | Latest fast video |
| `openai/sora-2` | OpenAI video |
| `openai/sora-2-pro` | OpenAI premium video |

---

## 1. Text Generation (Chat Completions)

**Endpoint:** `POST /apikey/v1/chat/completions`

```bash
curl -s -X POST https://aipass.one/apikey/v1/chat/completions \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Your prompt here"}
    ]
  }'
```

**Response:** `response.choices[0].message.content`

### Python
```python
import requests, os
AIPASS_API_KEY = os.environ["AIPASS_API_KEY"]

def chat(prompt, model="gpt-5-mini", system="You are a helpful assistant."):
    r = requests.post("https://aipass.one/apikey/v1/chat/completions",
        headers={"Authorization": f"Bearer {AIPASS_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]})
    return r.json()["choices"][0]["message"]["content"]
```

---

## 2. Image Generation

**Endpoint:** `POST /apikey/v1/images/generations`

```bash
curl -s -X POST https://aipass.one/apikey/v1/images/generations \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-pro/v1.1",
    "prompt": "A cute monster with big eyes and small horns, digital art",
    "size": "1024x1024",
    "n": 1
  }'
```

**Response:** `response.data[0].url` (image URL) or `response.data[0].b64_json` (base64)

### Python
```python
def generate_image(prompt, model="flux-pro/v1.1", size="1024x1024"):
    r = requests.post("https://aipass.one/apikey/v1/images/generations",
        headers={"Authorization": f"Bearer {AIPASS_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "prompt": prompt, "size": size, "n": 1})
    return r.json()["data"][0]["url"]
```

### Download image
```bash
URL=$(curl -s -X POST https://aipass.one/apikey/v1/images/generations \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"flux-pro/v1.1","prompt":"your prompt","size":"1024x1024","n":1}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['data'][0]['url'])")
curl -s "$URL" -o output.png
```

---

## 3. Image Editing

**Endpoint:** `POST /apikey/v1/chat/completions` (routes through chat completions for Gemini image models)

⚠️ **Note:** The `/apikey/v1/images/edits` endpoint has a known bug. Use chat completions with base64 image instead.

```python
import base64

def edit_image(image_path, prompt, model="gemini/gemini-3-pro-image-preview"):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
    
    r = requests.post("https://aipass.one/apikey/v1/chat/completions",
        headers={"Authorization": f"Bearer {AIPASS_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            }]
        })
    return r.json()["choices"][0]["message"]["content"]
```

### Bash
```bash
B64=$(base64 -w0 input.png)
curl -s -X POST https://aipass.one/apikey/v1/chat/completions \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini/gemini-3-pro-image-preview",
    "messages": [{"role": "user", "content": [
      {"type": "text", "text": "Remove the background"},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,'$B64'"}}
    ]}]
  }'
```

---

## 4. Text-to-Speech

**Endpoint:** `POST /apikey/v1/audio/speech`

**Voices:** `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`

```bash
curl -s -X POST https://aipass.one/apikey/v1/audio/speech \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello, this is AI Pass speaking!",
    "voice": "nova"
  }' --output speech.mp3
```

### Python
```python
def text_to_speech(text, voice="nova", model="tts-1", output="speech.mp3"):
    r = requests.post("https://aipass.one/apikey/v1/audio/speech",
        headers={"Authorization": f"Bearer {AIPASS_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "input": text, "voice": voice})
    with open(output, "wb") as f:
        f.write(r.content)
    return output
```

---

## 5. Audio Transcription (Speech-to-Text)

**Endpoint:** `POST /apikey/v1/audio/transcriptions`

**Formats:** mp3, mp4, mpeg, mpga, m4a, wav, webm, ogg

```bash
curl -s -X POST https://aipass.one/apikey/v1/audio/transcriptions \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=en"
```

**Response:** `response.text`

### Python
```python
def transcribe(file_path, language="en"):
    with open(file_path, "rb") as f:
        r = requests.post("https://aipass.one/apikey/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {AIPASS_API_KEY}"},
            files={"file": f},
            data={"model": "whisper-1", "language": language})
    return r.json()["text"]
```

---

## 6. Video Generation (Async)

**Endpoint:** `POST /apikey/v1/videos`

Video generation is async — start, poll, download.

```python
import time

def generate_video(prompt, model="gemini/veo-3.1-fast-generate-preview", seconds=5):
    # Start
    r = requests.post("https://aipass.one/apikey/v1/videos",
        headers={"Authorization": f"Bearer {AIPASS_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "prompt": prompt, "seconds": seconds})
    video_id = r.json()["videoId"]
    
    # Poll
    while True:
        status = requests.get(f"https://aipass.one/apikey/v1/videos/{video_id}/status",
            headers={"Authorization": f"Bearer {AIPASS_API_KEY}"}).json()
        if status["status"] == "completed":
            return status["downloadUrl"]
        elif status["status"] == "failed":
            raise Exception(f"Failed: {status}")
        time.sleep(5)
```

### Bash
```bash
# Start video generation
VIDEO_ID=$(curl -s -X POST https://aipass.one/apikey/v1/videos \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemini/veo-3.1-fast-generate-preview","prompt":"A monster dancing in the rain","seconds":5}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['videoId'])")

# Poll status
curl -s "https://aipass.one/apikey/v1/videos/$VIDEO_ID/status" \
  -H "Authorization: Bearer $AIPASS_API_KEY"
```

---

## Quick Reference

| Feature | Endpoint | Recommended Model | Response |
|---------|----------|-------------------|----------|
| Text gen | `POST /chat/completions` | `gpt-5-mini` | `.choices[0].message.content` |
| Image gen | `POST /images/generations` | `flux-pro/v1.1` | `.data[0].url` |
| Image edit | `POST /chat/completions` | `gemini/gemini-3-pro-image-preview` | base64 in content |
| TTS | `POST /audio/speech` | `tts-1` | binary audio |
| STT | `POST /audio/transcriptions` | `whisper-1` | `.text` |
| Video | `POST /videos` | `gemini/veo-3.1-fast-generate-preview` | async → poll → `.downloadUrl` |
| Embeddings | `POST /embeddings` | `text-embedding-3-small` | `.data[0].embedding` |
| List models | `GET /models` | — | `.data[].id` |

## 7. Text Embeddings

**Endpoint:** `POST /apikey/v1/embeddings`

```bash
curl -s -X POST https://aipass.one/apikey/v1/embeddings \
  -H "Authorization: Bearer $AIPASS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small",
    "input": "Your text to embed"
  }'
```

**Response:** `response.data[0].embedding` (array of floats)

### Python
```python
def embed(text, model="text-embedding-3-small"):
    r = requests.post("https://aipass.one/apikey/v1/embeddings",
        headers={"Authorization": f"Bearer {AIPASS_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "input": text})
    return r.json()["data"][0]["embedding"]

# Batch embedding
def embed_batch(texts, model="text-embedding-3-small"):
    r = requests.post("https://aipass.one/apikey/v1/embeddings",
        headers={"Authorization": f"Bearer {AIPASS_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "input": texts})
    return [d["embedding"] for d in r.json()["data"]]
```

---

## Cost Tips
- `gpt-5-nano` for simple text (cheapest)
- `gemini/gemini-2.5-flash-lite` for cheap text with good quality
- `flux-pro/v1.1` for standard images (~$0.05)
- `whisper-1` for audio — very cheap
- `tts-1` cheaper than `tts-1-hd`
- `gpt-image-1-mini` cheaper than `gpt-image-1`

## Building Apps with AI Pass SDK

If building web apps (not server-side), use the JS SDK instead:

```html
<script src="https://aipass.one/aipass-sdk.js"></script>
<script>
AiPass.initialize({ clientId: 'YOUR_CLIENT_ID', requireLogin: true, darkMode: true });
</script>
```

Get your Client ID: https://aipass.one/panel/developer.html → OAuth2 Clients

SDK methods mirror the API: `AiPass.generateCompletion()`, `AiPass.generateImage()`, `AiPass.editImage()`, `AiPass.generateSpeech()`, `AiPass.transcribeAudio()`, `AiPass.generateVideo()`

Developers earn **50% commission** on every API call their users make.

Full SDK docs: https://aipass.one/docs/sdk/reference.html
