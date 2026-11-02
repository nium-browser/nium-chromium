# Nium (Chromium)

Tudo o que é do Nium fica nesta pasta (`src/nium`). As mudanças em arquivos do próprio Chromium
são feitas por script, para poderem ser reaplicadas a cada versão nova do Chromium.

Base atual: Chromium **159.0.8134.0** (dev). Antes do lançamento vamos para a estável do momento.

## Aplicar e compilar

No cmd (como administrador), dentro de `E:\src\chromium\src`:

```
python3 nium\scripts\apply.py
autoninja -C out\Nium chrome
out\Nium\chrome.exe
```

`apply.py` faz tudo (marca + integrações) e pode rodar quantas vezes quiser.

## Fase 1 — marca Nium
- Nome, ícones e textos dizem "Nium" (traduções mantidas).
- Perfil em `%LOCALAPPDATA%\Nium\User Data`.
- Sem o aviso "Google API keys are missing".

## Fase 2 — chrome://nium (interface + ponte)
- `nium\ui\` — a interface do Nium (HTML/CSS/JS). **Mudou algo aqui? Só aperte F5 em chrome://nium,
  não precisa compilar.** O Nium procura a pasta em: `--nium-ui-dir=<pasta>`, depois `<exe>\nium_ui`,
  depois `src\nium\ui`.
- `nium\browser\ui\webui\` — o lado C++ (`chrome.send('nium.call', ...)`). Mudou aqui? Compile.
- Funções da ponte hoje: `version`, `openTab {url}`, `storeGet {key}`, `storeSet {key, value}`
  (dados em `<perfil>\Nium\<chave>.json`).
- Teste: abra `chrome://nium`.

## Fase 3 — a janela do Nium
- Toda janela normal tem a **barra lateral do Nium** à esquerda () no lugar
  da faixa de abas do Chromium. As abas são as de verdade: clicar ativa, X ou botão do meio fecha,
  arrastar reordena, "Nova aba" abre uma.
- A faixa de cima da barra lateral (40px) e o espaço vazio da barra de ferramentas arrastam a janela.
- Em tela cheia (vídeo, F11) a barra lateral some.
-  volta para as abas do Chromium (para comparar).
- Funções novas da ponte: ,  (depois disso chega o evento  a cada
  mudança; ouça com ), , ,
  , .
- Código:  (a barra na janela) e
   (ligação com a página). Os arquivos do Chromium
  mexidos estão em  ().

## Atualizar o Chromium

```
python3 nium\scripts\apply.py --revert
git fetch --depth=1 origin refs/tags/<versão> && git checkout -b nium-<versão> FETCH_HEAD
gclient sync -D --no-history
python3 nium\scripts\apply.py
```
