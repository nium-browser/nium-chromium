#!/usr/bin/env python3
# Nium — Fase 1: aplica a marca Nium a uma árvore do Chromium.
#
# Uso (no cmd, dentro de E:\src\chromium\src):
#     python3 nium\scripts\apply_branding.py
# Pode rodar quantas vezes quiser: o que já foi aplicado é pulado.
# Para desfazer tudo (por exemplo, antes de atualizar o Chromium):
#     python3 nium\scripts\apply_branding.py --revert
#
# O que faz:
#   1. Copia os ícones do Nium (nium/branding) por cima dos do Chromium.
#   2. Troca nome, empresa e ID do app no arquivo BRANDING.
#   3. Usa "Nium" no nome da pasta do perfil (%LOCALAPPDATA%\Nium) e nos registros do Windows.
#   4. Troca "Chromium" por "Nium" nos textos da interface, mantendo as traduções
#      (o Chromium liga cada tradução ao texto por um código; ele é recalculado com o grit).
#   5. Remove o aviso "Google API keys are missing".
import argparse
import filecmp
import glob
import os
import re
import shutil
import subprocess
import sys

NAME = 'Nium'
SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
KIT = os.path.join(SRC, 'nium')


def path(*parts):
  return os.path.join(SRC, *parts)


def read(p):
  with open(p, encoding='utf-8', newline='') as f:
    return f.read()


def write(p, text):
  # Só grava se mudou: arquivo regravado = data nova = o autoninja recompila o que depende dele.
  try:
    if read(p) == text:
      return
  except (OSError, UnicodeDecodeError):
    pass
  with open(p, 'w', encoding='utf-8', newline='') as f:
    f.write(text)


def say(msg):
  print('[nium] ' + msg)


# ---------------------------------------------------------------------------
# 1. Ícones
def copy_icons():
  root = os.path.join(KIT, 'branding')
  n = 0
  for folder, _, files in os.walk(root):
    for name in files:
      source = os.path.join(folder, name)
      target = path(os.path.relpath(source, root))
      os.makedirs(os.path.dirname(target), exist_ok=True)
      if os.path.exists(target) and filecmp.cmp(source, target, shallow=False):
        continue  # igual: não mexe (evita recompilar)
      shutil.copyfile(source, target)
      n += 1
  say(f'ícones copiados: {n}' if n else 'ícones: já estavam certos')


# ---------------------------------------------------------------------------
# 2. BRANDING
BRANDING = {
    'COMPANY_FULLNAME': 'Nium',
    'COMPANY_SHORTNAME': 'Nium',
    'PRODUCT_FULLNAME': NAME,
    'PRODUCT_SHORTNAME': NAME,
    'PRODUCT_INSTALLER_FULLNAME': NAME + ' Installer',
    'PRODUCT_INSTALLER_SHORTNAME': NAME + ' Installer',
    'COPYRIGHT': 'Copyright @LASTCHANGE_YEAR@ Nium. Baseado no Chromium, '
                 'Copyright The Chromium Authors.',
    'MAC_BUNDLE_ID': 'app.nium.browser',
}


def branding_file():
  p = path('chrome', 'app', 'theme', 'chromium', 'BRANDING')
  lines = read(p).splitlines(keepends=True)
  out = []
  for line in lines:
    key = line.split('=', 1)[0]
    if key in BRANDING:
      line = f'{key}={BRANDING[key]}' + ('\r\n' if line.endswith('\r\n') else '\n')
    out.append(line)
  write(p, ''.join(out))
  say('BRANDING atualizado')


# ---------------------------------------------------------------------------
# 3. Pasta do perfil e registros do Windows
INSTALL_MODES = [
    ('kProductPathName[] = L"Chromium";', f'kProductPathName[] = L"{NAME}";'),
    ('.base_app_name = L"Chromium",', f'.base_app_name = L"{NAME}",'),
    ('.base_app_id = L"Chromium",', f'.base_app_id = L"{NAME}",'),
    ('.browser_prog_id_prefix = L"ChromiumHTM",', f'.browser_prog_id_prefix = L"{NAME}HTM",'),
    ('L"Chromium HTML Document"', f'L"{NAME} HTML Document"'),
    ('.direct_launch_url_scheme = "chromium",', '.direct_launch_url_scheme = "nium",'),
    ('.pdf_prog_id_prefix = L"ChromiumPDF",', f'.pdf_prog_id_prefix = L"{NAME}PDF",'),
    ('L"Chromium PDF Document"', f'L"{NAME} PDF Document"'),
]


def replace_all(p, pairs, label):
  text = read(p)
  for old, new in pairs:
    if new in text and old not in text:
      continue  # já aplicado
    count = text.count(old)
    if count != 1:
      sys.exit(f'[nium] ERRO: em {p} esperava 1 ocorrência de {old!r}, achei {count}. '
               'O Chromium mudou este arquivo; me mande este erro.')
    text = text.replace(old, new)
  write(p, text)
  say(label)


