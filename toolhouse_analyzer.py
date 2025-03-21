from groq import Groq
from toolhouse import Toolhouse
import os

client = Groq(api_key="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")
MODEL = "llama-3.3-70b-versatile"

th = Toolhouse(api_key="th-bB2yNQLo8CNwn6xXxnrF-Od_fM0Sbxc6-VicU9bc1W8")
messages = [{
    "role": "user",
    "content": "hello"
    }]

response = client.chat.completions.create(
  model=MODEL,
  messages=messages,
  tools=th.get_tools(),
)

tool_run = th.run_tools(response)
messages.extend(tool_run)

response = client.chat.completions.create(
  model=MODEL,
  messages=messages,
  tools=th.get_tools(),
)

print(response.choices[0].message.content)