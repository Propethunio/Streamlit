import streamlit as st

def generate_game_scene(client, scene_description):
    """
    Na podstawie opisu sytuacji generuje prompt, 
    a następnie gotowy obraz z DALL-E 3.
    """
    try:
        # 1. Poproś model o zamianę opisu przygody na profesjonalny prompt dla DALL-E
        system_refiner = "Convert the given RPG story event into a concise, detailed English image generation prompt. Style: Cinematic dark fantasy concept art, highly detailed, moody lighting."
        
        response = client.chat.completions.create(
            model="gemini-2.5-flash", # lub gpt-4o, zależnie czego używasz
            messages=[
                {"role": "system", "content": system_refiner},
                {"role": "user", "content": f"Zamień to zdarzenie w prompt artystyczny: {scene_description}"}
            ],
            temperature=0.6
        )
        
        refined_prompt = response.choices[0].message.content
        
        # 2. Wygeneruj obraz za pomocą DALL-E 3
        image_response = client.images.generate(
            model="dall-e-3",
            prompt=refined_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        return image_response.data[0].url
    except Exception as e:
        # Jeśli brakuje środków na API lub wystąpi błąd, zwracamy None, by nie crashować gry
        print(f"Błąd generowania obrazu: {e}")
        return None