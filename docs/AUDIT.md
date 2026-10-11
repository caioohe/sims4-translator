# Auditoria e correções — The Sims 4 Translator

Data: 11/10/2026. Escopo: código dos dois repositórios, histórico git completo,
issues e PRs encontrados no GitHub; correções locais com testes simulados.
Não foram utilizados arquivos de mods pessoais nem credenciais de serviços.

## Bases e comparação Wisdom

- Upstream: `voky1/sims4-translator`, `606ca092b97b9ecd964363dfa38998d2558c3a01`.
- Wisdom: `Magonitte/wisdom-mod-translator`, `4cd6004` (HEAD consultado).
- Wisdom contém o mesmo commit upstream e apenas dois commits adicionais:
  `7d5f493` (renomeia aplicação) e `4cd6004` (README em português).

| Arquivo divergente | Mudança real | Efeito sobre tradução |
|---|---|---|
| `README.md` | Reescrita em PT-BR | Nenhum |
| `utils/constants.py` | `APP_NAME = 'Wisdom Mod Translator'` | Nenhum |
| `main.py` | Define applicationName/displayName | Branding |
| `windows/ui/main_window.py` | Troca nome no título | Branding |

`singletons/translator.py`, workers, STBL, DBPF, dicionários e dependências são
iguais nas duas bases. **Wisdom não oferece correção do 429 nessa versão.**
Nenhuma alteração Wisdom foi transplantada.

## Arquitetura e execução

`main.py` cria QApplication, storages e MainWindow. `singletons/config.py` mantém
preferências XML; `languages.py` mapeia idiomas de jogo/Google/DeepL; `interface.py`
carrega textos de interface. `storages/container.py` lê package/STBL/XML/JSON/binary;
`storages/packages.py` organiza registros e exporta/finaliza pacotes. `packer/`
implementa leitura/gravação binária, STBL v5 e DBPF 2.1 com zlib/RefPack.
`models/` e `widgets/` apresentam registros; `windows/` coordena ações de usuário.
`singletons/undo.py` marca pacotes modificados e mantém undo; `dictionaries.py`
carrega/salva DCT. Dependências diretas: PySide6, requests e pyperclip.

No upstream há três caminhos de tradução: toolbar/seleção síncrona com sleeps,
editor síncrono, e batch com QThreadPool sem limite explícito de threads. O batch
enfileira todos os chunks e modifica registros/undo nos workers. Stop chama
`waitForDone()` no thread da interface. O fork corrigido reutiliza o batch para
seleção, usa worker no editor e aplica resultados/undo no thread Qt principal.

## Histórico, issues e PRs

A implementação mudou em `70dde3e` (1.3.1) e `6558e55` (1.4, 05/08/2025).
1.4 substituiu marcadores `__PH_...__` por `(0)`, protegeu tags, adicionou MyMemory
 e tratamento genérico de exceções. A seleção recebeu retries/sleeps no thread GUI;
o batch continuou disparando requests concorrentes sem cooldown/retry.
Não existe evidência de regressão DeepL recente posterior ao HEAD de agosto/2025.

Issues relevantes: #33/#31/#30 reportam 429 sem identificar inequivocamente engine
ou fornecer trace HTTP; #32/#6/#3 reportam travamentos; #9/#2 tokens corrompidos;
#10 espaços perdidos; #4 pacotes ignorados. São relatos, não provas de causa.
O comentário de #33 não acrescenta diagnóstico. Não é correto concluir que todos
esses 429 são do DeepL: Google também pode emitir esse código.

PRs #13 e #14 estão fechados sem merge: separam texto por `{...}` e fazem retries
Google. Isso aumenta requests por string, omite timeout em partes e imprime texto
traduzido/URLs; não foi adotado. PR #16 está aberto e contém alterações extensas,
novos provedores e UI; foi examinado, mas não transplantado por misturar escopos e
não oferecer comprovação de resolver nosso fluxo. #8/#19 são traduções de interface.
Wisdom não apresentou issues/PRs na consulta. Nenhuma discussão externa foi alterada.

