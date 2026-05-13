import traceback
import pathlib
import os

try:
    base_dir = pathlib.Path('cti_dashboard_pro/app/web/templates/tabs')
    thermal_file = base_dir / 'thermalTabPanel.html'
    thermal_dir = base_dir / 'thermal'
    os.makedirs(thermal_dir, exist_ok=True)

    content = thermal_file.read_text(encoding='utf-8')
    lines = content.splitlines()

    tooltips_start = [i for i, l in enumerate(lines) if 'TOOLTIP CONTENT TEMPLATES' in l][0] - 1
    project_scope_start = [i for i, l in enumerate(lines) if 'PROJECT SCOPE HEADER' in l][0] - 1
    main_layout_start = [i for i, l in enumerate(lines) if 'MAIN LAYOUT' in l][0] - 1
    config_panel_start = [i for i, l in enumerate(lines) if 'LEFT: Collapsible Configuration Panel' in l][0] - 1
    right_charts_start = [i for i, l in enumerate(lines) if 'RIGHT: KaV/L Stats' in l][0] - 1
    margin_modal_start = [i for i, l in enumerate(lines) if 'MARGIN IMPACT ANALYSIS MODAL' in l][0] - 1

    (thermal_dir / '_tooltips.html').write_text('\n'.join(lines[tooltips_start:project_scope_start]), encoding='utf-8')
    (thermal_dir / '_project_scope.html').write_text('\n'.join(lines[project_scope_start:main_layout_start]), encoding='utf-8')
    (thermal_dir / '_config_panel.html').write_text('\n'.join(lines[config_panel_start:right_charts_start]), encoding='utf-8')
    (thermal_dir / '_charts_display.html').write_text('\n'.join(lines[right_charts_start:margin_modal_start-3]), encoding='utf-8')
    (thermal_dir / '_margin_modal.html').write_text('\n'.join(lines[margin_modal_start:]), encoding='utf-8')

    new_main = []
    new_main.append('<div id="thermalTabPanel">')
    new_main.append('    {% include \'tabs/thermal/_tooltips.html\' %}')
    new_main.append('    {% include \'tabs/thermal/_project_scope.html\' %}')
    new_main.append('')
    new_main.append('    <!-- ═══════════════════════════════════════════════════════════════════')
    new_main.append('         MAIN LAYOUT')
    new_main.append('         xl+: side-by-side with collapsible left panel')
    new_main.append('         < xl: single column stacked')
    new_main.append('         ═══════════════════════════════════════════════════════════════════ -->')
    new_main.append('    <div class="flex flex-col xl:flex-row xl:items-start gap-6">')
    new_main.append('        {% include \'tabs/thermal/_config_panel.html\' %}')
    new_main.append('        {% include \'tabs/thermal/_charts_display.html\' %}')
    new_main.append('    </div>')
    new_main.append('</div>')
    new_main.append('')
    new_main.append('{% include \'tabs/thermal/_margin_modal.html\' %}')

    thermal_file.write_text('\n'.join(new_main), encoding='utf-8')
    print('Successfully refactored thermalTabPanel.html into components!')
except Exception as e:
    traceback.print_exc()
