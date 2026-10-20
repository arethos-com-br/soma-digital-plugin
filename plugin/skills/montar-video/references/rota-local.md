# Rota local (sem CapCut)

Monta e renderiza o MP4 no computador de quem usa, com corte na batida da música. Precisa do ffmpeg no PATH; o script usa só a biblioteca padrão do Python. Sem ffmpeg: no Windows `winget install Gyan.FFmpeg`, no macOS `brew install ffmpeg`; peça antes de instalar.

Rodar: `py -B -I scripts/video_local.py render plano.json` no Windows (`python3` no macOS/Linux). `batidas <musica>` mostra BPM e acentos; `teste` confere o detector.

## Música

Arquivo de áudio ou vídeo com a música (a que indicarem, o áudio da trend baixado, ou extraída de um vídeo de referência). Deixe `musica_inicio` de fora (não use 0): o vídeo começa onde a batida já está em sequência, pulando introdução, voz e efeito sonoro solto. Informe o segundo só quando pedirem um trecho; aí o vídeo começa na primeira batida depois dele. Música tirada de um vídeo já editado (um exemplo, outro Reels) traz junto os efeitos sonoros e a voz daquela edição; se a parte só de música for mais curta que o vídeo, o render avisa: repasse o aviso e peça a música completa ou um vídeo mais curto. A detecção assume tempo constante; faixa só de voz não tem batida (use `"no_ritmo": false`).

## Plano (`plano.json`)

Caminhos relativos ao plano. Campos do plano sobrescrevem os da receita.

```json
{
  "receita": "corte-musical",
  "musica": "musica.m4a",
  "duracao": 15,
  "clipes": [{"arquivo": "brutos/IMG_5291.MP4", "inicio": 0.5}, {"arquivo": "brutos/IMG_0074.MP4", "inicio": 3}],
  "saida": "video.mp4"
}
```

- `inicio`: deixe de fora; o script escolhe a janela de cada bruto com o produto centralizado e no tamanho certo, nítida e com movimento, fora do começo e do fim, sem repetir trecho. Informe só quando viu um momento específico que precisa entrar.
- Não copie nem edite o script; se ele falhar, pare e informe o erro.
- Por clipe, opcional: `transicao` (como ele entra, no golpe), `efeito` ou `efeitos` (lista), `sfx` (efeito sonoro no corte), `zoom` (true/false), `continuo` (segue o bloco inteiro), `batidas` (fixa a duração; evite, tira o corte do golpe), `segundos` (sem música).
- Sem `transicao` no clipe, as transições giram pela lista `transicoes` da receita; `sfx_nos_cortes` põe o mesmo efeito sonoro em todos os cortes.
- `velocidade`: força uma velocidade no clipe (0.5 a 1); a receita já põe câmera lenta nos clipes longos.
- `enquadrar`: `false` no clipe desliga o reenquadramento automático dele.
- `voz`: `{"arquivo": ..., "inicio": ...}`, áudio contínuo de quem fala; a música desce para `musica_volume` (0.25). O clipe de quem fala com `"continuo": true` fica em sincronia com a voz.
- `blocos`: a sequência de layouts. Cada bloco tem `layout` (`cheio`, `cima-baixo`, `faixas` com `n`, `lado-a-lado`), `segundos` ou `batidas`, e `paineis`: uma lista de clipes por painel (em `cima-baixo`, o primeiro é o de cima). Painel com clipe mais curto que o bloco segura o último quadro. O último bloco sem duração preenche até `duracao`.

## Corte na música

Com `cortar_nos_golpes`, a troca de clipe cai no grave da música (bumbo e baixo, abaixo de 150 Hz), não numa grade de BPM: a batida não é cíclica, e o corte segue os golpes que a faixa tem de fato. Entram os golpes do grave acima de `golpe_piso` (0,6 da força dos golpes fortes daquela faixa), do mais forte para o mais fraco, com `corte_min` entre cortes; onde o grave bate forte e junto os clipes ficam curtos, onde some ficam longos. Vão maior que `corte_max` ganha o golpe mais forte do meio; nunca corta no silêncio. Faixa sem grave que bata (voz, violão) corta nos golpes do som todo; o render diz qual usou em `corte_no`. O gancho termina no golpe mais forte entre `gancho_min` e `gancho_max`. Testado em seis gêneros sintéticos (todo corte em bumbo ou baixo, nunca na caixa ou no chimbal) e na música do A01, onde os cortes caem nos mesmos golpes em que a Vitória cortou: `teste` repete essa conferência.

