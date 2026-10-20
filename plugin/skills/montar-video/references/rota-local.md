# Rota local (sem CapCut)

Monta e renderiza o MP4 no computador de quem usa, com corte na batida da música. Precisa do ffmpeg no PATH; o script usa só a biblioteca padrão do Python. Sem ffmpeg: no Windows `winget install Gyan.FFmpeg`, no macOS `brew install ffmpeg`; peça antes de instalar.

Rodar: `py -B -I scripts/video_local.py render plano.json` no Windows (`python3` no macOS/Linux). `batidas <musica>` mostra BPM e acentos; `teste` confere o detector.

## Música

Arquivo de áudio ou vídeo com a música (a que indicarem, o áudio da trend baixado, ou extraída de um vídeo de referência). Sem `musica_inicio`, o vídeo começa no primeiro golpe forte da música (pula introdução calma); para outro trecho, informe o segundo e o vídeo começa na primeira batida depois dele. A detecção assume tempo constante; faixa só de voz não tem batida (use `"no_ritmo": false`).

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

- `inicio`: segundo do bruto onde começa o melhor trecho, escolhido ao examinar os quadros (evite o começo tremido ou vazio do bruto; não deixe todos em 0).
- Não copie nem edite o script; se ele falhar, pare e informe o erro.
- Por clipe, opcional: `transicao` (como ele entra, no golpe), `efeito` ou `efeitos` (lista), `sfx` (efeito sonoro no corte), `zoom` (true/false), `continuo` (segue o bloco inteiro), `batidas` (fixa a duração; evite, tira o corte do golpe), `segundos` (sem música).
- Sem `transicao` no clipe, as transições giram pela lista `transicoes` da receita; `sfx_nos_cortes` põe o mesmo efeito sonoro em todos os cortes.
- `voz`: `{"arquivo": ..., "inicio": ...}`, áudio contínuo de quem fala; a música desce para `musica_volume` (0.25). O clipe de quem fala com `"continuo": true` fica em sincronia com a voz.
- `blocos`: a sequência de layouts. Cada bloco tem `layout` (`cheio`, `cima-baixo`, `faixas` com `n`, `lado-a-lado`), `segundos` ou `batidas`, e `paineis`: uma lista de clipes por painel (em `cima-baixo`, o primeiro é o de cima). Painel com clipe mais curto que o bloco segura o último quadro. O último bloco sem duração preenche até `duracao`.

## Corte na música

Com `cortar_nos_golpes`, o corte cai nos golpes da música (picos medidos no áudio, não numa grade fixa): o gancho vai até o primeiro golpe forte depois de `gancho_min` s; depois cada corte no próximo golpe com força ≥ `golpe_forte` (0 a 1), nenhum clipe com menos de `corte_min` s; sem golpe forte até `corte_max` s, o clipe estica até o golpe mais forte do fim da janela. O render devolve `sincronia` (cortes no golpe e golpes fortes com corte) e `cortes`; cite os números na entrega.

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
| `corte-musical` | vitrine de produto ou loja no ritmo da música | gancho até o primeiro golpe forte; cada corte num golpe; transições em giro (zoom in, corte, desfoque, corte, zoom out, brilho); zoom leve; flash no primeiro corte |
| `tela-dividida` | anúncio com alguém falando | cima-baixo (quem fala em cima, produto embaixo), 4 faixas, produto em tela cheia; voz contínua e música de fundo |

## Conferir

Antes de entregar: `ffprobe` (duração 1080x1920, áudio presente) e uma folha de quadros (`ffmpeg -i video.mp4 -vf "fps=1,scale=135:-1,tile=15x1" -frames:v 1 folha.jpg`) olhada de fato. Entregue o caminho do MP4 e o que foi aplicado. Não faz: texto e legenda, recorte de pessoa sobre fundo, transição com dissolução (Combinar), Radial Blur.
