import re

path = 'mkdocs-devops-platform/docs/architecture-diagrams.md'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\\n', '<br>')

def quote_participant(match):
    alias = match.group(1)
    desc = match.group(2).strip()
    if not desc.startswith('"'):
        return f'participant {alias} as "{desc}"'
    return match.group(0)

content = re.sub(r'participant\s+([A-Za-z0-9_]+)\s+as\s+([^\r\n]+)', quote_participant, content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
