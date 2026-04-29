import sys
with open('app/web/templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = '<div id="reportTabPanel" class="hidden space-y-6">'
end_marker = '            </div>\n        </div>\n    </main>'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + "{% include 'tabs/reportTabPanel.html' %}\n" + content[end_idx:]
    with open('app/web/templates/index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Replaced successfully')
else:
    print('Failed to find markers')
