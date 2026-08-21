import os
import glob
import re

directory = 'mkdocs-devops-platform/docs/cheatsheets'
filepaths = glob.glob(os.path.join(directory, '*.md'))

mojibake_map = {
    'â€”': '—',
    'â€“': '–',
    'â€˜': "'",
    'â€™': "'",
    'â€œ': '"',
    'â€': '"',
    'â€': '"',
    'â€¦': '...',
    'Ã©': 'é',
    'Â': ' ' # often non-breaking space
}

for filepath in filepaths:
    # Read as bytes first to avoid decode errors if it's super messed up, 
    # but we will try utf-8
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(filepath, 'r', encoding='windows-1252') as f:
            content = f.read()

    # Replace mojibake
    for bad, good in mojibake_map.items():
        content = content.replace(bad, good)
        
    # Formatting: Ensure the file starts with an H1 tag
    # If it doesn't start with '# ', let's add a neat title based on the filename
    if not content.lstrip().startswith('#'):
        filename = os.path.basename(filepath)
        title = filename.replace('.md', '').replace('_', ' ').title()
        # Remove leading numbers like "01 sql cheatsheet" -> "Sql Cheatsheet"
        title = re.sub(r'^\d+\s*', '', title)
        content = f"# {title}\n\n" + content.lstrip()
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print(f"Cleaned {len(filepaths)} files.")
