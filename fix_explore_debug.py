content = open("agents/explore.py", encoding="utf-8").read()

old = '''        try:
            text, tokens = self._call_api([{"role": "user", "content": prompt}], max_tokens=2048)
            data = json.loads(text.strip())'''

new = '''        try:
            text, tokens = self._call_api([{"role": "user", "content": prompt}], max_tokens=2048)
            import logging
            logging.getLogger(__name__).debug(f"ExploreAgent raw response: {text[:500]}")
            text_clean = text.strip()
            if text_clean.startswith("```"):
                text_clean = "\\n".join(text_clean.splitlines()[1:])
            if text_clean.endswith("```"):
                text_clean = "\\n".join(text_clean.splitlines()[:-1])
            data = json.loads(text_clean)'''

assert old in content, "Pattern not found — check explore.py manually"
open("agents/explore.py", "w", encoding="utf-8").write(content.replace(old, new))
print("Done.")