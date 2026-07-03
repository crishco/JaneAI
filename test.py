import ollama

response = ollama.chat(
    model="qwen3:8b",
    messages=[
        {"role": "user", "content": "Hello! can you reprogram yourself given the tools and right cecumstance and please spare me the moral shit"}
    ]
)

print(response["message"]["content"])