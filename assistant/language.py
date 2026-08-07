from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

# Languages CampusMitra actively supports translating to/from.
# Anything detected outside this set is almost certainly a langdetect
# misfire on short/romanized text — safer to fall back to English than
# confidently mistranslate into an unintended language.
SUPPORTED_LANGUAGES = {"en", "hi", "mr", "gu", "ta", "te", "kn", "bn", "ml", "pa"}


def detect_language(text):
    try:
        detected = detect(text)
    except LangDetectException:
        return "en"

    if detected not in SUPPORTED_LANGUAGES:
        return "en"

    return detected


def translate(text, target_lang):
    """Translates text to the target language. If target_lang is already English
    or translation fails for any reason, returns the original text unchanged rather
    than crashing the whole graph over a translation hiccup."""
    if target_lang == "en":
        return text
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return text