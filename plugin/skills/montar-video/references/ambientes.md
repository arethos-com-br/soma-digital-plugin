# Ambientes

O fluxo é o mesmo em qualquer ambiente; muda o acesso ao CapCut. Use os recursos do CapCut abaixo pelo que fazem; os nomes são do plugin oficial.

| Recurso do CapCut | Para quê |
|---|---|
| `capcut-upload` | enviar brutos locais e obter os ids de mídia |
| `capcut-stdraft-builder` | criar e editar o draft clipe a clipe (vídeo, música, efeitos, transições, texto) |
| `web-collaborative-editing` | sessão, versão, salvar na nuvem e link do editor |
| busca de música de fundo | candidatas de música |

## Codex / ChatGPT desktop

O plugin oficial do CapCut traz tudo isso e a autorização. Siga as skills dele.

## Claude (Claude Code)

- **Servidor:** `capcut_creation` em `https://www.capcut.com/api/external_mcp`, com login OAuth pelo `/mcp`. Sem login as ferramentas `capcut_*` não aparecem; avise e pare.
- **Skills do CapCut:** as três acima vêm do pacote oficial do CapCut (licença própria, não está neste repositório); precisam estar instaladas localmente. Se não estiverem, avise e pare.
- **Caminho local obrigatório:** o enviador só lê arquivos em disco. O download do Drive pelo conector passa por base64 no modelo e não serve para vídeo; use a pasta sincronizada (Google Drive para desktop). Se os brutos não estiverem em disco, diga isso e pare.
- **Ticket de upload:** o enviador lê o ticket do stdin, sem TTY: `printf '%s' "<ticket>" | node <skill>/scripts/capcut-upload.mjs --files '[...]' --upload-ticket-stdin --json`. Nunca em argumento nem em log. No Windows, use barras normais nos caminhos do JSON (`C:/Users/...`); barras invertidas quebram o JSON.
- **Montar o draft:** use as funções de `capcut-stdraft-builder` (`apply_video`, `apply_transition`, `apply_video_effect`, `apply_filter`, `apply_audio`) num script; no Windows, `py -B -I`. **Ordem dos clipes:** nas três rodadas de 19/10 o CapCut devolveu os clipes fora de ordem ao salvar quando os ids eram os gerados (cadeias aleatórias); o que funcionou (duas rodadas) foi renomear os ids dos clipes para `v01`, `v02`… na ordem do tempo antes de enviar. Hipótese: o salvamento ordena pelo id. Releia o draft salvo e confira a ordem.
- **Login:** só pelo `/mcp`. Ignore as instruções de `mcp-auth` e de `codex mcp login`.
- **Link do editor:** entregue o link ao usuário; a verificação visual depende de navegador disponível, senão diga que não foi feita.
- **Examinar vídeo:** precisa de `ffmpeg`/`ffprobe` no PATH (no Windows: `winget install Gyan.FFmpeg`). Medido: uma folha de contato por clipe (`ffmpeg -i clip.mp4 -vf "fps=1/2,scale=240:-1,tile=5x2" folha.jpg`), lida como imagem, basta para identificar produto, cenário e logotipos; `-af volumedetect` dá o nível do áudio. Não há transcrição local: sem ela, diga que a fala não foi verificada.