## DeepL e causa do 429

**Confirmado no código:** requests.post direto à API oficial `/v2/translate`.
Free usa `api-free.deepl.com`, Pro `api.deepl.com`; autorização por header.
Não usa endpoint web privado nem biblioteca intermediária. Upstream fazia uma
requisição por string no modo lento, ou uma requisição por chunk concatenado em
1024 caracteres no modo rápido (sem contabilizar separators, encoding e XML).
Não há proteção contra bursts no batch; retries da seleção não se aplicam a ele.
A resposta 429 provoca erro e interrompe a fila; 456 já era distinto, mas genérico.
Timeout upstream: 10 segundos; sem retry DeepL nem Retry-After.

**Causa mais provável:** a concorrência e muitos requests pequenos agravam o limite
de frequência/carga do DeepL. A documentação oficial descreve 429 como requests
demais em pouco tempo e recomenda backoff. **Não comprovado no ambiente do usuário:**
não houve chave, trace HTTP ou reprodução contra a conta real. O código corrigido
mitiga essa condição; não garante que o serviço nunca retornará 429.

Política implementada em `utils/translation.py::DeepLTransport.post`:

- Uma chamada DeepL ativa por processo, incluindo os retries; intervalo inicial 0,5s.
- No máximo 3 retries além da tentativa inicial para 429/500/502/503/504 e
  ConnectionError/Timeout, backoff 1/2/4s com jitter e Retry-After numérico/data.
- Retry-After longo é respeitado, sem truncar para chamar antes; espera cancelável.
- 400/403/413/456 não são repetidos; 456 informa cota, 429 persistente sugere aguardar.
- Timeouts separados: conexão 5s, leitura 30s. Requests timeout de leitura é por
  inatividade, não deadline total; uma requisição em curso não é abortada por Event.
- Batch nativo até 50 textos, respostas na ordem recebida e validação de contagem.
  Chunks GUI de 16k caracteres; limite real JSON de 128 KiB também verificado.
  String individual muito grande é rejeitada, não cortada no meio de tokens.

O custo potencial permanece: timeout pode acontecer depois de o servidor processar
a chamada; retry pode cobrar novamente. Nenhuma promessa de exactly-once ou cota
infinita. Intervalo de 0,5s é uma política conservadora local, não limite oficial.

## Problemas e evidências

| Status | Arquivo/função | Problema e correção |
|---|---|---|
| Código + mock | `translator.translate_many`, `DeepLTransport.post` | 429 sem retry/controle: fila, backoff, limites e mensagens |
| Reproduzido | `utils.translation.protect/restore` | `(0)` original colidia com token e tags perdiam espaços: marcadores sem colisão, XML ignore_tags e validação |
| Reproduzido | `BatchTranslateWorker.run` | Concatenar/split por newline tornava mapeamento frágil: array DeepL |
| Código + Qt teste | `TranslateDialog.stop_translate`, workers | GUI esperava threads; worker escrevia undo/records: cancel assíncrono, slots GUI, finished no finally |
| Qt teste | `TranslateDialog.__apply_results`, `RecoveryStore` | Falha posterior: resultados concluídos ficam aplicados e em checkpoint atômico |
| Reproduzido | `translator.__mymemory` | Limite por caracteres em vez de 500 bytes UTF-8; ignorava responseStatus/quotaFinished: valida ambos |
| Mock | `translator.__google` | HTTP sem TLS e exceção de HTML inesperado: HTTPS e erro seguro; scraper continua não oficial |
| Reproduzido | `PackagesStorage.finalize` | Descartava STBL destino sem substituto e recursos vazios: copia os originais |
| Reproduzido | `DbpfPackage.write` | Truncava destino e commitava mesmo em exceção: arquivo temporário e substituição só após sucesso |
| Reproduzido | `DbpfPackage.search` | Cache filtrado por primeiro search_stbl escondia demais recursos: cache completo, filtro na resposta |
| Reproduzido | `Packer.get_raw_bytes/_get_int`, `Stbl.strings/binary` | Leitura truncada produzia valores silenciosos: comprimento exato, contagem plausível e mensagem para string >65535 bytes |
| Reproduzido | `Container.backup` | Movia origem antes da validação e conflitava com backup existente: copia e preserva anteriores |
| Código | `DictionariesStorage.update/save_standalone/search` | Qt model alterado em thread secundário; gravação não atômica; SID 0 ignorado: update GUI, atomic write, teste de None |
| Código | `create_temporary_copy` | Nome temporário determinístico colidia entre mods de mesmo basename: mkstemp |
| Código + smoke | `ConfigManager`, `main.py` | Defaults compartilhados e detecção Windows-only: deepcopy, criação prefs, fallback fora Windows; frozen usa pasta EXE |

