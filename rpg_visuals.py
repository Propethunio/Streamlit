import streamlit as st
import os
import base64
from google import genai
from google.genai import types

def generate_game_scene(client_not_used, story_text):
    """
    Generuje darmowy obraz lokacji przy użyciu Google Imagen 3 na podstawie klucza GEMINI.
    """
    try:
        # Pobieramy klucz API bezpośrednio z secrets Streamlita lub zmiennych środowiskowych
        api_key = st.secrets.get("API_KEY", os.environ.get("GEMINI_API_KEY", ""))
        
        if not api_key:
            st.warning("⚠️ Brak klucza API dla Imagen 3 w secrets.")
            return None
            
        # Inicjalizacja dedykowanego klienta Google GenAI
        ai_client = genai.Client(api_key=api_key)
        
        # Przygotowanie bezpiecznego i klimatycznego promptu dla cyberpunku
        refined_prompt = (
            f"Cyberpunk isometric video game scene, neon lighting, dark atmospheric, "
            f"detailed digital art, high quality illustration, based on this scene: {story_text[:150]}"
        )
        
        # Wywołanie darmowego modelu Imagen 3
        result = ai_client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=refined_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="1:1",
                person_generation="ALLOW_ADULT", # Zapobiega blokowaniu humanoidalnych postaci/wrogów
                safety_filter_level="BLOCK_MEDIUM_AND_ABOVE"
            )
        )
        
        # Pobieramy bajty obrazu prosto z odpowiedzi API
        generated_image = result.generated_images[0]
        image_bytes = generated_image.image.image_bytes
        
        # Konwertujemy do Base64, aby Streamlit mógł wyświetlić obraz lokalnie (nie wygaśnie po godzinie)
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64_img}"
        
        return data_url

    except Exception as e:
        st.warning(f"⚠️ Problem z darmowym Google Imagen: {str(e)}")
        return None