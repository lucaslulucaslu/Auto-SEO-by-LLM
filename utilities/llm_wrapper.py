from langfuse.decorators import observe, langfuse_context
from google import genai
import os
from google.genai import types
from google.genai.types import GenerateContentConfig, ThinkingConfig

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-2.5-flash"
IMAGE_MODEL = "imagen-4.0-generate-001"
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


def llm_wrapper_url_summary(url):
    tools = [
        {"url_context": {}},
    ]

    summary_prompt = """
        Task Description: You are a professional news summarizer. Based on the content of the webpage provided by url: {url}, create a news summary of \
            approximately 500 English words.The summary must be written in English, ensuring comprehensive coverage of the information.
        Specific Requirements:
        1. News Summary: Extract the core content of the news, ensuring the information is complete and coherent. \
            The length should be around 500 English words.
        2. Title Extraction: If the webpage already contains a title, extract it. If there is no title, summarize an appropriate title based on the content. \
            The title must be in English.
        3. Date Information: If the webpage includes a publication date, make sure to include this date in the news summary, \
            using a format that includes the year.
        4. Content Related to U.S. Universities: If the webpage mentions U.S. universities (such as Harvard University, Yale University, etc.), \
        ensure that any related information (e.g., connection to the event or the author) is included in the summary.
        """
    response = client.models.generate_content(
        model=MODEL,
        contents=summary_prompt.format(url=url),
        config=GenerateContentConfig(tools=tools),
    )
    if 'URL_RETRIEVAL_STATUS_ERROR' in [metadata.url_retrieval_status for metadata in response.candidates[0].url_context_metadata.url_metadata]:
        return None
    return "\n".join([each.text for each in response.candidates[0].content.parts])


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
