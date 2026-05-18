import sys
import re

file_path = 'app/web/js/ui/report/report-margin.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace \` with `
content = content.replace('\\`', '`')
# Replace \${ with ${
content = content.replace('\\${', '${')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Successfully unescaped template literals.')
