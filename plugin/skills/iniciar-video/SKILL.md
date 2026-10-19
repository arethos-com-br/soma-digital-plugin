---
name: iniciar-video
description: Começa um vídeo novo da Soma Digital. Levanta cliente, pedido e pastas do Drive deduzindo o que o material mostra, confirma de uma vez e passa para montar-video. Use quando pedirem para criar, começar ou fazer um vídeo novo, ou quando faltar a ficha do cliente.
---

# Iniciar vídeo

Deduza antes de perguntar. Cada pergunta que o material responde (pastas, subpastas, nomes, quadros, áudio, referências) você mesmo responde; pergunte só o que não dá para saber. Registre só o que observou e marque cada campo como **dito** (por quem usa) ou **deduzido** (com a pista).

1. **Achar o material.** Com as pastas que a pessoa citou (ou, sem nenhuma, a pasta do Drive mais provável; só pergunte se não houver pista), liste brutos (inclusive em subpastas) e referências. Brutos são clipes soltos e referências são vídeos já editados; confira pelo conteúdo, não pelo nome.
2. **Examinar.** Veja quadros e áudio de uma amostra dos brutos e das referências com o que o ambiente oferece (no Claude, ver [ambientes](../montar-video/references/ambientes.md)). Disso saem: produto ou oferta em destaque, segmento e subnicho, público e tom provável, duração e plataforma das referências, modo mais adequado, e quais clipes têm fala ou som que importe (alimenta a regra de áudio de `montar-video`).
3. **Confirmar de uma vez.** Mostre a ficha em poucas linhas e peça um "ok" ou correção:
   - **Cliente:** segmento e subnicho, oferta em destaque, público, tom.
   - **Pedido:** pastas (com a quantidade de brutos e referências), plataforma, duração, música (a indicada ou uma em alta) e modo: `corte-musical-produto` (clipes cortados no ritmo da música) ou `template-tela-dividida` (dois vídeos na mesma tela).
   - **Perguntas:** só as que o material não respondeu, no máximo 3, cada uma com um exemplo de resposta. Não pergunte o que a ficha já propõe (o "ok" cobre); se nada ficou sem resposta, não faça perguntas.

Depois siga com `montar-video`, levando a ficha. Se o cliente tem nicho ou subnicho, o planejamento consulta `buscar-tendencias` para anúncios do nicho. Nesta etapa não se edita nem se envia nada ao CapCut.
