# soma-digital-plugin

Plugin público de edição da Soma Digital (ChatGPT/Codex e Claude). O que é instalado fica em `plugin/`; este arquivo e o `README.md` são para quem desenvolve. Sem dados de cliente aqui.

## Aprendizados (não repetir)

Erros que já aconteceram, com a regra que os evita. Leia antes de mexer no `montar-video`.

**Critério vem da cliente, não de mim**
- Antes de mudar estética ou ritmo, olhe os exemplos e referências da cliente e meça neles. Exemplos: o enquadramento do produto foi tirado do A02 (centro, cerca de metade da largura); os pontos de corte foram conferidos com os cortes que ela fez no A01.
- Mudança feita sem ler o material dela já foi desfeita duas vezes (templates do CapCut, 0.4.5 → 0.4.6).

**Corte na música**
- Corte no grave (bumbo e baixo), não em grade de BPM nem em qualquer golpe do som todo.
  - A batida não é cíclica. Grade de BPM deixa o corte num ritmo e a música em outro.
  - Golpe de banda larga pega caixa e chimbal.
- Nada calibrado para uma música só. Limiar sempre relativo à própria faixa (percentil 95 dos golpes dela).
- Fluxo de energia em log sem piso iguala o vazamento grave da caixa a um bumbo. Por isso o piso é metade da energia grave mediana da faixa.
- Áudio tirado de um vídeo já editado não é a música: traz os efeitos sonoros e a voz daquela edição. O A01 abre com 3,5 s de efeito de transição e voz antes da batida, e o Reels saiu com um "glitch" sem nada na tela. O início automático pula até a batida em sequência; se a faixa útil for mais curta que o vídeo, o render avisa em vez de esconder.
- Validar em três frentes: o `teste` (seis gêneros sintéticos com gabarito de bumbo e baixo), uma faixa real e os cortes de um exemplo da cliente.

**Tempo e quadros**
- Toda mudança de velocidade (slow, rampa, interpolação de quadros) pode sobrar ou faltar quadro, e a sobra acumula: na 0.7.0 cada clipe em slow ganhava um quadro e o vídeo atrasava até 170 ms em relação à música.
- Cada clipe termina com contagem exata de quadros (`trim=end_frame`). A auditoria mede o corte visível no quadro exato, não só o plano.

**Auditoria do render**
- O JSON do render diz o que foi planejado e não prova nada. Medir no MP4:
  - cortes visíveis na imagem (±1 quadro);
  - cortes no grave do áudio final (±40 ms);
  - loudness (ebur128; os exemplos dela ficam em cerca de −14,7 LUFS);
  - folha de quadros com uma cruz no centro, olhada de fato.
- Entregar só com esses números, sem afirmar além deles.

**Escolha do trecho e enquadramento**
- "Mais movimento" escolhe a mão girando o produto perto da câmera.
  - Produto: centralizado, tamanho perto do alvo, sem encostar na borda.
  - Pessoa: a janela que termina no gesto concluído (pôs o óculos e olhou para a câmera).
- O detector de produto confunde lente prateada com asfalto. Produto encostado na borda é evitado, mas revise a folha.
- Zoom até 1,35: mais que isso perde nitidez nos brutos de 720 px.

**Câmera lenta**
- Moderada (0,7x) e em rampa: entra no golpe em velocidade normal e desacelera.
- Slow forte (0,5x) no gancho cortou o gesto antes de ele acontecer.
- Interpolação por fluxo de movimento (minterpolate) em meia resolução: render de cerca de 30 s no PC, em vez de 11 s.

**Windows e o agente do ChatGPT**
- Rodar `py -B -I` para não gravar `.pyc` nem ler módulos do diretório atual.
- O ffmpeg 9 não tem `-filter_complex_script`: o grafo vai inline, com limite de 30 000 caracteres.
- Testar no PC, com o mesmo app que a cliente usa, antes de mostrar.
- Se o script falhar, o agente deve parar e informar o erro. Ele já copiou o script para contornar uma falha sem avisar.

**Repositório**
- Nada de `.pyc` nem de dado de cliente.
- Versão sobe nos dois manifestos (`plugin/plugin.json` e `plugin/.claude-plugin/plugin.json`).
