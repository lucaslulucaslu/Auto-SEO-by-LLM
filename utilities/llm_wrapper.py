import tiktoken
from langsmith import traceable
from google import genai
import os
from google.genai import types

MODEL = ["gemini-2.0-flash"]
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def tokens_count(text: str, model=0):
    encoding = tiktoken.encoding_for_model(MODEL[model])
    token_length = len(encoding.encode(text))
    return token_length


def llm_wrapper(
    sys_prompt,
    user_prompt,
    response_format=None,
    model=0,
):
    if response_format:
        response = llm_wrapper_raw(
            sys_prompt,
            user_prompt,
            response_format=response_format,
            model=model,
        )
        return response.parsed
    else:
        response = llm_wrapper_raw(
            sys_prompt,
            user_prompt,
            model=model,
        )
        return response.text


@traceable(
    run_type="llm", metadata={"ls_model_name": "gemini-2.0-flash", "ls_provider": "google"}
)
def llm_wrapper_raw(
    sys_prompt,
    user_prompt,
    response_format=None,
    model=0,
):
    if response_format:
        return client.models.generate_content(
            model=MODEL[model],
            contents=sys_prompt+user_prompt,
            config={
                "response_mime_type":"application/json",
                "response_schema": response_format,
            }
        )
    else:
        return client.models.generate_content(
            model=MODEL[model],
            contents=sys_prompt+user_prompt,
        )


@traceable
def llm_image_wrapper(image_query):
    return (
        client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=image_query,
            config=types.GenerateImagesConfig(
                number_of_images=1,  # Number of images to generate
                aspect_ratio="16:9",  # Aspect ratio of the image
            ),
        )
        .generated_images[0]
    )

if __name__ == "__main__":
    from io import BytesIO
    from PIL import Image
    
    image_query = "A futuristic city skyline at sunset."
    generated_image=llm_image_wrapper(image_query)
    with Image.open(BytesIO(generated_image.image.image_bytes)) as image:
        image.show()