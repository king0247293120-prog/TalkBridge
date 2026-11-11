
import os
import logging

import torch
import runpod

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_ID = os.getenv("MODEL_ID", "google/madlad400-3b-mt")
MAX_INPUT_TOKENS = int(os.getenv("MAX_INPUT_TOKENS", "512"))
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "256"))
NUM_BEAMS = int(os.getenv("NUM_BEAMS", "4"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("talkbridge-worker")

LANGUAGE_CODES = {
    "english": "en",
    "french": "fr",
    "spanish": "es",
    "german": "de",
    "chinese": "zh",
    "arabic": "ar",
    "japanese": "ja",
    "korean": "ko",
    "portuguese": "pt",
    "hindi": "hi",
    "italian": "it",
    "russian": "ru",
    "dutch": "nl",
    "turkish": "tr",
    "swedish": "sv",
    "polish": "pl",
    "twi": "ak",
    "akan": "ak",
    "fante": "ak",
    "ewe": "ee",
    "ga": "gaa",
    "dagbani": "dag",
}

tokenizer = None
model = None
device = None


@runpod.serverless.register_prestart_hook
def load_model():
    global tokenizer, model, device

    logger.info("Loading TalkBridge translation model...")

    if not torch.cuda.is_available():
        raise RuntimeError("A CUDA-enabled GPU is required.")

    device = "cuda"

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        use_fast=False,
    )

    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto",
        low_cpu_mem_usage=True,
    )

    model.eval()
    logger.info("Translation model loaded successfully.")


def get_target_code(target_language):
    language_key = target_language.strip().casefold()
    code = LANGUAGE_CODES.get(language_key)

    if not code:
        raise ValueError(
            f"Unsupported language: {target_language}"
        )

    language_token = f"<2{code}>"

    if language_token not in tokenizer.get_vocab():
        raise ValueError(
            f"The model does not contain {language_token}."
        )

    return code


def translate_text(text, source_language, target_language):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Translation text cannot be empty.")

    target_code = get_target_code(target_language)

    model_input = f"<2{target_code}> {text.strip()}"

    inputs = tokenizer(
        model_input,
        return_tensors="pt",
        truncation=False,
    )

    input_length = inputs["input_ids"].shape[1]

    if input_length > MAX_INPUT_TOKENS:
        raise ValueError(
            f"Text is too long. Maximum input is {MAX_INPUT_TOKENS} tokens."
        )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
    }

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            num_beams=NUM_BEAMS,
            do_sample=False,
            early_stopping=True,
        )

    translated_text = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True,
    ).strip()

    if not translated_text:
        raise RuntimeError("The model returned an empty translation.")

    return translated_text


def handler(job):
    job_input = job.get("input", {})

    text = job_input.get("text")
    source_language = job_input.get("source_language")
    target_language = job_input.get("target_language")

    if not all([text, source_language, target_language]):
        raise ValueError(
            "text, source_language and target_language are required."
        )

    logger.info(
        "Translation request: %s -> %s",
        source_language,
        target_language,
    )

    translated_text = translate_text(
        text=text,
        source_language=source_language,
        target_language=target_language,
    )

    return {
        "translated_text": translated_text,
        "source_language": source_language,
        "target_language": target_language,
        "model": MODEL_ID,
        "provider": "runpod_serverless",
    }


if __name__ == "__main__":
    runpod.serverless.start({
        "handler": handler,
        "prestart_timeout": 900,
    })
