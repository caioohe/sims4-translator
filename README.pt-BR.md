<p align="center"><a href="README.md">English</a> · <strong>Português (Brasil)</strong></p>

<p align="center">
  <img src="docs/assets/banner.svg" alt="The Sims 4 Translator — fork de confiabilidade" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licen%C3%A7a-MIT-68dbc2" alt="Licença MIT"></a>
  <img src="https://img.shields.io/badge/plataforma-Windows_10%2F11-3277bb" alt="Windows 10 e 11">
  <img src="https://img.shields.io/badge/Python-3.12_%7C_3.14-3277bb" alt="Python 3.12 e 3.14">
  <a href="https://github.com/caioohe/sims4-translator/pull/1"><img src="https://img.shields.io/badge/desenvolvimento-em_revis%C3%A3o-e6b85c" alt="Desenvolvimento em revisão"></a>
</p>

<p align="center">
  <a href="#baixar-e-executar">Download</a> ·
  <a href="#tradutores-disponíveis">Tradutores</a> ·
  <a href="#como-traduzir-um-mod">Como usar</a> ·
  <a href="#documentação-e-validação">Documentação</a> ·
  <a href="https://github.com/caioohe/sims4-translator/issues">Relatar problema</a>
</p>

Um editor de traduções de mods `.package` do **The Sims 4**, com dicionários reutilizáveis, exportação de traduções e integração com serviços de tradução automática.

