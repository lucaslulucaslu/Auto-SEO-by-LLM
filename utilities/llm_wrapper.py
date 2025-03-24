from langfuse.decorators import observe, langfuse_context
from google import genai
import os
from google.genai import types

MODEL = ["gemini-2.0-flash"]
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
RETRY_LIMIT = 5  # Retry limit for image generation


def tokens_count(text: str, model=0):
    token_length = client.models.count_tokens(model=MODEL[model], contents=text)
    return token_length


@observe(as_type="generation")
def llm_wrapper_raw(
    sys_prompt,
    user_prompt,
    response_format=None,
    model=0,
):
    if response_format:
        response = client.models.generate_content(
            model=MODEL[model],
            contents=sys_prompt + user_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": response_format,
            },
        )
        langfuse_context.update_current_observation(
            model=MODEL[model],
            output=response.parsed,
            usage_details={
                "input": response.usage_metadata.prompt_token_count,
                "output": response.usage_metadata.candidates_token_count,
                "total": response.usage_metadata.total_token_count,
            },
        )
    else:
        response = client.models.generate_content(
            model=MODEL[model],
            contents=sys_prompt + user_prompt,
        )
        langfuse_context.update_current_observation(
            model=MODEL[model],
            output=response.text,
            usage_details={
                "input": response.usage_metadata.prompt_token_count,
                "output": response.usage_metadata.candidates_token_count,
                "total": response.usage_metadata.total_token_count,
            },
        )

    return response


@observe(as_type="generation")
def llm_image_wrapper(image_query):
    retry = RETRY_LIMIT
    image_queries = [image_query]  # Store the original query for logging
    while retry > 0:
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=image_query,
            config=types.GenerateImagesConfig(
                number_of_images=1,  # Number of images to generate
                aspect_ratio="16:9",  # Aspect ratio of the image
            ),
        )
        if response.generated_images:
            langfuse_context.update_current_observation(
                model="imagen-3.0-generate-002",
                input=image_queries,
                output={"image generated": True, "tried": RETRY_LIMIT + 1 - retry},
                cost_details={
                    "input": 0,
                    "output": 0.04,
                },
            )
            break
        else:
            langfuse_context.update_current_observation(
                model="imagen-3.0-generate-002",
                input=image_queries,
                output={
                    "image generated": False,
                    "tried": RETRY_LIMIT + 1 - retry,
                    "response": response,
                },
                cost_details={
                    "input": 0,
                    "output": 0,
                },
                tags=["image_generation_retried"]
            )
            image_query = llm_wrapper_raw(
                sys_prompt=f"Generate one new image prompt that will not violate google's policy based on original prompt: \n\n{image_query}\n\n\
                    Only output the new prompt without any additional text.",
                user_prompt="",
            ).text
            image_queries.append(image_query)  # Append the new query for logging
            retry -= 1
    return response.generated_images[0]


if __name__ == "__main__":
    # from io import BytesIO
    # from PIL import Image

    # image_query = "A futuristic city skyline at sunset."
    # generated_image=llm_image_wrapper(image_query)
    # with Image.open(BytesIO(generated_image.image.image_bytes)) as image:
    #     image.show()
    response = llm_wrapper_raw(
        sys_prompt="You are a helpful assistant.",
        user_prompt="What is the capital of France?",
    )
    print(response)
