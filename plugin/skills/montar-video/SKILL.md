---
name: montar-video
description: Planeja, monta e confere um vídeo da Soma Digital (MP4 cortado na batida, renderizado no computador, ou draft editável no CapCut), a partir dos brutos do Drive e da ficha do cliente. Use depois de iniciar-video, ou quando o pedido já trouxer cliente, pasta dos brutos e modo (corte musical, tela dividida).
---

# Montar vídeo

Regras fixas:

- Nunca publicar. Preservar os originais do Drive.
- Usar só os brutos do job. Sem stock, mídia gerada ou imagem genérica.
- Respeitar o que já foi alterado no CapCut por quem usa: não sobrescrever; em dúvida, perguntar.
- Na rota CapCut, não exportar o vídeo final a menos que peçam; entregar o draft editável e o link.
- Não usar o AI Lab do CapCut (AI rough cut, ferramentas com `capcut_ailab` no nome), nem para o corte inicial: ele refaz o plano e ignora o nosso.
- Música: a que indicarem ou uma em alta (ver `buscar-tendencias`). Não cheque nem mencione licença ou direitos: o uso é como no Instagram.

Duas rotas. **Local** (padrão): renderiza o MP4 com ffmpeg, cortando na batida da música; ver [rota local](references/rota-local.md). **CapCut**: draft editável no editor, sem corte na batida; use quando pedirem para editar no CapCut. A rota CapCut precisa de acesso ao CapCut na sessão; se faltar, avise e pare. Os nomes das ferramentas e o que muda em cada ambiente (Codex, Claude) estão em [ambientes](references/ambientes.md).

## Fluxo

Um job tem um único modo (ver [modos](references/modos.md)).

1. **Entender.** Use a ficha do cliente e o pedido levantados por `iniciar-video`. Se o pedido chegou direto, sem ficha, rode `iniciar-video` primeiro. Procure os brutos também nas subpastas.
2. **Planejar.** Examine os brutos e as referências; registre só o que observou (nome de arquivo não descreve o vídeo). Consulte o [repertório](references/repertorio.md) e a [biblioteca](references/biblioteca.md); pode propor gancho e efeitos que não foram pedidos, marcados como sugestão. Se o cliente tem nicho específico, consulte também a skill `buscar-tendencias` para anúncios do nicho. Mostre um plano curto: plataforma, proporção e duração; trechos escolhidos e o que foi examinado; timeline com gancho e efeitos; música e texto; áudio original só nos clipes em que você verificou que importa; uma única dúvida, se impedir a edição. Não invente texto, CTA ou logo. A aprovação do plano cobre o envio dos brutos ao CapCut.
3. **Editar.** Na rota local, escreva o `plano.json` com a receita do modo e os trechos do plano e renderize ([rota local](references/rota-local.md)). Na rota CapCut, monte o draft você mesmo, seguindo o plano aprovado, com as habilidades de pós-edição do plugin do CapCut: envie os brutos (`capcut-upload`), crie o draft a partir deles e aplique clipe por clipe, com os trechos e tempos do plano (`capcut-stdraft-builder`). Salve e abra pelo fluxo `web-collaborative-editing`, mantendo uma versão recuperável. Áudio original: desligado por padrão. Só fica no clipe em que você verificou fala ou som que importe (por exemplo, o cliente falando ou o som do produto); o plano diz quais.

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

4. **Verificar e entregar.** Na rota local, confira a duração e a folha de quadros e entregue o caminho do MP4. Na rota CapCut, releia ou reabra o draft quando o editor permitir e confira mídia presente, ordem e duração, proporção, texto e áudio, e compare com o plano a contagem de transições, efeitos, filtros e efeitos sonoros do draft relido: tudo o que o plano trouxe e não está lá vai nomeado na entrega. Entregue o link do draft e um resumo curto do que foi aplicado; prévia só se foi de fato gerada.

Concluído quando o draft foi conferido e quem pediu recebeu o link. Ajustes, exportação e publicação são decisão de quem usa.
