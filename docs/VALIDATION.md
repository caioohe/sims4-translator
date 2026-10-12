# Validação

- Base upstream: 606ca092b97b9ecd964363dfa38998d2558c3a01.
- Ambiente local: Linux, Python 3.12.14, PySide6 6.12.0, requests 2.34.2, pytest 9.1.1.
- Comando: `QT_QPA_PLATFORM=offscreen python -m pytest -q`.
- Resultado local: **114 passed**, sem rede/API real (aproximadamente 0,6s).
- Sintaxe: `python -m compileall -q main.py singletons storages packer windows utils`.
- `git diff --check`: sem erros.

Também executamos os 7 testes binários sobre um checkout isolado e inalterado do
upstream: **6 falham e 1 passa**. As falhas demonstram truncamento silencioso,
perda do arquivo alvo em exceção, remoção de STBL destino e recursos vazios,
cache incompleto após search_stbl e backup que move a origem. No código corrigido,
os mesmos testes passam. Nenhum arquivo pessoal participou dessa reprodução.

Cobertura: 429/5xx e backoff/Retry-After, 456/403 sem retry, connection error,
timeout, cancelamento, concorrência serializada, lote DeepL nativo, contagem e XML
inválidos, tamanho JSON, placeholders/Unicode, MyMemory/Google, Qt main thread e
progresso após falha, checkpoint atômico, DBPF/STBL, finalização, backups e startup.

CI remoto: workflow no PR testa Windows/Python 3.12 e 3.14 e compila com PyInstaller
em Python 3.12, sem chave/API/mods privados. Consulte o run vinculado ao PR para
resultado e artifact exatos. Build aprovado não comprova tradução real nem uso no jogo.

Não validado com serviço real: chave/conta DeepL, cota/429 do usuário, tradução
semântica, comportamento de gênero, mudanças atuais do Google HTML, mods reais e jogo.

## Atualização Gemini + Google

114 testes locais aprovados. Gemini é testado somente com HTTP simulado; sem chave
real. Google usa mocks e uma tentativa real sintética terminou em ReadTimeout.
A atualização protege gênero, tokens, IDs e respostas incompletas, acrescenta
controle de frequência Google e botão de teste Gemini. Consulte o PR para o run
Windows correspondente ao commit final; o run anterior não valida código novo.

Microsoft Translator, configurações na aba Geral e salvamento das chaves: [MICROSOFT.md](MICROSOFT.md).

## Microsoft, lotes e persistência — código eecc409

146 testes passaram no Windows/Python 3.12 e 3.14; build PyInstaller aprovado na
[execução #5](https://github.com/caioohe/sims4-translator/actions/runs/38183900356).
Inclui HTTP Microsoft simulado, preservação de gênero/tokens, lotes de 100 textos
Gemini/Microsoft e reabertura de configurações. Não confirma autenticação real,
qualidade semântica nem resultado em mods pessoais. O relato de perda de chave no
fechamento normal não foi reproduzido no computador do usuário.
