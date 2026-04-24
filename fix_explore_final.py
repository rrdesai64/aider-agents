content = open("agents/explore.py", encoding="utf-8").read()

# Store clean JSON in explore_output, not the fenced version
old = '''            context.explore_output = text
            context.save()'''

new = '''            context.explore_output = text_clean
            context.save()'''

assert old in content, "Pattern not found"
open("agents/explore.py", "w", encoding="utf-8").write(content.replace(old, new))
print("Done.")