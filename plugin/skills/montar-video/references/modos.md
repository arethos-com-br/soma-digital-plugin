# Modos de entrega

| Modo | Resultado | Cuidados |
|---|---|---|
| `corte-musical-produto` | Sequência de clipes reais cortada pelo ritmo da música | Áudio original desligado, salvo clipe com fala ou som do produto que importe; gancho nos primeiros segundos |
| `template-tela-dividida` | Dois espaços de vídeo, cada um com duração e enquadramento independentes | Ajustes de um lado não podem alterar o outro; definir o que ocorre quando um clipe acaba antes |

Batida: a API do CapCut não entrega batidas. A busca de música não traz BPM nem prévia, e as marcas da "Detecção de batidas" do editor ficam na nuvem mas não voltam no snapshot (medido em 20/10/2026). Corte numa grade regular e diga na entrega que o corte não está na batida. Não ofereça templates do CapCut: eles fixam duração e espaços, que os dois modos deixam livres. Na rota local, o corte cai nos acentos da música (ver [rota local](rota-local.md)).

Primeiro modo em validação: `corte-musical-produto`.
