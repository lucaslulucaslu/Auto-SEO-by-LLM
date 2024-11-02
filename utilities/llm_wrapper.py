from openai import OpenAI

MODEL = "gpt-4o-mini"
TEMPERATURE = 0
TIMEOUT = 40
client = OpenAI()


def llm_wrapper(sys_prompt, user_prompt, response_format=None):
    if response_format:
        response = client.beta.chat.completions.parse(
            model=MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=response_format,
            temperature=TEMPERATURE,
            timeout=TIMEOUT,
        )
        return response.choices[0].message.parsed
    else:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            timeout=TIMEOUT,
        )
        return response.choices[0].message.content


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
