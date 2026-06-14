import base64
import os

import streamlit as st
from google import genai
from google.genai import types


def generate_game_scene(story_text):
    """Generuje obraz lokacji przy użyciu Google Imagen 3 na podstawie tekstu sceny."""
    try:
        api_key = st.secrets.get("API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        if not api_key:
            st.error("⚠️ Brak klucza API dla Imagen 3 w secrets (klucz 'API_KEY').")
            return None

        ai_client = genai.Client(api_key=api_key)
        prompt = (
            "Cyberpunk isometric video game scene, neon lighting, dark atmospheric, "
            f"detailed digital art, high quality illustration, based on this scene: {story_text[:150]}"
        )
        result = ai_client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="1:1",
                person_generation="ALLOW_ADULT",
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE",
            ),
        )

        if not result.generated_images:
            st.warning("⚠️ Imagen nie zwrócił żadnego obrazu (możliwe blokowanie przez safety filter).")
            return None

        image_bytes = result.generated_images[0].image.image_bytes
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    except Exception as e:
        st.error(f"⚠️ Błąd Google Imagen 3: {e}")
        return None
