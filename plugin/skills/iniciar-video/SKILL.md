---
name: iniciar-video
description: Começa um vídeo novo da Soma Digital. Localiza os brutos no computador ou no Drive, confirma cliente e pedido e passa para montar-video. Use quando pedirem para criar, começar ou fazer um vídeo novo, ou quando faltar a ficha do cliente.
---

# Iniciar vídeo

Deduza antes de perguntar. Use apenas arquivos que o ambiente atual consegue acessar. Cada pergunta que o material responde (pastas, subpastas, quadros, áudio, referências) você mesmo responde; pergunte só o que não dá para saber. Registre só o que observou e marque cada campo como **dito** (por quem usa) ou **deduzido** (com a pista).

1. **Achar o material.** Use o caminho local informado ou, quando a pessoa indicar o Drive, a conexão disponível. Se não houver caminho nem conexão, pergunte onde estão os arquivos. Liste brutos (inclusive em subpastas) e referências. Brutos são clipes soltos e referências são vídeos já editados; confira pelo conteúdo, não pelo nome. Para render local, confirme que os brutos e a música também estão em uma pasta local acessível; um link do Drive, sozinho, não é um caminho local.
2. **Examinar.** Veja quadros e áudio de uma amostra dos brutos e das referências com o que o ambiente oferece (no Claude, ver [ambientes](../montar-video/references/ambientes.md)). Disso saem: produto ou oferta em destaque, segmento e subnicho, público e tom provável, duração e plataforma das referências, modo mais adequado, e quais clipes têm fala ou som que importe (alimenta a regra de áudio de `montar-video`). Se não puder abrir um arquivo, diga qual e peça uma alternativa acessível; não deduza seu conteúdo pelo nome.
3. **Confirmar de uma vez.** Mostre a ficha em poucas linhas e peça um "ok" ou correção:
   - **Cliente:** segmento e subnicho, oferta em destaque, público, tom.
   - **Pedido:** origem e quantidade de brutos e referências, plataforma, duração, música (a indicada ou uma em alta), modo (`corte-musical-produto` ou `template-tela-dividida`) e saída: MP4 local (padrão) ou draft editável no CapCut (só se pedido).
   - **Perguntas:** só as que o material não respondeu, no máximo 3, cada uma com um exemplo de resposta. Não pergunte o que a ficha já propõe (o "ok" cobre); se nada ficou sem resposta, não faça perguntas.

Adote MP4 local por padrão; não exija Drive ou CapCut para essa rota. Para ela, os arquivos precisam estar acessíveis no computador e Python 3, FFmpeg e FFprobe precisam estar instalados. Use a rota CapCut apenas se pedida e confira as integrações necessárias ao ambiente em [ambientes](../montar-video/references/ambientes.md). Se o cliente tem nicho ou subnicho, o planejamento consulta `buscar-tendencias` para anúncios do nicho. Nesta etapa não se edita nem se envia nada ao CapCut.
