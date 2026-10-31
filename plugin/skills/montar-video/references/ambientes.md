# Ambientes

O fluxo é o mesmo em qualquer ambiente; muda o acesso ao CapCut. Use os recursos do CapCut abaixo pelo que fazem; os nomes são do plugin oficial.

| Recurso do CapCut | Para quê |
|---|---|
| `capcut-upload` | enviar brutos locais e obter os ids de mídia |
| `capcut-stdraft-builder` | criar e editar o draft clipe a clipe (vídeo, música, efeitos, transições, texto) |
| `web-collaborative-editing` | sessão, versão, salvar na nuvem e link do editor |
| busca de música de fundo | candidatas de música |

## Codex / ChatGPT desktop

O plugin oficial CapCut × Codex traz as ferramentas e o fluxo de autorização. Ele é separado do plugin Soma Digital. Se não estiver instalado e autorizado, instale-o pela [página oficial](https://www.capcut.com/tools/capcut-x-codex) e peça ao usuário, uma permissão por vez e dizendo para que serve: (1) autorizar o plugin do CapCut; (2) conectar o Google Drive, se os brutos ou referências estiverem lá; (3) liberar uma pasta local com os arquivos escolhidos, para o upload.

O aplicativo CapCut Desktop é outra instalação. Ele não é requisito para instalar ou autenticar o MCP; se a pessoa quiser abrir ou ajustar o draft nesse aplicativo, confirme se está instalado e indique o [download oficial para Windows](https://www.capcut.com/resource/capcut-for-windows) quando faltar.

## Claude (Claude Code)

- **Windows:** o fluxo de upload usa Bash (`printf`). No Claude Code nativo, instale Git for Windows para habilitar a ferramenta Bash; ou execute Claude Code no WSL.
- **Servidor:** `capcut_creation` em `https://www.capcut.com/api/external_mcp`, com login OAuth pelo `/mcp`. Sem login as ferramentas `capcut_*` não aparecem.
- **Skills do CapCut:** as três skills da tabela vêm do pacote oficial do CapCut (licença própria, não está neste repositório); precisam estar instaladas localmente.
- **Caminho local obrigatório:** o enviador só lê arquivos em disco. O download do Drive pelo conector passa por base64 no modelo e não serve para vídeo; use a pasta sincronizada (Google Drive para desktop). Se os brutos não estiverem em disco, diga isso e pare.
- **Ticket de upload:** o enviador lê o ticket do stdin, sem TTY: `printf '%s' "<ticket>" | node <skill>/scripts/capcut-upload.mjs --files '[...]' --upload-ticket-stdin --json`. Nunca em argumento nem em log. No Windows, use barras normais nos caminhos do JSON (`C:/Users/...`); barras invertidas quebram o JSON.
- **Montar o draft:** use as funções de `capcut-stdraft-builder` (`apply_video`, `apply_transition`, `apply_video_effect`, `apply_filter`, `apply_audio`) num script; no Windows, `py -B -I`. **Ordem dos clipes:** o CapCut pode mudar a ordem ao salvar ids aleatórios. Renomeie-os para `v01`, `v02`… na ordem do tempo antes do envio e confira o draft salvo.
- **Login:** só pelo `/mcp`; peça-o ao usuário, uma ação por vez e dizendo para que serve. Ignore as instruções de `mcp-auth` e de `codex mcp login`.
- **Link do editor:** entregue o link ao usuário; a verificação visual depende de navegador disponível, senão diga que não foi feita.
- **Examinar vídeo:** precisa de `ffmpeg`/`ffprobe` no PATH (no Windows: `winget install Gyan.FFmpeg`). Medido: uma folha de contato por clipe (`ffmpeg -i clip.mp4 -vf "fps=1/2,scale=240:-1,tile=5x2" folha.jpg`), lida como imagem, basta para identificar produto, cenário e logotipos; `-af volumedetect` dá o nível do áudio. Não há transcrição local: sem ela, diga que a fala não foi verificada.
