#!/usr/bin/env python3
# Nium — aplica tudo do Nium a uma árvore do Chromium (marca + integrações).
#
# Uso (no cmd, dentro de E:\src\chromium\src):
#     python3 nium\scripts\apply.py            aplica (pode rodar várias vezes)
#     python3 nium\scripts\apply.py --revert   desfaz tudo (antes de atualizar o Chromium)
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import apply_branding as branding  # noqa: E402

path, read, write, say = branding.path, branding.read, branding.write, branding.say


def insert_after(rel, anchor, line, label, first_only=True):
  """Inserts `line` right after the (first) line equal to `anchor`. Idempotent."""
  p = path(*rel.split('/'))
  text = read(p)
  if line.strip() in text:
    return
  newline = '\r\n' if '\r\n' in text else '\n'
  lines = text.split(newline)
  for i, current in enumerate(lines):
    if current == anchor:
      lines.insert(i + 1, line)
      write(p, newline.join(lines))
      say(label)
      return
  sys.exit(f'[nium] ERRO: não achei o ponto de encaixe em {rel}:\n  {anchor}\n'
           'O Chromium mudou este arquivo; me mande este erro.')


def patch(rel, old, new, label):
  """Replaces the one occurrence of `old` by `new` (written with \n). Idempotent."""
  p = path(*rel.split('/'))
  text = read(p)
  newline = '\r\n' if '\r\n' in text else '\n'
  old, new = old.replace('\n', newline), new.replace('\n', newline)
  if new in text:
    return
  count = text.count(old)
  if count != 1:
    sys.exit(f'[nium] ERRO: em {rel} esperava 1 ponto de encaixe, achei {count}:\n{old}\n'
             'O Chromium mudou este arquivo; me mande este erro.')
  write(p, text.replace(old, new))
  say(label)


# Fase 2 — chrome://nium (interface do Nium + ponte com o C++)
def integrate_webui():
  insert_after('chrome/browser/ui/webui/BUILD.gn',
               '    "//chrome/browser/ui/webui/version",',
               '    "//nium/browser/ui/webui:nium_ui",  # Nium',
               'chrome://nium incluído na compilação')
  insert_after('chrome/browser/ui/webui/chrome_web_ui_configs.cc',
               '#include "chrome/browser/ui/webui/version/version_ui.h"',
               '#include "nium/browser/ui/webui/nium_ui.h"  // Nium',
               'chrome://nium: cabeçalho incluído')
  insert_after('chrome/browser/ui/webui/chrome_web_ui_configs.cc',
               '  map.AddWebUIConfig(std::make_unique<AccessibilityUIConfig>());',
               '  map.AddWebUIConfig(std::make_unique<nium::NiumUIConfig>());  // Nium',
               'chrome://nium registrado')


# Fase 3 — a janela do Nium: barra lateral (chrome://nium/sidebar.html) com as abas de verdade
# no lugar da faixa de abas do Chromium. Para comparar com o Chromium: --nium-classic-tabs.
FRAME = 'chrome/browser/ui/views/frame/'


