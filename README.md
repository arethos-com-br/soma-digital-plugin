# Soma Digital — plugin de edição

Plugin para o ChatGPT/Codex desktop e para o Claude que ajuda a equipe da Soma Digital a editar vídeos sociais (Reels, vertical 9:16). Quem usa coloca os brutos numa pasta do Drive, descreve o pedido em linguagem natural e recebe um **draft editável no CapCut**, pronto para revisar. Feito pela [Arethos](https://github.com/arethos-tech).

Status: MVP em validação. O fluxo e a instalação abaixo ainda estão sendo testados do ponto de vista de quem vai usar.

## Fluxo de uso

```mermaid
flowchart TD
    P["Quero criar um vídeo novo"] --> V{"Google Drive e CapCut<br/>habilitados?"}
    V -- "não" --> X["Avisa o que falta e para"]
    V -- "sim" --> E["1. Iniciar vídeo, guiado<br/>cliente, pedido, pastas do Drive"]
    E --> PL["2. Planejar<br/>examina os brutos e as referências"]
    K["Conhecimento<br/>modos, repertório, biblioteca, tendências"] -.-> PL
    PL --> PLANO["Plano curto<br/>trechos, timeline, gancho, efeitos, música, texto"]
    PLANO --> AP{"Plano aprovado?"}
    AP -- "ajustar" --> PL
    AP -- "sim" --> ED["3. Editar<br/>versão recuperável do draft no CapCut"]
    ED --> VF["4. Verificar<br/>mídia, ordem, duração, proporção, texto, áudio"]
    VF --> EN["Entrega<br/>link do draft editável e resumo do que foi aplicado"]
    EN --> RH["Revisão humana no CapCut"]
    RH -- "ajustes" --> ED
    RH -- "aprovado" --> FIM["Exportação e publicação<br/>fora do plugin"]
```

Quem faz o quê em cada conversa:

```mermaid
sequenceDiagram
    actor U as Equipe
    participant C as ChatGPT com o plugin
    participant D as Google Drive
    participant K as CapCut
    U->>C: pedido (pasta, plataforma, duração, modo)
    C->>D: lê os brutos e as referências
    C-->>U: plano para aprovar
    U->>C: aprova
    C->>K: envia os brutos do plano e cria o draft
    C->>K: relê o draft e confere
    C-->>U: link do draft e resumo
    U->>K: revisa, ajusta, exporta
```

A skill `buscar-tendencias` também funciona sozinha: pedido de tendências, consulta das fontes, até 3 sugestões com fonte, data e aplicação ao job.

## Etapas em detalhe

| Etapa | O que faz | Lê | Produz |
|---|---|---|---|
| Conferir | Verifica se Google Drive e CapCut estão habilitados | conectores da conversa | aviso e parada se faltar um |
| 1. Iniciar vídeo (`iniciar-video`) | Acha e examina os brutos e as referências (inclusive em subpastas), deduz cliente, pedido e modo do que o material mostra e confirma tudo de uma vez; pergunta só o que não deduziu | o que quem usa disse, Drive | ficha do cliente e pedido confirmados |
| 2. Planejar (`montar-video`) | Examina brutos e referências, registra só o que observou, consulta o conhecimento e pode sugerir gancho e efeitos | Drive, `references/`, `buscar-tendencias` | plano curto: formato, trechos, timeline, música, texto e, no máximo, uma dúvida |
| Aprovação | Quem usa aprova ou pede ajuste; a aprovação cobre o envio dos brutos ao CapCut | plano | sinal para editar |
| 3. Montar | Monta o draft clipe por clipe, seguindo o plano aprovado, com as funções de pós-edição do plugin do CapCut (sem AI Lab), e mantém uma versão recuperável | plano | draft no CapCut |
| 4. Verificar | Relê o draft e confere mídia, ordem, duração, proporção, texto e áudio | draft | link e resumo; prévia só se foi gerada |
| Revisão humana | Ajustes, exportação e publicação ficam com quem usa | draft | decisão |

## Modos de entrega

Cada pedido usa um único modo.

| Modo | Resultado | Cuidados |
|---|---|---|
| `corte-musical-produto` | Sequência de clipes reais cortada pelo ritmo da música | marcar as batidas antes de cortar; tratar o áudio original dos brutos; gancho nos primeiros segundos |
| `template-tela-dividida` | Dois espaços de vídeo, cada um com duração e enquadramento independentes | ajustes de um lado não alteram o outro; definir o que ocorre quando um clipe acaba antes |

## Conhecimento que o plugin consulta

| Arquivo | Conteúdo | Estado |
|---|---|---|
| `references/modos.md` | os dois modos e seus cuidados | pronto |
| `references/repertorio.md` | transições, efeitos visuais e efeitos sonoros usados | pronto; falta ligar cada item ao efeito equivalente no CapCut |
| `references/biblioteca.md` | templates, ganchos e estruturas com evidência | vazio; só entra o que for testado |
| skill `buscar-tendencias` | o que está em alta e, para clientes de nicho específico, anúncios do nicho | pronto |

## Regras fixas

- Nunca publica. Preserva os originais do Drive.
- Usa só os brutos do pedido: sem banco de imagens, mídia gerada ou imagem genérica.
- Não inventa texto, chamada para ação nem logo; não exporta o vídeo final sem pedido.
- Não usa o AI Lab do CapCut: o corte segue o plano aprovado, não um plano refeito pelo CapCut.
- Respeita o que já foi alterado no CapCut por quem usa.

## Instalar

Requisitos: app desktop do ChatGPT, plugin oficial do [CapCut](https://www.capcut.com/tools/capcut-x-codex) instalado e autorizado, e o conector do Google Drive habilitado.

```bash
codex plugin marketplace add arethos-tech/soma-digital-plugin
```

Depois instale o plugin:

```bash
codex plugin add soma-digital@soma-digital
```

Ou, pelo app: reinicie, abra o diretório de plugins, escolha o marketplace "Soma Digital" e instale. Verificado pela CLI no Windows em 19/10/2026; o caminho pela interface do app ainda não foi testado.

## Instalar no Claude

Claude Code 2.1.275 ou mais novo:

```bash
claude plugin marketplace add arethos-tech/soma-digital-plugin
claude plugin install soma-digital@soma-digital
```

Depois, o CapCut (hoje o plugin oficial dele é só para Codex; não está neste repositório):

1. Adicione o servidor e faça o login pelo `/mcp`: `claude mcp add --transport http capcut_creation https://www.capcut.com/api/external_mcp`.
2. Instale localmente as skills `capcut-upload`, `capcut-stdraft-builder` e `web-collaborative-editing` do pacote oficial (veja a [página do CapCut × Codex](https://www.capcut.com/tools/capcut-x-codex)).
3. Os brutos precisam estar em disco (Google Drive para desktop); o enviador do CapCut não lê direto do conector do Drive.
4. `ffmpeg` no PATH, para examinar quadros e áudio dos brutos (Windows: `winget install Gyan.FFmpeg`).

Detalhes do que muda por ambiente: `plugin/skills/montar-video/references/ambientes.md`. Status: instalação e skills validadas pelo `claude plugin validate`; login no CapCut e montagem pelo Claude ainda não testados de ponta a ponta.

## Usar

Quem usa só grava e coloca os vídeos no Drive; o plugin guia o resto. Abra uma conversa nova e diga o que quer (no Claude, também `/soma-digital:iniciar-video`), por exemplo:

> Quero criar um vídeo novo para um cliente.

A skill `iniciar-video` examina o que está no Drive, mostra o que entendeu sobre o cliente e o pedido, pergunta só o que faltou e segue para o plano. Quem já sabe o que quer pode mandar tudo de uma vez:

> Cliente: loja de moda feminina, público jovem, tom descontraído; destaque: coleção nova. Brutos na pasta Agência e referências na pasta Ref. Reels de 15 segundos para Instagram, corte musical de produto. Me mostra o plano antes de editar.

## Estrutura do repositório

```
.agents/plugins/marketplace.json     catálogo para instalar pelo Codex
plugin/plugin.json                   manifesto
plugin/.claude-plugin/plugin.json      manifesto para o Claude
.claude-plugin/marketplace.json      catálogo para instalar pelo Claude
plugin/skills/iniciar-video/         início guiado (cliente, pedido, pastas)
plugin/skills/montar-video/          plano, montagem e verificação (SKILL.md) e references/
plugin/skills/buscar-tendencias/     tendências e anúncios do nicho
```

Não há vídeos, links de Drive nem dados pessoais neste repositório.
