import tiktoken
from langsmith import traceable
from openai import OpenAI

MODEL = ["gpt-4o-mini", "gpt-4o"]
TEMPERATURE = 0.2
TIMEOUT = 40
client = OpenAI()


def tokens_count(text: str, model=0):
    encoding = tiktoken.encoding_for_model(MODEL[model])
    token_length = len(encoding.encode(text))
    return token_length


def llm_wrapper(
    sys_prompt,
    user_prompt,
    response_format=None,
    timeout=TIMEOUT,
    model=0,
    temperature=TEMPERATURE,
):
    if response_format:
        response = llm_wrapper_raw(
            sys_prompt,
            user_prompt,
            response_format=response_format,
            timeout=timeout,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.parsed
    else:
        response = llm_wrapper_raw(
            sys_prompt,
            user_prompt,
            timeout=timeout,
            model=model,
            temperature=temperature,
        )
        return response.choices[0].message.content


@traceable(
    run_type="llm", metadata={"ls_model_name": "gpt-4o-mini", "ls_provider": "openai"}
)
def llm_wrapper_raw(
    sys_prompt,
    user_prompt,
    response_format=None,
    timeout=TIMEOUT,
    model=0,
    temperature=TEMPERATURE,
):
    if response_format:
        return client.beta.chat.completions.parse(
            model=MODEL[model],
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
            temperature=temperature,
            timeout=timeout,
        )
    else:
        return client.chat.completions.create(
            model=MODEL[model],
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            timeout=timeout,
        )


@traceable
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
