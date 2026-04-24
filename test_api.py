import os
from dotenv import load_dotenv
load_dotenv()
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

for model in ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"]:
    try:
        r = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "say hi"}],
        )
        print(f"OK  {model}: {r.content[0].text}")
    except Exception as e:
        print(f"FAIL {model}: {e}")