def integrate_window():
  patch(FRAME + 'BUILD.gn',
        'source_set("browser_view") {\n  sources = [ "browser_view.cc" ]\n',
        'source_set("browser_view") {\n  sources = [\n    "browser_view.cc",\n'
        '    "//nium/browser/ui/views/nium_sidebar_view.cc",  # Nium\n'
        '    "//nium/browser/ui/views/nium_sidebar_view.h",  # Nium\n  ]\n',
        'barra lateral incluída na compilação')
  patch(FRAME + 'BUILD.gn',
        '  sources = [\n    "browser_view.cc",\n'
        '    "//nium/browser/ui/views/nium_sidebar_view.cc",  # Nium\n'
        '    "//nium/browser/ui/views/nium_sidebar_view.h",  # Nium\n  ]\n'
        '  public_deps = [ ":browser_view_header" ]\n  deps = [\n',
        '  sources = [\n    "browser_view.cc",\n'
        '    "//nium/browser/ui/views/nium_sidebar_view.cc",  # Nium\n'
        '    "//nium/browser/ui/views/nium_sidebar_view.h",  # Nium\n  ]\n'
        '  public_deps = [ ":browser_view_header" ]\n  deps = [\n'
        '    "//nium/browser/ui/webui:nium_ui",  # Nium\n',
        'barra lateral: dependência da ponte')
  # Lista de views da janela: um lugar para a barra lateral.
  patch(FRAME + 'layout/browser_view_layout.h',
        '  raw_ptr<views::View> top_container_separator = nullptr;\n',
        '  raw_ptr<views::View> top_container_separator = nullptr;\n\n'
        '  // Nium: the Nium sidebar (left edge, full height). Null when not used.\n'
        '  raw_ptr<views::View> nium_sidebar = nullptr;\n',
        'layout: campo da barra lateral')
  # BrowserView: cria a barra lateral e a entrega ao layout.
  patch(FRAME + 'browser_view.cc',
        '#include "chrome/browser/ui/views/frame/browser_view.h"\n',
        '#include "chrome/browser/ui/views/frame/browser_view.h"\n'
        '#include "nium/browser/ui/views/nium_sidebar_view.h"  // Nium\n',
        'janela: cabeçalho da barra lateral')
  patch(FRAME + 'browser_view.cc',
        '  BrowserViewLayoutViews layout_views;\n',
        '  BrowserViewLayoutViews layout_views;\n\n'
        '  // Nium: the sidebar with the tabs replaces the tab strip.\n'
        '  views::View* nium_sidebar = nullptr;\n'
        '  if (nium::NiumSidebarEnabled(browser_)) {\n'
        '    nium_sidebar =\n'
        '        AddChildView(std::make_unique<nium::NiumSidebarView>(browser_));\n'
        '  }\n',
        'janela: barra lateral criada')
  patch(FRAME + 'browser_view.cc',
        '  layout_views.top_container_separator = top_container_separator_;\n',
        '  layout_views.top_container_separator = top_container_separator_;\n'
        '  layout_views.nium_sidebar = nium_sidebar;  // Nium\n',
        'janela: barra lateral no layout')
  # A moldura trata a janela como no modo de abas verticais (barra de ferramentas na linha de cima).
  patch(FRAME + 'browser_view.cc',
        '      ShouldDrawTabStrip() && !ShouldDrawVerticalTabStrip() &&\n',
        '      ShouldDrawTabStrip() && !ShouldDrawVerticalTabStrip() &&\n'
        '              !nium::NiumSidebarEnabled(browser_) &&  // Nium\n',
        'moldura: sem altura da faixa de abas')
  patch(FRAME + 'browser_view.cc',
        '  if (toolbar_ && ShouldDrawVerticalTabStrip()) {\n',
        '  if (toolbar_ && (ShouldDrawVerticalTabStrip() ||\n'
        '                   nium::NiumSidebarEnabled(browser_))) {  // Nium\n',
        'moldura: barra de ferramentas na linha de cima')
  # Arrastar a janela: topo da barra lateral e espaço vazio da barra de ferramentas.
  patch(FRAME + 'browser_view.cc',
        '  if (vertical_tab_strip_region_view_ &&\n'
        '      vertical_tab_strip_region_view_->GetVisible()) {\n'
        '    // See if the mouse pointer is within the bounds of the\n'
        '    // VerticalTabStripRegionView.\n',
        '  // Nium: the top strip of the sidebar and the empty parts of the toolbar\n'
        '  // move the window (HTNOWHERE lets the frame test the caption buttons first).\n'
        '  if (auto* nium_sidebar = nium::NiumSidebarView::FromBrowserView(this);\n'
        '      nium_sidebar && nium_sidebar->GetVisible()) {\n'
        '    gfx::Point test_point(point);\n'
        '    if (ConvertedHitTest(parent(), nium_sidebar, &test_point)) {\n'
        '      return nium_sidebar->IsPositionInWindowCaption(test_point) ? HTNOWHERE\n'
        '                                                               : HTCLIENT;\n'
        '    }\n'
        '    gfx::Point test_point2(point);\n'
        '    if (ConvertedHitTest(parent(), top_container_, &test_point2) &&\n'
        '        top_container_->IsPositionInWindowCaption(test_point2)) {\n'
        '      return HTNOWHERE;\n'
        '    }\n'
        '  }\n\n'
        '  if (vertical_tab_strip_region_view_ &&\n'
        '      vertical_tab_strip_region_view_->GetVisible()) {\n'
        '    // See if the mouse pointer is within the bounds of the\n'
        '    // VerticalTabStripRegionView.\n',
        'janela: arrastar pela barra lateral')
  # Layout: sem faixa de abas; a barra lateral ocupa a esquerda.
  patch(FRAME + 'layout/browser_view_layout_delegate_impl.cc',
        '#include "chrome/browser/ui/views/frame/layout/browser_view_layout_delegate_impl.h"\n',
        '#include "chrome/browser/ui/views/frame/layout/browser_view_layout_delegate_impl.h"\n'
        '#include "nium/browser/ui/views/nium_sidebar_mode.h"  // Nium\n',
        'layout: cabeçalho do modo barra lateral')
  patch(FRAME + 'layout/browser_view_layout_delegate_impl.cc',
        '  if (!browser_view_->ShouldDrawTabStrip()) {\n    return TabStripType::kNone;\n  }\n',
        '  if (!browser_view_->ShouldDrawTabStrip() ||\n'
        '      nium::NiumSidebarEnabled(browser_view_->browser())) {  // Nium\n'
        '    return TabStripType::kNone;\n  }\n',
        'layout: faixa de abas escondida')
  patch(FRAME + 'layout/browser_view_tabbed_layout_impl.cc',
        '  layout_data_->tab_strip_type = delegate().GetTabStripType();\n',
        '  layout_data_->tab_strip_type = delegate().GetTabStripType();\n'
        '  // Nium: everything else lays out to the right of the Nium sidebar, and the\n'
        '  // space next to the caption buttons stays free to drag the window.\n'
        '  if (views().nium_sidebar && !is_fullscreen(layout_data_->window_state)) {\n'
        '    layout_data_->revised_params.InsetHorizontal(\n'
        '        views().nium_sidebar->GetPreferredSize().width(), /*leading=*/true);\n'
        '    IncreasePaddingToMinimum(layout_data_->revised_params,\n'
        '                             kVerticalTabsGrabHandleSize);\n'
        '  }\n',
        'layout: espaço da barra lateral')
  patch(FRAME + 'layout/browser_view_tabbed_layout_impl.cc',
        '  if (views().window_scrim) {\n'
        '    layout.AddChild(views().window_scrim, browser_params.visual_client_area);\n  }\n',
        '  if (views().window_scrim) {\n'
        '    layout.AddChild(views().window_scrim, browser_params.visual_client_area);\n  }\n\n'
        '  // Nium: the sidebar takes the left edge, full height (hidden in fullscreen).\n'
        '  if (views().nium_sidebar) {\n'
        '    const bool show_nium_sidebar = !is_fullscreen(layout_data_->window_state);\n'
        '    gfx::Rect nium_sidebar_bounds;\n'
        '    if (show_nium_sidebar) {\n'
        '      const gfx::Rect& area = browser_params.visual_client_area;\n'
        '      nium_sidebar_bounds = gfx::Rect(\n'
        '          area.x(), area.y(),\n'
        '          std::min(area.width(),\n'
        '                   views().nium_sidebar->GetPreferredSize().width()),\n'
        '          area.height());\n'
        '    }\n'
        '    layout.AddChild(views().nium_sidebar, nium_sidebar_bounds,\n'
        '                    show_nium_sidebar);\n'
        '  }\n',
        'layout: barra lateral posicionada')


