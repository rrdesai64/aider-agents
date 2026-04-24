path = "agents/explore.py"
content = open(path, encoding="utf-8").read()

content = content.replace(
    "if p.is_file() and p.suffix not in skip_ext:",
    'if p.is_file() and p.suffix not in skip_ext and p.name not in {".env", ".env.example", "secrets.yaml", "secrets.yml"}:'
)

open(path, "w", encoding="utf-8").write(content)
print("Fixed.")