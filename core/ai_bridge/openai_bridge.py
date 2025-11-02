import os
from dotenv import load_dotenv

load_dotenv()

# --- MODEL FALLBACK CHAIN ---
# Try the configured model first, then fallback gracefully
_model_candidates = [
    os.getenv("RESEARCH_MODEL"),
    os.getenv("OPTIMIZER_MODEL"),
    "gpt-5-turbo",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]

# pick the first one available
DEFAULT_MODEL = next((m for m in _model_candidates if m), "gpt-4o")

def get_model():
    """Return the best available model string."""
    return DEFAULT_MODEL

def get_openai_client():
    """Return an OpenAI client using best available key."""
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY in .env")
        return OpenAI(api_key=api_key)
    except Exception as e:
        print(f"[WARN] Could not initialize OpenAI client: {e}")
        return None

if __name__ == "__main__":
    print(f"[INFO] Using model: {get_model()}")
