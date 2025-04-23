from langfuse.decorators import observe, langfuse_context
from google import genai
import os
from google.genai import types
from google.genai.types import GenerateContentConfig, ThinkingConfig

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-2.5-flash-preview-04-17"
IMAGE_MODEL = "imagen-3.0-generate-002"
RETRY_LIMIT = 5  # Retry limit for image generation


def tokens_count(text: str, model=MODEL):
    token_length = client.models.count_tokens(model=model, contents=text)
    return token_length


@observe(as_type="generation")
def llm_wrapper_raw(sys_prompt, user_prompt, response_format=None, model=MODEL):
    retry_count = 0
    error_messages = []
    while retry_count < RETRY_LIMIT:
        retry_count += 1
        try:
            if response_format:
                response = client.models.generate_content(
                    model=model,
                    contents=sys_prompt + user_prompt,
                    config=GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_format,
                        thinking_config=ThinkingConfig(thinking_budget=0),
                    ),
                )
                if hasattr(response, "error"):
                    raise Exception(response["error"])
                langfuse_output = response.parsed
            else:
                response = client.models.generate_content(
                    model=model,
                    contents=sys_prompt + user_prompt,
                    config=GenerateContentConfig(
                        thinking_config=ThinkingConfig(thinking_budget=0)
                    ),
                )
                if hasattr(response, "error"):
                    raise Exception(response["error"])
                langfuse_output = response.text
            langfuse_context.update_current_observation(
                model=model,
                output=langfuse_output,
                usage_details={
                    "input": response.usage_metadata.prompt_token_count,
                    "output": response.usage_metadata.candidates_token_count,
                    "total": response.usage_metadata.total_token_count,
                },
            )
            return response
        except Exception as e:
            error_messages.append(str(e))
            langfuse_context.update_current_observation(
                model=model,
                output={"errors": error_messages},
                usage_details={
                    "input": 0,
                    "output": 0,
                    "total": 0,
                },
                tags=["retried"],
            )


@observe(as_type="generation")
def llm_image_wrapper(image_query):
    retry_count = 0
    image_queries = []
    error_messages = []
    while retry_count < RETRY_LIMIT:
        retry_count += 1
        image_queries.append(image_query)
        try:
            response = client.models.generate_images(
                model=IMAGE_MODEL,
                prompt=image_query,
                config=types.GenerateImagesConfig(
                    number_of_images=1,  # Number of images to generate
                    aspect_ratio="16:9",  # Aspect ratio of the image
                ),
            )
            if response.generated_images:
                langfuse_context.update_current_observation(
                    model=IMAGE_MODEL,
                    input=image_queries,
                    output={
                        "image generated": True,
                        "tried": retry_count,
                        "errors": error_messages,
                    },
                    cost_details={
                        "input": 0,
                        "output": 0.04,
                    },
                )
                return response.generated_images[0]
            else:
                raise Exception("Image generation response is empty")
        except Exception as e:
            error_messages.append(str(e))
            langfuse_context.update_current_observation(
                model=IMAGE_MODEL,
                input=image_queries,
                output={
                    "image generated": False,
                    "tried": retry_count,
                    "errors": error_messages,
                },
                cost_details={
                    "input": 0,
                    "output": 0,
                },
                tags=["image_generation_retried"],
            )
            image_query = llm_wrapper_raw(
                sys_prompt=f"Generate one single new image prompt that will not violate google's policy based on original prompt, \
                you need to void child, violance, nudity, racism, sexual, toxic, derogatory, etc.\
                    it's Ok to change the meaning of the prompt a little bit to make it safer: \n\n{image_query}\n\n\
                    Only output the new prompt without any additional text.",
                user_prompt="",
            ).text


if __name__ == "__main__":
    from io import BytesIO
    from PIL import Image

    image_query = "A beautiful sunset over the ocean with a sailboat in the distance."
    generated_image = llm_image_wrapper(image_query)
    with Image.open(BytesIO(generated_image.image.image_bytes)) as image:
        image.show()
    # response = llm_wrapper_raw(
    #     sys_prompt="You are a helpful assistant.",
    #     user_prompt="What is the capital of France?",
    # )
    # print(response)
