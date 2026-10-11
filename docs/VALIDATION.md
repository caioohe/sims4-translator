# Validação

- Base upstream: 606ca092b97b9ecd964363dfa38998d2558c3a01.
- Ambiente local: Linux, Python 3.12.14, PySide6 6.12.0, requests 2.34.2, pytest 9.1.1.
- Comando: `QT_QPA_PLATFORM=offscreen python -m pytest -q`.
- Resultado local: **51 passed**, sem rede/API real (aproximadamente 0,4s).
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
