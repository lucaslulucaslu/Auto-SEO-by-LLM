import tiktoken
from openai import OpenAI

MODEL = ["gpt-4o-mini", "gpt-4o"]
TEMPERATURE = 0
TIMEOUT = 40
client = OpenAI()


def tokens_count(text: str, model=0):
    encoding = tiktoken.encoding_for_model(MODEL[model])
    token_length = len(encoding.encode(text))
    return token_length


def llm_wrapper(
    sys_prompt, user_prompt, response_format=None, timeout=TIMEOUT, model=0
):
    if response_format:
        response = client.beta.chat.completions.parse(
            model=MODEL[model],
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
            temperature=TEMPERATURE,
            timeout=timeout,
        )
        return response.choices[0].message.parsed
    else:
        response = client.chat.completions.create(
            model=MODEL[model],
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            timeout=timeout,
        )
        return response.choices[0].message.content


def llm_wrapper_raw(
    sys_prompt, user_prompt, response_format=None, timeout=TIMEOUT, model=0
):
    if response_format:
        response = client.beta.chat.completions.parse(
            model=MODEL[model],
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
            temperature=TEMPERATURE,
            timeout=timeout,
        )
        return response
    else:
        response = client.chat.completions.create(
            model=MODEL[model],
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            timeout=timeout,
        )
        return response


def llm_image_wrapper(image_query):
    return (
        client.images.generate(
            model="dall-e-3",
            size="1792x1024",
            quality="standard",
            prompt=image_query,
            n=1,
        )
        .data[0]
        .url
    )
