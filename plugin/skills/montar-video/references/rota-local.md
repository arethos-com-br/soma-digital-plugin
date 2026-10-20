# Rota local (sem CapCut)

Monta e renderiza o MP4 no computador de quem usa, com corte na batida da música. Precisa do ffmpeg no PATH; o script usa só a biblioteca padrão do Python. Sem ffmpeg: no Windows `winget install Gyan.FFmpeg`, no macOS `brew install ffmpeg`; peça antes de instalar.

Rodar: `py -B -I scripts/video_local.py render plano.json` no Windows (`python3` no macOS/Linux). `batidas <musica>` mostra BPM e acentos; `teste` confere o detector.

## Música

Arquivo de áudio ou vídeo com a música (a que indicarem, o áudio da trend baixado, ou extraída de um vídeo de referência). Ache o trecho que interessa (`musica_inicio`, em segundos); o vídeo começa na primeira batida depois dele. A detecção assume tempo constante; faixa só de voz não tem batida (use `"no_ritmo": false`).

## Plano (`plano.json`)

Caminhos relativos ao plano. Campos do plano sobrescrevem os da receita.

```json
{
  "receita": "corte-musical",
  "musica": "musica.m4a", "musica_inicio": 3.2,
  "duracao": 15,
  "clipes": [{"arquivo": "brutos/IMG_5291.MP4", "inicio": 0.5}, {"arquivo": "brutos/IMG_0074.MP4", "inicio": 3}],
  "saida": "video.mp4"
}
```

- `inicio`: segundo do bruto onde começa o melhor trecho (escolhido ao examinar os quadros).
- Por clipe, opcional: `batidas` (fixa quantas batidas ele dura), `segundos` (sem música), `zoom` (true/false), `continuo` (segue o bloco inteiro).
- `voz`: `{"arquivo": ..., "inicio": ...}`, áudio contínuo de quem fala; a música desce para `musica_volume` (0.25). O clipe de quem fala com `"continuo": true` fica em sincronia com a voz.
- `blocos`: a sequência de layouts. Cada bloco tem `layout` (`cheio`, `cima-baixo`, `faixas` com `n`, `lado-a-lado`), `segundos` ou `batidas`, e `paineis`: uma lista de clipes por painel (em `cima-baixo`, o primeiro é o de cima). Painel com clipe mais curto que o bloco segura o último quadro. O último bloco sem duração preenche até `duracao`.

## Receitas (`receitas/*.json`)

Templates nossos, editáveis: estrutura, ritmo e efeitos, sem fixar a duração dos clipes.

| Receita | Quando | Estrutura |
|---|---|---|
| `corte-musical` | vitrine de produto ou loja no ritmo da música | gancho de 4 batidas; cada corte no golpe mais forte entre 1 e 2 batidas; zoom leve; flash no primeiro corte |
| `tela-dividida` | anúncio com alguém falando | cima-baixo (quem fala em cima, produto embaixo), 4 faixas, produto em tela cheia; voz contínua e música de fundo |

## Conferir

Antes de entregar: `ffprobe` (duração 1080x1920, áudio presente) e uma folha de quadros (`ffmpeg -i video.mp4 -vf "fps=1,scale=135:-1,tile=15x1" -frames:v 1 folha.jpg`) olhada de fato. Entregue o caminho do MP4 e o que foi aplicado. Não faz: texto e legenda, recorte de pessoa sobre fundo, transições com desfoque de movimento.