Este fork de **caioohe** deriva de [voky1/sims4-translator](https://github.com/voky1/sims4-translator). O foco é melhorar o tratamento de falhas, preservar a estrutura dos textos e reduzir a perda de progresso em mods grandes.

> **Versão em revisão:** as melhorias estão na branch [`fix/translation-reliability`](https://github.com/caioohe/sims4-translator/tree/fix/translation-reliability), no [PR #1](https://github.com/caioohe/sims4-translator/pull/1). A branch `main` ainda contém a base original. Nenhum merge foi feito automaticamente.

## O que mudou neste fork

- **Gemini e Microsoft Translator:** APIs oficiais, tradução em lotes e botões de teste nas opções.
- **Proteção do texto do jogo:** validação de variáveis, tags e escapes; Gemini/Microsoft traduzem o texto visível dos ramos de gênero `{M0...}` e `{F0...}` preservando sua estrutura.
- **Falhas de rede e limites:** timeouts, tentativas limitadas e espera orientada por `Retry-After` nos provedores implementados. Um erro persistente interrompe a tradução.
- **Recuperação de progresso:** checkpoints dos lotes concluídos, com retomada de registros compatíveis ao reabrir o pacote.
- **Arquivos `.package` e STBL:** correções documentadas de escrita, backup, cache e preservação de recursos.
- **Opções organizadas:** provedores na aba Geral, chaves mascaradas, salvamento ao fechar Opções e tamanho de lote configurável.

As funções originais de dicionários, tradução manual, exportação para um pacote separado e finalização no mod continuam disponíveis. Consulte a [auditoria](docs/AUDIT.md) para os problemas demonstrados e as limitações de cada correção.

## Baixar e executar

1. Abra [GitHub Actions](https://github.com/caioohe/sims4-translator/actions/workflows/ci.yml) e selecione uma execução **bem-sucedida** da branch `fix/translation-reliability`.
2. Na seção **Artifacts**, baixe **Sims4Translator-Windows**. É necessário estar conectado ao GitHub.
3. Extraia **todo o ZIP** para uma pasta com permissão de escrita.
4. Abra **`Sims4Translator.exe`**.

Não copie apenas o executável: mantenha `_internal`, `prefs` e `fonts` junto dele. Os artifacts ficam disponíveis por **14 dias**; ainda não existe uma release estável deste fork.

**Build validado das integrações atuais:** [execução #5](https://github.com/caioohe/sims4-translator/actions/runs/38183900356), código `eecc409`.

## Tradutores disponíveis

| Serviço | Integração | O que configurar |
| --- | --- | --- |
| **Microsoft Translator** | API oficial Azure Translator v3 | Chave e região do recurso; escolha **F0** para a franquia gratuita |
| **Gemini** | API oficial Google `generateContent` | Chave do AI Studio e modelo disponível no seu projeto |
| **DeepL** | API oficial, com lotes nativos | Chave **DeepL API** Free ou paga |
| **Google Translate** | Página web não oficial | Sem chave; intervalo ajustável, sujeito a bloqueios e alterações do site |
| **MyMemory** | Serviço MyMemory | Sem chave na integração atual; sujeito às cotas do serviço |

As franquias e a disponibilidade pertencem a cada serviço. Uma assinatura do aplicativo Gemini ou do tradutor web DeepL não equivale à franquia de suas APIs. Este programa não cria contas, não ativa faturamento e não contorna limites com proxies ou rotação de IP.

### Configuração rápida

Em **Opções → Geral**, selecione os idiomas de origem e destino e configure o provedor:

- **Microsoft:** informe a chave e a região exata do recurso. Para **Brazil South**, use `brazilsouth`; para um recurso **Global**, deixe a região vazia. [Guia completo](docs/MICROSOFT.md).
- **Gemini:** informe a chave e escolha um modelo. Use **Testar tradução** antes de iniciar um mod grande. [Guia e investigação do Google](docs/GEMINI_GOOGLE.md).
- **DeepL:** informe sua chave de API. O programa identifica o endpoint Free pelas chaves terminadas em `:fx`.

Feche as Opções para salvar. Gemini e Microsoft aparecem na lista de tradutores quando uma chave está configurada, localmente ou por variável de ambiente. Gemini aceita `GEMINI_API_KEY`; Microsoft aceita
`AZURE_TRANSLATOR_KEY` e `AZURE_TRANSLATOR_REGION`.

**Textos por lote:** de 1 a 100, padrão 50, no modo de várias linhas para Gemini/Microsoft. DeepL fica limitado a 50. O limite de caracteres continua valendo: textos longos podem gerar lotes menores. Lotes maiores não garantem maior velocidade.

## Como traduzir um mod

1. Trabalhe com uma cópia do arquivo `.package` e abra-a no programa.
2. Confira os idiomas e selecione o tradutor automático.
3. Traduza um trecho pequeno e revise nomes, sentido e variáveis antes de processar tudo.
4. Salve o dicionário para reutilizar as traduções em versões futuras do mod.
5. Exporte a tradução para um `.package` separado ou finalize no mod, conforme seu fluxo.
6. Confira o pacote no Sims 4 Studio e teste no jogo.

### Se a tradução parar

- **429:** limite de frequência ou cota. Aguarde e confira o uso no painel do provedor.
- **503:** indisponibilidade do serviço ou falha de conexão reportada pelo adaptador. Tente novamente mais tarde.
- **DeepL 456:** cota de tradução esgotada; repetir o pedido não repõe a franquia.
- **Resposta inválida:** o lote não é aplicado quando faltam resultados ou os tokens protegidos são alterados.

Os lotes anteriores permanecem aplicados. A recuperação considera o caminho do pacote, texto original e idiomas; não substitui o dicionário nem o arquivo final. Veja [como retomar um mod grande](docs/WINDOWS.md#retomar-um-mod-grande).

## Documentação e validação

| Documento | Conteúdo |
| --- | --- |
| [Auditoria técnica](docs/AUDIT.md) | Problemas confirmados, arquivos afetados e comparação com Wisdom |
| [Gemini e Google](docs/GEMINI_GOOGLE.md) | Proteção de tokens, integração Gemini e investigação do HTTP 429 |
| [Microsoft e opções](docs/MICROSOFT.md) | Configuração Azure, tamanho dos lotes e persistência de chaves |
| [Windows](docs/WINDOWS.md) | Executar o código, compilar, testar e recuperar progresso |
| [Resultados de validação](docs/VALIDATION.md) | Evidências e limitações dos testes |

**146 testes passaram no Windows com Python 3.12 e 3.14**, e o build PyInstaller foi aprovado na [execução #5](https://github.com/caioohe/sims4-translator/actions/runs/38183900356). Os testes usam HTTP simulado e pacotes sintéticos, sem credenciais reais.

Isso não certifica a qualidade de tradução de cada modelo, o acesso à sua conta, todas as variantes de mods nem o resultado no jogo. Traduções reais precisam de revisão; os bloqueios do Google web continuam fora do controle do programa.

## Desenvolver

Windows 10/11 de 64 bits; Python **3.12 ou 3.14** de 64 bits. No PowerShell:

```powershell
git clone --branch fix/translation-reliability https://github.com/caioohe/sims4-translator.git
cd sims4-translator
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

Para executar os testes:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:QT_QPA_PLATFORM
```

O Actions usa runners padrão `windows-latest`, cache de dependências e um build após os testes. O [guia Windows](docs/WINDOWS.md) contém o comando de compilação.

**Arquivos locais:** `prefs/config.xml` contém chaves em texto, apesar da máscara na interface. Não publique esse arquivo, `prefs/recovery/`, dicionários nem mods pessoais. Para relatar um bug, inclua mensagem, versão e passos para reproduzir; remova credenciais dos prints e logs.

## Idiomas da interface

As traduções da interface ficam em `prefs/interface/`. Um novo idioma pode ser adicionado com um arquivo XML nessa pasta. O fork inclui os novos controles em PT-BR.

## Créditos e licença

- **Projeto original:** [voky1 / The Sims 4 Translator](https://github.com/voky1/sims4-translator).
- **Manutenção deste fork:** [caioohe](https://github.com/caioohe).
- **Inspiração original:** [xTranslator](https://www.nexusmods.com/skyrimspecialedition/mods/134).
- **Roboto:** [Apache 2.0](fonts/LICENSE-Roboto.txt).
- **JetBrains Mono:** [SIL Open Font License 1.1](fonts/LICENSE-JetBrains.txt).

Código sob [licença MIT](LICENSE), preservando a licença e os créditos originais. Projeto comunitário, sem afiliação com EA/Maxis ou com os provedores de tradução.
