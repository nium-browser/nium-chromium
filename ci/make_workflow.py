#!/usr/bin/env python3
# Gera .github/workflows/build.yml (N etapas encadeadas). Rode de novo se mudar STAGES.
from pathlib import Path

STAGES = 12
out = ['''# GERADO por ci/make_workflow.py — edite lá.
# Compila o Nium para Windows em etapas de até 6 h (limite do GitHub). Cada etapa continua de onde
# a anterior parou; a que terminar envia o zip, e "publish" cria uma Release para baixar.
name: build-windows
on:
  workflow_dispatch:
  push:
    tags:
      - 'v*'

permissions:
  contents: read

concurrency:
  group: build-windows
  cancel-in-progress: false

jobs:''']
for i in range(1, STAGES + 1):
  first = i == 1
  prev = f'needs.stage-{i - 1}.outputs.finished'
  skip = "" if first else f"\n        if: {prev} != 'true'"
  out.append(f'''  stage-{i}:{"" if first else f"{chr(10)}    needs: stage-{i - 1}"}
    runs-on: windows-2022
    timeout-minutes: 358
    outputs:
      finished: ${{{{ {"steps.stage.outputs.finished" if first else f"steps.stage.outputs.finished || {prev}"} }}}}
    steps:
      - uses: actions/checkout@v4{skip}
      - uses: ./.github/actions/prepare{skip}
      - name: Compilar
        id: stage{skip}
        uses: ./.github/actions/stage
        with:
          finished: false
          from_artifact: {"false" if first else "true"}''')
out.append(f'''  publish:
    needs: stage-{STAGES}
    if: needs.stage-{STAGES}.outputs.finished == 'true'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: nium-windows
          path: dist
      - name: Criar Release
        env:
          GH_TOKEN: ${{{{ github.token }}}}
        run: |
          tag="build-${{{{ github.run_number }}}}"
          gh release create "$tag" dist/*.zip --repo "${{{{ github.repository }}}}" \\
            --target "${{{{ github.sha }}}}" --prerelease \\
            --title "Nium (compilação ${{{{ github.run_number }}}})" \\
            --notes "Compilado de ${{{{ github.sha }}}}. Descompacte e abra chrome.exe."
''')
path = Path(__file__).resolve().parents[1] / '.github' / 'workflows' / 'build.yml'
path.write_text('\n'.join(out))
print(f'escrito {path}')