O render devolve `corte_no`, `sincronia` (cortes, cortes num golpe forte a ±40 ms, golpes fortes e quantos ganharam corte), `cortes` e `clipes` (trecho, velocidade e zoom de cada um); cite os números na entrega.

## Dinâmica

- `ordem: contraste`: mantém o primeiro clipe (gancho) e encadeia os outros do mais diferente para o mais diferente do anterior (cor média), para não juntar planos iguais.
- `pulsos`: empurrão de zoom de 4% nos golpes fortes que caem dentro de um clipe.
- `enquadrar`: acha o produto em cada quadro (o que destoa do fundo, sem contar a mão) e recorta seguindo ele: centro do quadro e largura `tamanho_alvo` (0,5, medida no A02), com zoom até `zoom_teto` (1,35, para não perder nitidez). Planos de pessoa ou de loja não têm produto destacado e ficam como estão; neles o trecho escolhido é o que termina no gesto concluído (pôs o óculos e olhou para a câmera), para o corte não chegar antes.
- `lento` (0.7), `lento_min` (0,9 s) e `rampa`: nos clipes longos, entra no golpe em velocidade normal e desacelera até 0,7x; os quadros intermediários são criados por fluxo de movimento, sem engasgar a partir de 30 qps.
- `sfx_nas_transicoes`: o som acompanha a transição visual (zoom e desfoque: swoosh; flash com falha: glitch), baixo (`sfx_volume` 0.35); corte seco fica sem som.
- `transicoes`: giro das transições, intercaladas com cortes secos.

## Repertório (D01) na rota local

| Da lista dela | Campo e valor |
|---|---|
| Zoom In / Zoom Out | `transicao`: `zoom_in`, `zoom_out` |
| Fade In/Out | `transicao`: `fade` |
| Flash | `transicao`: `flash` |
| Reflexo de luz / Brilho | `transicao`: `brilho` |
| Blur (Desfoque) | `transicao`: `desfoque` |
| Flash com falha | `transicao`: `flash_falha` |
| Câmera de mão | `efeito`: `camera_de_mao` |
| Obturador lento | `efeito`: `obturador_lento` |
| Sobreposição negativa | `efeito`: `negativo` (2 quadros no golpe) |
| Desfoque cromático | `efeito`: `cromatico` |
| Swoosh, Woosh, Swish, Shun | `sfx`: `swoosh` (sintetizado; o pico cai no corte) |
| Pop, Click Sound, Glitch, Wind Noise | `sfx`: `pop`, `click`, `glitch`, `vento` (sintetizados) |
| Combinar, Radial Blur, Typing, Typewriting | sem equivalente: o render avisa e deixa de fora |

Os efeitos sonoros são sintetizados pelo ffmpeg (sem arquivo); soam simples. Use com moderação: um por transição forte, não em todo corte.

## Receitas (`receitas/*.json`)

Templates nossos, editáveis: estrutura, ritmo e efeitos, sem fixar a duração dos clipes.

| Receita | Quando | Estrutura |
|---|---|---|
| `corte-musical` | vitrine de produto ou loja no ritmo da música | gancho até o golpe mais forte entre 1,5 e 4 s; cortes no bumbo e no baixo; ordem por contraste; trecho automático; produto centralizado e do mesmo tamanho; câmera lenta leve (0,7x) com rampa nos clipes longos; pulsos; transições intercaladas com corte seco, com som junto |
| `tela-dividida` | anúncio com alguém falando | cima-baixo (quem fala em cima, produto embaixo), 4 faixas, produto em tela cheia; voz contínua e música de fundo |

## Conferir

Antes de entregar: `ffprobe` (duração 1080x1920, áudio presente) e uma folha de quadros (`ffmpeg -i video.mp4 -vf "fps=1,scale=135:-1,tile=15x1" -frames:v 1 folha.jpg`) olhada de fato: o produto tem que aparecer inteiro e perto do centro em todos os clipes; se algum ficar cortado ou perto demais, informe `inicio` de um momento melhor daquele bruto e renderize de novo. Entregue o caminho do MP4 e o que foi aplicado. Não faz: texto e legenda, recorte de pessoa sobre fundo, transição com dissolução (Combinar), Radial Blur.