TOUCHED = branding.TOUCHED + [
    'chrome/browser/ui/webui/BUILD.gn',
    'chrome/browser/ui/webui/chrome_web_ui_configs.cc',
    FRAME + 'BUILD.gn',
    FRAME + 'browser_view.cc',
    FRAME + 'layout/browser_view_layout.h',
    FRAME + 'layout/browser_view_layout_delegate_impl.cc',
    FRAME + 'layout/browser_view_tabbed_layout_impl.cc',
]


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--revert', action='store_true')
  args = parser.parse_args()
  if not os.path.exists(path('chrome', 'app', 'chromium_strings.grd')):
    sys.exit('[nium] Rode este script de dentro de E:\\src\\chromium\\src')
  if args.revert:
    subprocess.check_call(['git', 'checkout', '--'] + TOUCHED, cwd=branding.SRC)
    return say('tudo desfeito (arquivos do Chromium restaurados)')
  branding.copy_icons()
  branding.branding_file()
  branding.replace_all(path('chrome', 'install_static', 'chromium_install_modes.h'),
                       branding.INSTALL_MODES, 'perfil e registros do Windows como Nium')
  branding.fix_infobar()
  for grd in branding.GRDS:
    if os.path.exists(path(*grd.split('/'))):
      branding.rebrand_strings(grd)
  integrate_webui()
  integrate_window()
  say('pronto. Agora compile: autoninja -C out\\Nium chrome')


if __name__ == '__main__':
  main()
