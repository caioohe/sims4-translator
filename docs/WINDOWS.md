# Executar, compilar e testar no Windows

Este fork preserva a licença MIT e os créditos de voky1. As correções estão na branch
`fix/translation-reliability`; `main` permanece igual ao upstream até revisão e merge.

## Código-fonte

Use Windows 10/11 de 64 bits e Python 3.12 ou 3.14 de 64 bits. Abra PowerShell:

```powershell
git clone https://github.com/caioohe/sims4-translator.git
cd sims4-translator
git switch fix/translation-reliability
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe main.py
```

Execute a partir da pasta do aplicativo. `prefs/languages.xml`, interfaces e fontes
precisam estar presentes. A configuração é criada localmente em `prefs/config.xml`.
Insira sua chave DeepL somente na interface. DeepL exige uma chave **API**; uma
assinatura do tradutor web não equivale necessariamente a acesso à API.

## Testes sem chave e sem rede

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:QT_QPA_PLATFORM
```

Os testes usam strings e pacotes sintéticos. Nenhum mod pessoal ou API real é usado.

## Build

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name Sims4Translator main.py
Copy-Item prefs dist/Sims4Translator/prefs -Recurse
Copy-Item fonts dist/Sims4Translator/fonts -Recurse
Copy-Item LICENSE dist/Sims4Translator/LICENSE
```

**Antes de distribuir**, exclua do build `prefs/config.xml`, `prefs/recovery/` e
quaisquer dicionários locais. Para um pacote público, prefira o artifact do Actions,
que parte de um checkout limpo e verifica que esses arquivos não estão presentes.
Não copie só o EXE: mantenha a pasta inteira, inclusive `_internal`, `prefs` e `fonts`.
O executável pode ser aberto de outra pasta: o programa ajusta o diretório inicial.

## GitHub Actions

Abra o PR e veja **Checks**, ou abra **Actions → Tests and Windows build**.
Após um run bem-sucedido, baixe **Sims4Translator-Windows**, extraia e abra o EXE.
Os artifacts exigem login no GitHub. O workflow usa apenas `windows-latest`, cache
pip, duas versões de Python nos testes e um build em 3.12. Pushes à branch de
trabalho não disparam builds separados: o PR é o gatilho. Runs antigos do mesmo PR
são cancelados automaticamente. Não há serviços pagos, runners grandes ou secrets.
A gratuidade depende das regras/conta do GitHub; este workflow não configura cobrança.

## Retomar um mod grande

1. Escolha idiomas, abra uma **cópia** do `.package` e selecione DeepL.
2. Use tradução em lote; o modo multiline envia até 50 strings independentes.
3. Cada lote concluído é aplicado e salvo em `prefs/recovery/`. Em 456, revise a
   cota da conta; em 429 persistente, aguarde antes de retomar.
4. Se o app continuar aberto, selecione “Everything but already validated strings”.
5. Ao reabrir o mesmo pacote no mesmo caminho, checkpoints compatíveis são
   recuperados. Mudanças no texto original ou no par de idiomas não são reutilizadas.
6. Salve também seu dicionário e exporte a tradução. Checkpoints não substituem
   backup nem o arquivo final; representam a última tradução automática desse registro.

Para descartar recuperação antiga e começar de novo, feche o app e mova
`prefs/recovery/` para outro local. Traduções de dicionário carregadas têm prioridade
sobre checkpoints. Undo é por lote; desfazer em memória não apaga checkpoints em disco.
Se editar manualmente, salve seu dicionário antes de fechar para ele ter prioridade.

## Validação manual pendente

- Use uma chave válida para testar Free/Pro, idiomas e XML com o serviço real.
- Teste um mod grande, Stop/Cancel/Esc, falha de conexão e retomada após fechar.
- Verifique nomes, tags, quebras e textos de gênero no jogo. Conteúdo dentro de
  `{M0...}`/`{F0...}` é preservado integralmente, não traduzido automaticamente.
- Verifique o pacote exportado no Sims 4 Studio e no jogo. Testes sintéticos não
  certificam todas as variantes DBPF/RefPack nem o conteúdo de mods reais.
- Google continua dependendo de HTML não oficial. Se receber 429, aguarde ou
  escolha uma API autorizada; não há proxy, rotação de IP ou bypass de limites.

## Gemini e Google na atualização

Veja [GEMINI_GOOGLE.md](GEMINI_GOOGLE.md) para configurar a chave Gemini, testar
uma tradução sintética e ajustar o intervalo Google. O ZIP atualizado usa a mesma
branch, com Gemini como provedor adicional.

Microsoft Translator, configurações na aba Geral e salvamento das chaves: [MICROSOFT.md](MICROSOFT.md).