# ---------------------------------------------------------------------------
# 5. Aviso das chaves de API do Google
INFOBAR_ORIGINAL = '  if (!google_apis::HasAPIKeyConfigured()) {'
# Versão anterior do Nium ("if (false && ...)"): o compilador recusa (código inalcançável).
INFOBAR_OLD = '  if (false && !google_apis::HasAPIKeyConfigured()) {  // Nium: sem aviso de chaves do Google'
INFOBAR_NEW = ('  if (!google_apis::HasAPIKeyConfigured() &&\n'
               '      base::CommandLine::ForCurrentProcess()->HasSwitch(\n'
               '          "nium-api-keys-warning")) {  // Nium: aviso só com essa opção')


def fix_infobar():
  p = path('chrome', 'browser', 'ui', 'startup', 'infobar_utils.cc')
  text = read(p)
  newline = '\r\n' if '\r\n' in text else '\n'
  new = INFOBAR_NEW.replace('\n', newline)
  if new in text:
    return say('aviso de chaves do Google: já aplicado')
  for old in (INFOBAR_OLD, INFOBAR_ORIGINAL):
    if text.count(old) == 1:
      write(p, text.replace(old, new))
      return say('aviso de chaves do Google removido')
  sys.exit(f'[nium] ERRO: não achei o aviso de chaves em {p}. O Chromium mudou este arquivo; me mande este erro.')


# ---------------------------------------------------------------------------
# 4. Textos da interface (grd + traduções xtb)
# Keeps "The Chromium Authors", ChromiumOS and the credit link to the Chromium project.
WORD = re.compile(r'\bChromium\b(?! Authors)(?! OS)(?!OS)(?!<ph name="END_LINK_CHROMIUM")')
MESSAGE = re.compile(r'(<message\b[^>]*>)(.*?)(</message>)', re.S)
TRANSLATION = re.compile(r'<translation id="(\d+)"(.*?)>(.*?)</translation>', re.S)


def rebrand_text(text):
  return WORD.sub(NAME, text)


def grit_ids(grd):
  sys.path.insert(0, path('tools', 'grit'))
  from grit import grd_reader
  from grit.node import message

  class Defines(dict):
    def __missing__(self, key):
      return False

    def __contains__(self, key):
      return True

  res = grd_reader.Parse(grd, debug=False, defines=Defines({'_chromium': True}))
  return [(node.attrs['name'], node.clique.GetMessage().GetId())
          for node in res.Preorder()
          if isinstance(node, message.MessageNode) and node.clique]


def rebrand_strings(grd_rel):
  grd = path(*grd_rel.split('/'))
  folder = os.path.dirname(grd)
  text = read(grd)
  parts = [os.path.join(folder, p) for p in re.findall(r'<part file="([^"]+)"', text)]
  sources = [grd] + parts
  before = grit_ids(grd)
  changed = 0
  for source in sources:
    original = read(source)
    updated = MESSAGE.sub(lambda m: m.group(1) + rebrand_text(m.group(2)) + m.group(3), original)
    if updated != original:
      write(source, updated)
      changed += 1
  after = grit_ids(grd)
  if len(before) != len(after):
    sys.exit(f'[nium] ERRO: {grd_rel} mudou de estrutura ao trocar o nome.')
  mapping = {old: new for (_, old), (_, new) in zip(before, after) if old != new}
  xtbs = [os.path.join(folder, p) for p in re.findall(r'<file path="([^"]+\.xtb)"', text)]
  fixed = 0
  for xtb in xtbs:
    if not os.path.exists(xtb):
      continue
    content = read(xtb)
    present = set(re.findall(r'<translation id="(\d+)"', content))

    def swap(m):
      old, attrs, body = m.group(1), m.group(2), m.group(3)
      new = mapping.get(old)
      if not new or new in present:
        return m.group(0)
      return f'<translation id="{new}"{attrs}>{rebrand_text(body)}</translation>'

    updated = TRANSLATION.sub(swap, content)
    if updated != content:
      write(xtb, updated)
      fixed += 1
  say(f'{grd_rel}: {len(mapping)} textos com o novo nome, {fixed} arquivos de tradução ajustados')


GRDS = ['chrome/app/chromium_strings.grd', 'components/components_chromium_strings.grd']

TOUCHED = ['chrome/app/theme', 'chrome/app/chromium_strings.grd', 'chrome/app/settings_chromium_strings.grdp',
           'chrome/app/resources', 'components/components_chromium_strings.grd', 'components/strings',
           'chrome/install_static/chromium_install_modes.h', 'chrome/browser/ui/startup/infobar_utils.cc']


def revert():
  subprocess.check_call(['git', 'checkout', '--'] + TOUCHED, cwd=SRC)
  say('marca desfeita (arquivos do Chromium restaurados)')


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--revert', action='store_true')
  args = parser.parse_args()
  if not os.path.exists(path('chrome', 'app', 'chromium_strings.grd')):
    sys.exit('[nium] Rode este script de dentro de E:\\src\\chromium\\src')
  if args.revert:
    return revert()
  copy_icons()
  branding_file()
  replace_all(path('chrome', 'install_static', 'chromium_install_modes.h'), INSTALL_MODES,
              'perfil em %LOCALAPPDATA%\\Nium e registros do Windows como Nium')
  fix_infobar()
  for grd in GRDS:
    if os.path.exists(path(*grd.split('/'))):
      rebrand_strings(grd)
  say('pronto. Agora compile: autoninja -C out\\Nium chrome')


if __name__ == '__main__':
  main()
