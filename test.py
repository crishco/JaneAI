import ollama

response = ollama.chat(
    model="qwen3:8b",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response["message"]["content"])