import os
import glob
import re

filepaths = glob.glob('mkdocs-devops-platform/docs/cheatsheets/*.md')

mojibake_map = {
    'â€”': '—',
    'â€“': '–',
    'â€˜': "'",
    'â€™': "'",
    'â€œ': '"',
    'â€ ': '"',
    'â€': '"',
    'â€¦': '...',
    'Ã©': 'é',
    'â†’': '→',
    'Ã—': '×',
    'Ã·': '÷',
    'Â°': '°',
    'Â±': '±',
    'Â': ' ',
    '\xef\xbb\xbf': '' # BOM
}

for filepath in filepaths:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Clean Mojibake
    for bad, good in mojibake_map.items():
        content = content.replace(bad, good)
        
    # 2. Fix Double Headers (e.g. '# Devops Cloud Engineering Handbook\n\n# DevOps ...')
    lines = content.split('\n')
    if len(lines) >= 3 and lines[0].startswith('# ') and lines[2].startswith('# '):
        content = '\n'.join(lines[2:])
        
    # 3. Clean up the BOM if it got rendered as a string anywhere
    content = content.replace('\ufeff', '')
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Deep cleaned {len(filepaths)} files.")
