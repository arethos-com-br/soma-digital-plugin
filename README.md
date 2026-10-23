# Soma Digital — plugin de edição

Ajuda a planejar e montar vídeos sociais a partir dos brutos da equipe. A saída padrão é um **MP4 renderizado no computador**; um draft editável no CapCut é uma rota opcional, quando pedida. Feito pela [Arethos](https://github.com/arethos-com-br).

Os arquivos desta versão contêm instruções e scripts, sem vídeos, links de Drive ou dados pessoais de clientes.

**Estado:** MVP em validação. A versão atual (0.10.3) ainda precisa de uma primeira instalação e execução no PC de uso.

## O que vem no plugin

| Parte | Para que serve |
|---|---|
| `iniciar-video` | Localiza e examina brutos e referências; confirma cliente, pedido e arquivos. |
| `montar-video` | Apresenta um plano, renderiza um MP4 local ou, se pedido, monta e confere um draft no CapCut. |
| `buscar-tendencias` | Traz até três tendências e anúncios do nicho, com fonte e data. |
| `montar-video/references/` | Modos de edição, requisitos por ambiente e repertório da Soma. |
| `montar-video/receitas/` e `scripts/video_local.py` | Receitas de edição e render local com FFmpeg. |

## Instalar no Windows — Codex desktop

É preciso ter o app desktop do ChatGPT com Codex e o [Codex CLI](https://developers.openai.com/codex/cli). No PowerShell, adicione o marketplace público:

```powershell
codex plugin marketplace add arethos-com-br/soma-digital-plugin
codex plugin marketplace list
```

O primeiro comando registra o catálogo; a instalação termina no app, conforme o [guia de marketplaces do Codex](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli). Feche e reabra o ChatGPT, abra **Plugins Directory**, escolha o marketplace **Soma Digital** e instale o plugin. Depois, inicie uma conversa nova no Codex com o plugin habilitado.

## Primeiro vídeo: MP4 local

Esta é a rota padrão e não exige conectores do Drive ou do CapCut. Requer Python 3, `ffmpeg` e `ffprobe` no `PATH`, além dos brutos e da música em uma pasta que o Codex consiga acessar. Se os arquivos estão no Drive, sincronize essa pasta no PC. O plugin usa a biblioteca padrão do Python; não requer pacotes `pip`.

Se ainda não tiver Python, instale o [Python Install Manager](https://www.python.org/downloads/windows/) oficial, que instala a versão estável atual. Para instalar o FFmpeg, abra o PowerShell e rode:

```powershell
winget install -e --id Gyan.FFmpeg
```

Se preferir instalar o FFmpeg manualmente, escolha um build para Windows indicado na [página oficial de download](https://www.ffmpeg.org/download.html). Depois da instalação, feche e reabra o PowerShell.

Confira no PowerShell:

```powershell
py --version
ffmpeg -version
ffprobe -version
```

Em uma conversa nova, informe o pedido e o caminho local. Exemplo:

> Quero um Reels de 15 segundos no modo corte musical. Os brutos estão em `C:/Users/SeuUsuario/Videos/Projeto/Brutos` e a música em `C:/Users/SeuUsuario/Videos/Projeto/musica.mp3`. Mostre o plano e espere minha aprovação antes de renderizar o MP4 local.

O plugin confirma o que entendeu, apresenta o plano e só renderiza depois da aprovação. Se não conseguir acessar os arquivos ou algum comando falhar, deve informar o bloqueio; não substitui o script em silêncio.

## Draft editável no CapCut

Peça explicitamente a rota CapCut. Ela exige o [plugin oficial do CapCut](https://www.capcut.com/tools/capcut-x-codex) instalado e autorizado no Codex; conecte o Google Drive quando os arquivos ou referências estiverem lá. Aprove o plano antes do envio dos brutos. O draft precisa de revisão humana no editor; o plugin não publica nem exporta o vídeo final automaticamente.

## Instalar no Claude Code (opcional)

O repositório também inclui o plugin para Claude Code. No Windows, Claude Code pode rodar nativamente ou no WSL; a rota CapCut nativa exige Git for Windows para a ferramenta Bash. Com Claude Code 2.1.292 ou mais recente, instale pelo PowerShell ou terminal:

```bash
claude plugin install soma-digital --marketplace arethos-com-br/soma-digital-plugin
```

Para a rota CapCut no Claude Code, há configuração adicional do MCP e das skills oficiais do CapCut; veja [`references/ambientes.md`](plugin/skills/montar-video/references/ambientes.md) e o [guia oficial de instalação de plugins](https://code.claude.com/docs/en/plugins/install).

## Limites

- Usa os brutos do pedido; não busca stock nem gera imagens genéricas.
- Não inventa texto, chamada para ação ou logo.
- Preserva os originais. Aprovação, revisão final, exportação e publicação ficam com quem usa.

## Validação pendente

O histórico registra testes no Windows para versões anteriores (rota local 0.5.0 e CapCut 0.4.2). Isso não confirma a instalação nem a execução da versão atual no PC de uso. A primeira validação deve confirmar os três requisitos no PowerShell e concluir um vídeo de amostra com arquivos acessíveis naquela máquina.
