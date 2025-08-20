from openai import OpenAI

client = OpenAI(base_url="http://localhost:8555/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="Qwen/Qwen3-14b",
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    temperature=0.7,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)

print(response.choices[0].message.content)