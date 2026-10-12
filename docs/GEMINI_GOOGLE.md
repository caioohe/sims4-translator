# Gemini e Google Translate — integração e diagnóstico

Esta atualização parte de `1df8ee2` na branch de trabalho, preservando as correções
anteriores de DeepL, arquivos e recuperação de progresso. Não altera mods pessoais.

## Usar Gemini no Windows

1. Extraia a pasta inteira do novo ZIP e abra `Sims4Translator.exe`.
2. Em **Options → Gemini and Google** (Opções → Gemini e Google), clique em
   **Get API key / Obter chave de API** para abrir https://aistudio.google.com/apikey.
3. Crie/use uma chave de um projeto **Free Tier**, se quiser manter uso gratuito.
   A disponibilidade e a cota pertencem ao projeto; não são inferidas da assinatura
   de estudante no app Gemini. O tradutor não ativa cobrança nem troca de projeto.
4. Cole a chave no campo local. Ela fica mascarada na tela e é gravada em
   `prefs/config.xml`, como a chave DeepL existente. Esse arquivo é ignorado pelo git.
   Alternativa: configure `GEMINI_API_KEY` no Windows antes de iniciar o app; a
   variável de ambiente tem prioridade e não é copiada para as preferências.
5. Modelo padrão: `gemini-3.8-flash`. O campo é editável. Se aparecer 404, selecione
   um ID que sua conta realmente disponibiliza. Não há troca automática de modelo.
6. Configure os idiomas de origem/destino e clique em **Test translation**.
   Isso envia somente `Hello {0.SimFirstName}!`, sem ler/enviar um mod pessoal.
7. Abra seu pacote, escolha **Gemini** na tradução em lote e, para poupar chamadas,
   use **Multiline translation**. Para continuar após uma falha, escolha a opção
   que exclui strings já validadas.

Nunca publique a chave nem envie-a em mensagens, screenshots, logs ou issues.
A chave não vai no ZIP/Actions. A integração não verifica automaticamente o plano
Free/Paid do projeto: **uma chave de projeto pago pode gerar cobrança**. No Free Tier,
os limites e o uso do conteúdo para melhoria de produtos seguem as regras Google.
Nenhum fluxo OAuth/assinatura Google ou ponte de navegador é usado nesta integração.

## Contrato da API

`utils/gemini.py::translate_gemini` usa `requests.post` diretamente no endpoint
oficial `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`.
A chave vai no header `x-goog-api-key`, nunca na URL. Não adicionamos SDK nem proxy.

`systemInstruction` orienta tradução fiel ao jogo, distingue PT-BR de PT-PT,
trata as strings como dados e exige preservar os marcadores. `generationConfig`
usa JSON (`responseMimeType` e `responseSchema`), uma resposta candidata e saída
limitada. A resposta só é aceita com `finishReason == STOP`, JSON válido, IDs
inteiros únicos e completos, conteúdo não vazio quando a origem não é vazia e
todos os tokens protegidos corretos. Respostas SAFETY/MAX_TOKENS, prompt bloqueado,
IDs repetidos/trocados/ausentes e tokens alterados são rejeitados integralmente.
O app não modifica filtros de segurança Google nem repete uma resposta bloqueada.

As strings têm IDs por chamada e respostas fora de ordem são mapeadas por ID,
nunca por posição de quebra de linha. Cada chamada contém até 50 strings e 16.000
caracteres de origem (com limite adicional de 256 KiB do JSON protegido). A fila
Gemini tem uma chamada ativa e intervalo local de 6 segundos, até dois retries
para 429/5xx/conexão/timeout, com backoff, Retry-After e RetryInfo. Cota diária
identificável por QuotaFailure não é repetida. Esperas de servidor >60s interrompem
o lote e mantêm cooldown para uma retomada posterior. Esses números são políticas
conservadoras do app, **não as cotas oficiais da sua conta**.

Timeout: conexão 5s/leitura 60s por inatividade. Stop cancela a espera/retry;
não aborta imediatamente uma chamada HTTP em andamento. Repetir após timeout
pode consumir novamente a cota se o servidor já processou a primeira chamada.
Ao terminar um lote, aplicação de registros e checkpoints ocorre no thread Qt.

## Proteção TS4 e gênero

`utils/sims_tokens.py::protect_sims/restore_sims` percorre chaves balanceadas:

