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
- **Ticket de upload:** o enviador lê o ticket do stdin, sem TTY: `printf '%s' "<ticket>" | node <skill>/scripts/capcut-upload.mjs --files '[...]' --upload-ticket-stdin --json`. Nunca em argumento nem em log.
- **Login:** só pelo `/mcp`. Ignore as instruções de `mcp-auth` e de `codex mcp login`.
- **Link do editor:** entregue o link ao usuário; a verificação visual depende de navegador disponível, senão diga que não foi feita.
