import glob
import re

filepaths = glob.glob('mkdocs-devops-platform/docs/cheatsheets/*.md')

# A regex to match the blockquote section containing Author, Last Updated, Pages
pattern = re.compile(
    r'^>\s*\*\*Author\*\*[:].*?\n'
    r'(?:>\s*\*\*Last Updated\*\*[:].*?\n)?'
    r'(?:>\s*\*\*Pages\*\*[:].*?\n)?',
    re.IGNORECASE | re.MULTILINE
)

removed_count = 0

for filepath in filepaths:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content, count = pattern.subn('', content)
    
    if count > 0:
        removed_count += 1
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

print(f"Removed author text from {removed_count} files.")