- Variáveis como `{0.SimFirstName}`, `{1.Number}` e blocos desconhecidos/nested
  são protegidos integralmente, incluindo seu conteúdo e letras.
- `{M0.He likes {1.SimFirstName}}` protege o prefixo `{M0.`, a variável interna
  e o fechamento `}`, deixando `He likes` visível para tradução. O mesmo vale
  para F e para ramos aninhados. Limite defensivo: 32 níveis.
- Tags `<b>`, `</b>`, `<font ...>`, quebras reais e escapes `\n`, `\r`, `\t`
  são protegidos. Chaves soltas também são preservadas.
- Marcadores não colidem com texto que já usa seu prefixo; cada marcador deve
  voltar uma vez e na ordem original. Chaves/tags/quebras inventadas são rejeitadas.

Exemplo de teste simulado:
`{M0.He likes {1.SimFirstName}}{F0.She likes {1.SimFirstName}}`
→ `{M0.Ele gosta de {1.SimFirstName}}{F0.Ela gosta de {1.SimFirstName}}`.

As regras Gemini são deliberadamente conservadoras: uma tradução que reordena
variáveis pode ser rejeitada mesmo quando linguisticamente aceitável. A integridade
de tokens não comprova qualidade semântica. Revise termos próprios, humor e gênero
no jogo. DeepL/Google/MyMemory mantêm a proteção anterior; o novo parser de gênero
é específico do Gemini, evitando alterar de forma ampla os provedores existentes.

## Diagnóstico do 429 Google

**Confirmado no código:** Google usa `translate.google.com/m`, uma página HTML
para uso web, sem API Cloud Translation e sem contrato de cota/estabilidade para
este cliente. Mesmo após a fila serial do primeiro patch, chamadas Google não
tinham intervalo próprio; o retry antigo da toolbar foi substituído pela fila
comum, que não fazia retry Google. Isso permitia sequências rápidas de GETs.

**Hipótese mais provável para o relato:** limitação do serviço web por frequência
ou condições de tráfego da rede. Não houve trace da conexão do usuário. Uma única
requisição sintética (`Hello world`) neste ambiente terminou em **ReadTimeout**;
portanto **não reproduzimos o 429 real do usuário** e não afirmamos remover o
bloqueio do lado Google. Não foram feitas tentativas de contornar o timeout.

Correções em `utils/google_translate.py` e `utils/http_policy.py`:

- Intervalo mínimo de 2s, configurável até 60s em Options, compartilhado entre
  batch/editor/testes na mesma instância. Uma chamada ativa por provedor.
- Uma tentativa adicional para 429/5xx/conexão/timeout, espera inicial de pelo
  menos 15s com jitter e respeito ao Retry-After. 403 não é repetido.
- Após 429 persistente, pausa do lote e cooldown de pelo menos 60s. Um novo clique
  não elimina esse cooldown. O app preserva as traduções concluídas.
- HTML de captcha/tráfego incomum com status 200 é rejeitado e pausa a tradução.
  Não resolve desafios, troca IP, usa proxies ou muda para outro endpoint oculto.
- Parser HTML no lugar de regex que parava no primeiro `<`: suporta spans internos
  e entidades; página de consentimento/login ou estrutura alterada não vira tradução.

Isso mitiga tráfego excessivo e melhora recuperação, **não garante que Google
pare de retornar 429**. Use Gemini/DeepL ou uma API Cloud Translation autorizada
se o bloqueio continuar. Não há troca automática de provedor nem envio surpresa.

## Validação

A suíte local inclui mocks para Gemini/Google: erros HTTP, retries e RetryInfo,
cota diária, timeout/conexão, cancelamento, corrupção de tokens e IDs, JSON
inválido/duplicado, gênero/Unicode/aninhamento, PT-BR/PT-PT, parser HTML, cooldown e
configuração/teste assíncrono na interface. Os testes anteriores de DeepL e pacotes
continuam presentes. Resultados em `VALIDATION.md` e no run final do PR.

Não há chave Gemini neste ambiente. A tradução ao vivo e a qualidade real dependem
do teste local com a sua chave; **não foram declaradas como comprovadas**. Build
Windows e testes com mocks não garantem que uma conta/modelo particular tenha cota.

## Fontes oficiais

- https://ai.google.dev/api/generate-content
- https://ai.google.dev/gemini-api/docs/structured-output
- https://ai.google.dev/gemini-api/docs/api-key
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/rate-limits