A preservação de placeholders detecta remoção/duplicação/alteração e rejeita o lote
sem gravar tradução corrompida. Não demonstra qualidade semântica nem detecta toda
reordenação de tokens. Tags e conteúdo `{...}` são preservados integralmente.
Textos por gênero `{M0...}`/`{F0...}` **não são traduzidos internamente** nesta etapa;
não existe motor gramatical de gênero no upstream. Traduzir esse conteúdo com
segurança exige parser dedicado e exemplos reais, fora desta correção focalizada.

## Progresso e privacidade

`prefs/recovery/` contém apenas identidade dos registros, origem e tradução, por
pacote e par de idiomas. O nome é um hash; o conteúdo não é criptografado. Está
ignorado no git e não entra no artifact CI. Não inclui chave API. Recuperação só
é aplicada a registros ainda não validados com fonte idêntica; dicionário vence.
Falha ao gravar checkpoint interrompe novos lotes e informa que os resultados estão
em memória. Cada lote tem undo independente. Checkpoints não são apagados por undo:
para descartar resultados antigos, mova essa pasta com o programa fechado.

Não há cache HTTP novo; recuperação evita repetir strings já concluídas.
DCT mantém seu formato/versionamento, agora com gravação atômica. Dicionários
antigos/corrompidos ainda podem interromper a leitura; isolamento por arquivo não
foi implementado. Finalização escreve apenas em caminhos escolhidos pelo usuário;
nenhuma finalização foi executada sobre mods pessoais durante a auditoria.

## Validação e limites

Testes em Python 3.12/Linux com PySide6 6.12, requests 2.34.2 e Qt offscreen.
Suite: mocks HTTP, política de concorrência, cancelamento GUI, thread de aplicação,
retenção de progresso/checkpoint, startup MainWindow, DBPF/STBL Unicode e falhas de
exportação. `python -m compileall` também executado. Resultado final em `VALIDATION.md`.
Windows/Python 3.12 e 3.14 mais PyInstaller são validados pelo workflow do PR; o
resultado remoto deve ser consultado antes de tratar o EXE como build aprovado.

Sem validação real: API/qualidade DeepL, Google HTML atual, MyMemory ao vivo, mods
reais/Sims 4 Studio/jogo, todos os caminhos XML/JSON e todas variantes RefPack.
Acesso ao código não substitui testes de ponta a ponta no Windows e no console do jogo.
Remaining: localização PT-BR das novas mensagens; parser de gênero; tratamento
individual de DCT inválido; import/export muito grandes continuam parcialmente
síncronos. Config XML guarda chave local em texto, como upstream; não foi migrado
para keyring. Compatibilidade Win7 e Python 3.15 não é prometida.

## Fontes

- https://github.com/voky1/sims4-translator
- https://github.com/Magonitte/wisdom-mod-translator
- https://github.com/voky1/sims4-translator/issues/33
- https://github.com/voky1/sims4-translator/pull/16
- https://developers.deepl.com/docs/best-practices/error-handling
- https://developers.deepl.com/docs/translate/translating-large-volumes
- https://developers.deepl.com/api-reference/translate/request-translation
- https://mymemory.translated.net/doc/spec.php
- https://mymemory.translated.net/doc/usagelimits.php
