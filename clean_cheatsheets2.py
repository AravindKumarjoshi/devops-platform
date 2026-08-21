import os
import glob
import re

filepaths = glob.glob('mkdocs-devops-platform/docs/cheatsheets/*.md')

for filepath in filepaths:
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Fix standard mojibake
    content = content.replace('â€”', '—').replace('â€“', '–')
    content = content.replace('â€˜', "'").replace('â€™', "'")
    content = content.replace('â€œ', '"').replace('â€ ', '"').replace('â€', '"')
    
    # Fix specific corrupted arrows and replacement chars
    content = re.sub(r'A\ufffd\ufffdT', '->', content)
    content = re.sub(r'A\?\?T', '->', content)
    content = content.replace('\ufffd', '')
    
    # Remove BOM if present
    if content.startswith('\ufeff'):
        content = content[1:]
    
    # Fix double titles created from previous script run
    if content.startswith('# '):
        lines = content.split('\n')
        if len(lines) > 2 and lines[0].startswith('# ') and lines[2].startswith('# '):
            content = '\n'.join(lines[2:])
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Cleaned {len(filepaths)} files.")
