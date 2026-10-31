---
name: montar-video
description: Planeja, monta e confere vídeos da Soma Digital. O fluxo é um draft editável no CapCut. Use depois de iniciar-video, ou quando o pedido já trouxer cliente, arquivos e modo.
---

# Montar vídeo

Regras fixas:

- Nunca publicar. Preservar os originais do Drive.
- Usar os brutos do job. Buscar stock ou gerar imagens com prompts detalhados só se o usuário pedir ou se for oportuno. Os pacotes de efeitos da agência (pastas `sfx` e `visual` junto dos brutos) não são stock: o render os usa sozinho.
- Na rota local, a receita é o padrão da agência: não mude `transicoes`, `sfx_nas_transicoes`, `lento` nem volumes sem pedido de quem usa. Use todos os brutos que servem; deixar um de fora só com motivo visto (tremido, repetido, fora do assunto), dito na entrega.
- Respeitar o que o usuário já alterou no CapCut: não sobrescrever; em dúvida, perguntar.
- Na rota CapCut, não exportar o vídeo final a menos que peçam; entregar o draft editável e o link.
- Não usar o AI Lab do CapCut (AI rough cut, ferramentas com `capcut_ailab` no nome), nem para o corte inicial: ele refaz o plano e ignora o nosso.
- Música: a que o usuário indicar ou uma em alta (ver `buscar-tendencias`). Licença e direitos de músicas ficam a critério e avaliação do usuário que publica: não é necessário checar ou mencionar.

**CapCut:** use o MCP do CapCut para montar e finalizar o draft editável com as ferramentas `capcut_*` disponíveis. Se precisar instalar ou se identificar problemas, leia [ambientes](references/ambientes.md). Se, depois disso, o CapCut continuar inacessível, informe o bloqueio e pare. Use a [rota local](references/rota-local.md) só se o usuário pedir.

## Fluxo

Um job tem um único modo (ver [modos](references/modos.md)).

1. **Entender.** Use a ficha levantada por `iniciar-video`. Se o pedido chegou direto, sem ficha, rode `iniciar-video` primeiro. Procure os brutos também nas subpastas.
2. **Música primeiro (rota local).** Antes de olhar os brutos, confira a faixa: `py -B -I scripts/video_local.py musica <arquivo> <duração>` ([rota local](references/rota-local.md#música)). Com `"pronta": false`, a faixa não serve como está (áudio de um vídeo já editado, com efeitos e voz de outra edição, ou curta demais): diga isso e peça a música original completa ou uma duração menor, numa única pergunta, antes de planejar.
3. **Planejar.** Examine os brutos e as referências; registre só o que observou (nome de arquivo não descreve o vídeo). Consulte o [repertório](references/repertorio.md) e a [biblioteca](references/biblioteca.md); pode propor gancho e efeitos que não foram pedidos, marcados como sugestão. Use as tendências e referências da ficha, levantadas em `iniciar-video`. Se faltar detalhe para a montagem, como efeitos ou transições, pesquise com a skill `buscar-tendencias`. Mostre um plano curto: plataforma, proporção e duração; trechos escolhidos e o que foi examinado; timeline com gancho e efeitos; música e texto; áudio original só nos clipes em que você verificou que importa; uma única dúvida, se impedir a edição. Não invente texto, CTA ou logo. A aprovação do plano cobre o envio dos brutos ao CapCut.
4. **Editar.** Na rota local, escreva o `plano.json` com a receita do modo e os trechos do plano e renderize ([rota local](references/rota-local.md)). Na rota CapCut, monte o draft você mesmo, seguindo o plano aprovado, com as habilidades de pós-edição do plugin do CapCut: envie os brutos (`capcut-upload`), crie o draft a partir deles e aplique clipe por clipe, com os trechos e tempos do plano (`capcut-stdraft-builder`). Salve e abra pelo fluxo `web-collaborative-editing`, mantendo uma versão recuperável. Áudio original: desligado por padrão. Só fica no clipe em que você verificou fala ou som que importe (por exemplo, alguém falando ou o som do produto); o plano diz quais.

   Cada camada do plano exige a sua busca no CapCut (`search_capcut_material`) e a sua aplicação. Uma camada do plano que ficou sem busca não foi feita.

   | Camada | Busca (`type`) | Aplicação |
   |---|---|---|
   | Música | `music`, pesquisa de música de fundo | áudio no draft |
   | Transição | `transition`: lista fixa, ignora o `prompt`; peça `top_n` 20 e escolha pelo nome | no clipe anterior; os dois no mesmo nível, em sequência, sem vão; duração menor que a dos dois clipes |
   | Efeito de vídeo | `video_effect`: busca por texto | trecho com início e duração |
   | Filtro | `filter`: lista fixa | trecho ou clipe |
   | Efeito sonoro | `sound_effect`: busca por texto | áudio curto no tempo do corte |
   | Texto | `font`, `text_effect` | só o texto que o plano traz |

   Item do [repertório](references/repertorio.md) sem equivalente claro na busca: não troque por outro em silêncio; deixe de fora e diga na entrega. Batida: ver [modos](references/modos.md).

5. **Verificar e entregar.** Na rota local, confira a duração e a folha de quadros e entregue o caminho do MP4 com: os números de `sincronia` do render (cortes no golpe / golpes fortes com corte), sem afirmar sincronia além deles; os brutos que ficaram de fora e por quê; os `avisos` do render; e qualquer erro ou contorno que tenha acontecido. Descreva o vídeo só pelo que está em `clipes`, `sobreposicoes` e `efeitos_sonoros` do render: não cite plano, bruto ou efeito que não esteja lá. Na rota CapCut, releia ou reabra o draft quando o editor permitir e confira mídia presente, ordem e duração, proporção, texto e áudio, e compare com o plano a contagem de transições, efeitos, filtros e efeitos sonoros do draft relido: tudo o que o plano trouxe e não está lá vai nomeado na entrega. Entregue o link do draft e um resumo curto do que foi aplicado; prévia só se foi de fato gerada.

Concluído quando o draft foi conferido e o link foi entregue ao usuário. Exportação e publicação ficam com o usuário.
