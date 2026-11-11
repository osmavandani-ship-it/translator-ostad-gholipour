import os, re, base64, wave, io
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
app = Flask(__name__)
API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
client = genai.Client(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = """
You are a careful Persian-English translator and language tutor.
Detect whether the input is Persian or English.
If it is English, translate it into fluent, natural Persian. Preserve meaning,
tone, names, numbers and formatting. Use correct Persian spelling, punctuation,
half-spaces, and right-to-left-friendly natural writing. Also provide a natural
Persian-script pronunciation guide for the English input.
If it is Persian, translate it into natural, grammatically correct English.
Also provide a learner-friendly pronunciation guide for the English translation.
Do not transliterate the whole Persian input unless useful.
Return ONLY valid JSON with these keys:
source_language ("fa" or "en"), source_text, translated_text,
translated_language ("fa" or "en"), pronunciation_fa.
The pronunciation_fa field must represent how the English text is pronounced
using Persian letters. For English input, pronounce source_text; for Persian
input, pronounce the English translation. Do not add markdown fences.
"""

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/status")
def status():
    return jsonify({"configured": bool(client)})

@app.post("/api/translate")
def translate():
    if not client:
        return jsonify({"error": "کلید API تنظیم نشده است. فایل .env را تکمیل کنید."}), 503
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "لطفاً ابتدا متن یا واژه‌ای وارد کنید."}), 400
    if len(text) > 12000:
        return jsonify({"error": "متن طولانی است. لطفاً متن را کوتاه‌تر کنید."}), 400
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[SYSTEM_PROMPT, "\n\nInput:\n" + text],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        import json
        result = json.loads(response.text)
        required = ["source_language", "source_text", "translated_text",
                    "translated_language", "pronunciation_fa"]
        if not all(k in result for k in required):
            raise ValueError("پاسخ مدل کامل نیست.")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "ترجمه انجام نشد: " + str(e)}), 500

@app.post("/api/speak")
def speak():
    if not client:
        return jsonify({"error": "کلید API تنظیم نشده است."}), 503
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    lang = data.get("language", "en")
    if not text:
        return jsonify({"error": "متنی برای خواندن وجود ندارد."}), 400
    if len(text) > 5000:
        return jsonify({"error": "برای تبدیل گفتار، متن را کوتاه‌تر کنید."}), 400

    language_label = "Persian" if lang == "fa" else "English"
    voice = "Kore" if lang == "en" else "Aoede"
    prompt = (
        f"Read the following {language_label} text aloud clearly and naturally. "
        "Use accurate pronunciation, a moderate pace, and natural pauses. "
        "Do not translate, summarize, or add any words. Text: " + text
    )
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice
                        )
                    )
                )
            )
        )
        audio_bytes = None
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                audio_bytes = part.inline_data.data
                break
        if not audio_bytes:
            raise ValueError("داده صوتی از سرویس دریافت نشد.")
        # Gemini TTS PCM: 24 kHz, mono, 16-bit
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(audio_bytes)
        encoded = base64.b64encode(wav_buffer.getvalue()).decode("ascii")
        return jsonify({"audio": encoded, "mime": "audio/wav"})
    except Exception as e:
        return jsonify({"error": "تولید صدا انجام نشد: " + str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
