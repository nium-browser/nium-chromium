# Nium (Chromium)

O navegador Nium, feito sobre o Chromium. Tudo o que é do Nium fica em `nium/`; as mudanças nos
arquivos do próprio Chromium são feitas por `nium/scripts/apply.py`.

## Baixar
Cada compilação terminada aparece em **Releases**: descompacte o zip e abra `chrome.exe`.

## Compilar
A compilação roda no GitHub Actions (aba **Actions → build-windows → Run workflow**). Ela é
dividida em etapas de até 6 horas: cada etapa continua de onde a anterior parou. A versão do
Chromium usada está em `ci/CHROMIUM_VERSION`.

- `ci/build.py` — baixa o Chromium, aplica o Nium, compila e empacota.
- `ci/make_workflow.py` — gera `.github/workflows/build.yml`.
- `.github/actions/stage` — uma etapa (salva/retoma o progresso). Baseado no
  [ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows)
  (BSD-3-Clause).

## Mexer na interface sem compilar
A interface do Nium (`nium/ui`) é HTML/CSS/JS. No zip ela fica na pasta `nium_ui` ao lado do
`chrome.exe`: edite lá e reabra o Nium. Para testar uma pasta sua: `chrome.exe --nium-ui-dir=<pasta>`.
