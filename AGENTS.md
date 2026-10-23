# soma-digital-plugin

Plugin público de edição da Soma Digital (ChatGPT/Codex e Claude). O que é instalado fica em `plugin/`; este arquivo e o `README.md` são para quem desenvolve. Sem dados de cliente aqui.

## Aprendizados (não repetir)

Erros que já aconteceram, com a regra que os evita. Leia antes de mexer no `montar-video`.

**Critério vem do briefing e das referências**
- Antes de mudar estética ou ritmo, examine e meça nas referências aprovadas para o job. Mantenha preferências específicas do job fora do pacote público.
- Não altere uma receita com base em suposições; confira as referências e o resultado primeiro.

**Corte na música**
- Corte no grave (bumbo e baixo), não em grade de BPM nem em qualquer golpe do som todo.
  - A batida não é cíclica. Grade de BPM deixa o corte num ritmo e a música em outro.
  - Golpe de banda larga pega caixa e chimbal.
- Nada calibrado para uma música só. Limiar sempre relativo à própria faixa (percentil 95 dos golpes dela).
- Fluxo de energia em log sem piso iguala o vazamento grave da caixa a um bumbo. Por isso o piso é metade da energia grave mediana da faixa.
- Áudio tirado de um vídeo já editado pode trazer efeitos sonoros e voz da edição anterior. O início automático pula a introdução quando há música suficiente; se a faixa útil for curta, o render avisa.
- Validar em três frentes: o `teste` (seis gêneros sintéticos com gabarito de bumbo e baixo), uma faixa real e uma referência aprovada mantida localmente.

**Tempo e quadros**
- Toda mudança de velocidade (slow, rampa, interpolação de quadros) pode sobrar ou faltar quadro, e a sobra acumula: na 0.7.0 cada clipe em slow ganhava um quadro e o vídeo atrasava até 170 ms em relação à música.
- Cada clipe termina com contagem exata de quadros (`trim=end_frame`). A auditoria mede o corte visível no quadro exato, não só o plano.

**Auditoria do render**
- O JSON do render diz o que foi planejado e não prova nada. Medir no MP4:
  - cortes visíveis na imagem (±1 quadro);
  - cortes no grave do áudio final (±40 ms);
  - loudness (ebur128; comparar com a meta definida para o job, se houver);
  - folha de quadros com uma cruz no centro, olhada de fato.
- Entregar só com esses números, sem afirmar além deles.

**Efeitos sonoros**
- Volume relativo à música, nunca fixo: o pico do efeito fica 8 dB abaixo do nível da música naquele corte. Conferir no MP4 subtraindo a música do mix e medindo o que sobra.
- O ponto que cai no corte é o pico de energia (janela de 20 ms), não a amostra mais alta: num swoosh longo a amostra mais alta chega até 0,2 s antes do que se ouve.
- Swoosh real tem grave: a auditoria de corte no grave feita no mix final cai (8 de 10 na v11) sem que o corte tenha mudado. Medir a sincronia na música, não no mix.
- Pacotes baixados (YouTube) ficam fora do repositório público; o plugin só lê uma pasta local (`sfx_pasta`).

**Efeitos visuais**
- Transições entre clipes com `xfade` (nativo do ffmpeg): cada clipe sobra meia transição antes e depois, é partido em começo, corpo e fim, e o meio da passagem cai no golpe. Conferir o total de quadros (o `teste` cobre).
- Expressões do xfade-easing rodam no ffmpeg comum, mas custam cerca de 50 s por transição em 1080x1920. Por isso: meia resolução, uma por vídeo e `threads=1` no filtro. Elas guardam valores em `st()`/`ld()`, que viram ruído com várias threads (o README deles avisa; aqui saiu ruído antes do ajuste).
- Sobreposição de fundo preto (luz, glitch, film burn) mistura em "tela" em RGB (`gbrp`). Em YUV a mistura mexe na cor.
- Pacotes do YouTube: tirar quadros com texto ("TRANSITION 2") e fundo verde. Formas abstratas podem ser esticadas do 16:9 para o 9:16; cortar o centro perde a luz, que fica nas bordas.

**Escolha do trecho e enquadramento**
- Escolha trechos que mostrem a ação relevante para o briefing; confira a folha de quadros antes de entregar.
- Produto: centralizado, tamanho próximo ao alvo e sem encostar na borda.
- Pessoa: escolha uma janela que mostre o gesto concluído, sem cortar a ação.
- O detector pode confundir reflexos e elementos do cenário com o produto; revise a folha.
- Limite o zoom para preservar a nitidez de fontes em baixa resolução.

**Câmera lenta**
- Moderada (0,7x) e em rampa: entra no golpe em velocidade normal e desacelera.
- Slow forte (0,5x) no gancho cortou o gesto antes de ele acontecer.
- Interpolação por fluxo de movimento (minterpolate) em meia resolução: render de cerca de 30 s no PC, em vez de 11 s.

**Windows e o agente do ChatGPT**
- Rodar `py -B -I` para não gravar `.pyc` nem ler módulos do diretório atual.
- O ffmpeg 9 não tem `-filter_complex_script`: o grafo vai inline, com limite de 30 000 caracteres.
- Validar no PC e no mesmo app que serão usados na entrega, antes de apresentar o resultado.
- Se o script falhar, o agente deve parar e informar o erro.
- O agente deve seguir a receita, usar os pacotes locais e descrever somente o que aparece no resultado do render. Se o script falhar, pare e informe o erro; não o copie nem o contorne em silêncio. O que puder ser decidido no script deve ficar definido nele.

**Repositório**
- Nada de `.pyc`, mídia, links, identificadores ou dados pessoais de clientes no repositório público; use fixtures sintéticas e mantenha referências reais localmente.
- Versão sobe nos dois manifestos (`plugin/plugin.json` e `plugin/.claude-plugin/plugin.json`).
