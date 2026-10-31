# Soma Digital — plugin de edição

Ajuda a planejar e montar vídeos sociais a partir dos brutos fornecidos ou referenciados pelo usuário. O fluxo principal entrega um **draft editável no CapCut**; o MP4 local fica disponível quando pedido. Feito pela [Arethos](https://github.com/arethos-com-br).

Os arquivos desta versão contêm instruções e scripts, sem vídeos, links de Drive ou dados pessoais de clientes.

## O que vem no plugin

| Parte | Para que serve |
|---|---|
| `iniciar-video` | Localiza e examina brutos e referências; confirma cliente, pedido e arquivos. |
| `montar-video` | Apresenta um plano e monta um draft no CapCut; pode renderizar MP4 local quando pedido. |
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

## Primeiro vídeo: draft no CapCut

O fluxo principal usa o plugin oficial [CapCut × Codex](https://www.capcut.com/tools/capcut-x-codex), instalado e autorizado no Codex. Conecte o Google Drive se os brutos ou referências estiverem lá. Para o upload, os arquivos escolhidos também precisam estar numa pasta local acessível; sincronize a pasta do Drive no PC. Instalar o Soma Digital não instala nem autentica esses serviços.

Em uma conversa nova, informe o pedido e onde estão os brutos e as referências. Exemplo:

> Quero montar um draft editável no CapCut para um Reels de 12 segundos. Os brutos estão em [pasta do Drive] e as referências em [pasta de referências]. Mostre o plano e espere minha aprovação antes de montar.

Revalide e entregue o draft final para o usuário revisar; não é necessário exportar nem publicar o vídeo.

O aplicativo **CapCut Desktop** é separado do plugin e da conexão MCP. Instale-o pelo [site oficial](https://www.capcut.com/resource/capcut-for-windows) se ela quiser abrir ou ajustar o draft nesse aplicativo; a ausência do app, sozinha, não confirma falha do MCP. A disponibilidade pode variar por versão do ChatGPT, conta e região, conforme a [página oficial](https://www.capcut.com/tools/capcut-x-codex).

## MP4 local (alternativa, quando pedido)

Esta rota não exige conectores do Drive ou CapCut. Requer Python 3, `ffmpeg` e `ffprobe` no `PATH`, além dos brutos e da música em uma pasta acessível. O script usa apenas a biblioteca padrão do Python; não requer pacotes `pip`.

Se ainda não tiver Python, instale o [Python Install Manager](https://www.python.org/downloads/windows/) oficial. Para o FFmpeg, abra o PowerShell e rode:

```powershell
winget install -e --id Gyan.FFmpeg
```

Ou escolha um build para Windows na [página oficial de download do FFmpeg](https://www.ffmpeg.org/download.html). Depois, feche e reabra o PowerShell e confira:

```powershell
py --version
ffmpeg -version
ffprobe -version
```

Em uma conversa nova, peça a rota local e indique os caminhos. Exemplo:

> Quero um Reels de 15 segundos no modo corte musical. Os brutos estão em `C:/Users/SeuUsuario/Videos/Projeto/Brutos` e a música em `C:/Users/SeuUsuario/Videos/Projeto/musica.mp3`. Mostre o plano e espere minha aprovação antes de renderizar o MP4 local.

Confirme o pedido e apresente um plano. Renderize só depois da aprovação. Se não acessar os arquivos ou um comando falhar, informe o bloqueio; não troque de rota nem substitua o script em silêncio.

## Instalar no Claude Code (opcional)

O repositório também inclui o plugin para Claude Code. No Windows, Claude Code pode rodar nativamente ou no WSL; a rota CapCut nativa exige Git for Windows para a ferramenta Bash. Com Claude Code 2.1.292 ou mais recente, instale pelo PowerShell ou terminal:

```bash
claude plugin install soma-digital --marketplace arethos-com-br/soma-digital-plugin
```

Para a rota CapCut no Claude Code, há configuração adicional do MCP e das skills oficiais do CapCut; veja [`references/ambientes.md`](plugin/skills/montar-video/references/ambientes.md) e o [guia oficial de instalação de plugins](https://code.claude.com/docs/en/plugins/install).

## Limites

- Use os brutos do pedido. Busque stock ou gere imagens com prompts detalhados só se o usuário pedir ou se for oportuno.
- Não invente texto, chamada para ação nem logo: o usuário que instrui a edição fornece esse conteúdo.
- Preserve os originais. Aprovação e revisão final ficam com o usuário. Exportar e publicar o vídeo também é responsabilidade dele: não pergunte sobre isso nem tente fazê-lo.

Regras completas: [`montar-video/SKILL.md`](plugin/skills/montar-video/SKILL.md).

## Validação pendente

Valide a versão atual no computador do usuário. Os testes registrados no Windows cobrem só versões anteriores (rota local 0.5.0 e CapCut 0.4.2).

1. Confirme na conversa o acesso ao CapCut e ao Drive.
2. Peça ao usuário os arquivos do primeiro vídeo.
3. Conclua um draft com esses arquivos.
