#!/usr/bin/env python3
# Nium — compila o Nium (Chromium + pasta nium/) numa máquina Windows do GitHub Actions.
#
#   python ci/build.py --fresh    baixa o Chromium, aplica o Nium, configura e começa a compilar
#   python ci/build.py            continua a compilação de C:\nium\src (vinda da etapa anterior)
#
# Sai com 0 quando terminou (e deixa o zip em C:\nium\dist), 124 quando o tempo da etapa acabou
# (o progresso fica em C:\nium\src para a próxima etapa) e outro código em caso de erro.
import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r'C:\nium')
SRC = ROOT / 'src'
OUT = SRC / 'out' / 'Nium'
DIST = ROOT / 'dist'
DEPOT_TOOLS = ROOT / 'depot_tools'
REPO = Path(__file__).resolve().parents[1]
VERSION = (REPO / 'ci' / 'CHROMIUM_VERSION').read_text().strip()
TIMEOUT_EXIT = 124

GN_ARGS = '''is_debug = false
is_component_build = false
symbol_level = 0
blink_symbol_level = 0
v8_symbol_level = 0
enable_nacl = false
proprietary_codecs = true
ffmpeg_branding = "Chrome"
enable_widevine = true
use_clang_modules = false
'''


def say(msg):
  print(f'[nium] {msg}', flush=True)


def env():
  e = os.environ.copy()
  e['PATH'] = str(DEPOT_TOOLS) + os.pathsep + e['PATH']
  e['DEPOT_TOOLS_WIN_TOOLCHAIN'] = '0'  # usa o Visual Studio instalado na máquina
  return e


def run(cmd, cwd=ROOT):
  say('> ' + cmd)
  subprocess.run(cmd, cwd=cwd, env=env(), shell=True, check=True)


def setup_depot_tools():
  if not (DEPOT_TOOLS / 'gclient.bat').exists():
    ROOT.mkdir(parents=True, exist_ok=True)
    run('git clone --depth 1 https://chromium.googlesource.com/chromium/tools/depot_tools.git '
        f'"{DEPOT_TOOLS}"')
  run('gclient --version')  # prepara as ferramentas do depot_tools (python, git, cipd)


def checkout():
  ROOT.mkdir(parents=True, exist_ok=True)
  (ROOT / '.gclient').write_text(
      'solutions = [{"name": "src", "url": "https://chromium.googlesource.com/chromium/src.git",'
      ' "managed": False, "custom_deps": {}, "custom_vars": {"checkout_pgo_profiles": False}}]\n')
  if not (SRC / 'BUILD.gn').exists():
    run(f'git -c core.longpaths=true clone --depth 1 --branch {VERSION} '
        f'https://chromium.googlesource.com/chromium/src.git src')
  # O servidor do Chromium às vezes responde erro 500 no meio do download: tenta de novo.
  for attempt in range(1, 5):
    try:
      run('gclient sync -D --no-history --shallow -j 8')
      return
    except subprocess.CalledProcessError:
      if attempt == 4:
        raise
      say(f'gclient sync falhou (tentativa {attempt}); tentando de novo em 1 minuto')
      time.sleep(60)


def apply_nium():
  target = SRC / 'nium'
  if target.exists():
    shutil.rmtree(target)
  shutil.copytree(REPO / 'nium', target)
  run(f'"{sys.executable}" nium\\scripts\\apply.py', cwd=SRC)


def configure():
  OUT.mkdir(parents=True, exist_ok=True)
  (OUT / 'args.gn').write_text(GN_ARGS)
  run('gn gen out\\Nium', cwd=SRC)


def build(deadline):
  remaining = deadline - time.time()
  if remaining < 600:
    say('sem tempo para compilar nesta etapa')
    return TIMEOUT_EXIT
  say(f'compilando por até {remaining / 3600:.1f} h')
  # Ninja direto (como o ungoogled-chromium): ele decide o que recompilar pela data dos arquivos,
  # que o zip entre as etapas preserva. O siso (padrão do autoninja) recompilava tudo a cada etapa,
  # porque a máquina nova do GitHub muda o ambiente do Visual Studio que ele leva em conta.
  ninja = SRC / 'third_party' / 'ninja' / 'ninja.exe'
  command = f'"{ninja}" -C out\\Nium chrome -j 3' if ninja.exists() else 'autoninja -C out\\Nium chrome -j 3'
  say('> ' + command)
  proc = subprocess.Popen(command, cwd=SRC, env=env(), shell=True,
                          creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
  try:
    return proc.wait(timeout=remaining)
  except subprocess.TimeoutExpired:
    say('tempo da etapa acabou: parando a compilação com segurança')
    for _ in range(3):
      ctypes.windll.kernel32.GenerateConsoleCtrlEvent(1, proc.pid)  # Ctrl+Break
      time.sleep(2)
    try:
      proc.wait(timeout=180)
    except subprocess.TimeoutExpired:
      proc.kill()
    return TIMEOUT_EXIT


KEEP_EXT = {'.exe', '.dll', '.pak', '.bin', '.dat', '.manifest', '.json'}
KEEP_DIRS = ['locales', 'MEIPreload', 'PrivacySandboxAttestationsPreloaded']
SKIP_EXE = {'gn.exe', 'siso.exe'}


def package():
  nium_version = (SRC / 'nium' / 'browser' / 'ui' / 'webui' / 'nium_handler.cc').read_text(
      encoding='utf-8').split('kNiumVersion[] = "', 1)[1].split('"', 1)[0]
  name = f'Nium-{nium_version}-chromium-{VERSION}-win64'
  stage = DIST / name
  if DIST.exists():
    shutil.rmtree(DIST)
  stage.mkdir(parents=True)
  for item in OUT.iterdir():
    if item.is_file() and item.suffix.lower() in KEEP_EXT and item.name not in SKIP_EXE \
        and not item.name.endswith('.ninja_deps'):
      shutil.copy2(item, stage / item.name)
  for folder in KEEP_DIRS:
    if (OUT / folder).is_dir():
      shutil.copytree(OUT / folder, stage / folder)
  shutil.copytree(SRC / 'nium' / 'ui', stage / 'nium_ui')
  archive = shutil.make_archive(str(DIST / name), 'zip', DIST, name)
  shutil.rmtree(stage)
  say(f'pacote pronto: {archive}')


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--fresh', action='store_true')
  parser.add_argument('--minutes', type=float, default=270,
                      help='tempo máximo desta etapa, contado do início do script')
  args = parser.parse_args()
  deadline = time.time() + args.minutes * 60
  setup_depot_tools()
  if args.fresh:
    checkout()
    apply_nium()
    configure()
  code = build(deadline)
  if code == 0:
    package()
  sys.exit(code)


if __name__ == '__main__':
  main()
