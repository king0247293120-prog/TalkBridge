from app.database.database import SessionLocal
from app.database.models import TranslationEntry

db = SessionLocal()

try:
    existing = (
        db.query(TranslationEntry)
        .filter(
            TranslationEntry.source_text == "Good morning",
            TranslationEntry.source_language == "English",
            TranslationEntry.target_language == "Twi",
        )
        .first()
    )

    if existing:
        existing.translated_text = "Maakye"
        existing.status = "verified"
        existing.provider = "human"
        existing.translation_method = "human"
    else:
        entry = TranslationEntry(
            source_text="Good morning",
            translated_text="Maakye",
            source_language="English",
            target_language="Twi",
            provider="human",
            status="verified",
            translation_method="human",
            confidence=None,
        )

        db.add(entry)

    db.commit()

    print("Test translation added successfully.")

except Exception as error:
    db.rollback()
    print(f"Error adding test translation: {error}")
    raise

finally:
    db.close()