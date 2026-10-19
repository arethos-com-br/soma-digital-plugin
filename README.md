# Soma Digital — plugin de edição

Plugin para o ChatGPT/Codex desktop que ajuda a Soma Digital a editar vídeos sociais (Reels, vertical 9:16): a usuária coloca os brutos no Drive, descreve o job e recebe um draft editável no CapCut. Feito pela [Arethos](https://github.com/arethos-tech).

Status: MVP em validação. A instalação e o fluxo abaixo ainda estão sendo testados do ponto de vista de quem vai usar.

## O que faz

- Edita os brutos reais de uma pasta do Drive; não gera vídeo do zero.
- Dois modos, um por job: `corte-musical-produto` (clipes cortados pelo ritmo da música) e `template-tela-dividida` (dois vídeos com duração e enquadramento independentes).
- Aplica o repertório de efeitos e transições da Soma e uma biblioteca de templates e ganchos.
- Propõe edições e aponta o que está em alta (templates, áudios, formatos).
- Nunca publica: entrega o link de um draft editável e a Soma revisa no CapCut.

## Instalar

Requisitos: app desktop do ChatGPT, plugin oficial do [CapCut](https://www.capcut.com/tools/capcut-x-codex) instalado e autorizado, e o conector do Google Drive habilitado.

```bash
codex plugin marketplace add arethos-tech/soma-digital-plugin
```

Reinicie o app, abra o diretório de plugins, escolha o marketplace "Soma Digital" e instale.

## Usar

Abra uma conversa nova e escreva como falaria com uma pessoa, por exemplo:

> Quero um Reels de 15 segundos com os brutos da pasta Agência. É um corte musical de produto para Instagram. Usa as referências da pasta Referências e me mostra o plano antes de editar.

1. O plugin lê o pedido e pergunta só o que faltar.
2. Examina os brutos e as referências e mostra um plano curto.
3. Com a sua aprovação, cria o draft no CapCut e devolve o link.
4. Você revisa e ajusta no CapCut.

## Conteúdo

| Caminho | O quê |
|---|---|
| `plugin/skills/editar-video` | Fluxo completo: entender, planejar, editar, verificar |
| `plugin/skills/editar-video/references` | Modos de entrega, repertório de efeitos e biblioteca de templates e ganchos |
| `plugin/skills/trends` | Tendências, em separado porque se pede sozinha |

Não há vídeos, links de Drive nem dados de cliente neste repositório.
