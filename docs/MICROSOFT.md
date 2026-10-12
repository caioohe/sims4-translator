# Microsoft Translator e persistência das opções

## Como configurar no Windows

1. Extraia todo o ZIP para uma pasta com permissão de escrita; execute `Sims4Translator.exe`.
2. Abra Opções → Geral. As configurações dos provedores estão nesta aba, com rolagem.
3. Em Microsoft Translator, use Obter chave de API para abrir o portal Azure.
4. Crie um recurso **Translator** no plano **F0 (gratuito)**; não selecione S1 se não deseja cobranças.
5. Em Keys and Endpoint do recurso, copie a chave e a região para os respectivos campos.
   Para recurso global, deixe a região vazia. Recursos regionais exigem sua região exata.
6. Clique Testar tradução. O teste envia apenas `Hello {0.SimFirstName}!`, sem mods pessoais.
7. Feche Opções para gravar as configurações e selecione Microsoft na janela de tradução.

Também aceita `AZURE_TRANSLATOR_KEY` e `AZURE_TRANSLATOR_REGION`, com prioridade sobre a configuração local.
A chave fica mascarada na interface, mas é salva como texto no `prefs/config.xml` local, como as outras chaves.
Não compartilhe esse arquivo. Nenhum recurso Azure ou faturamento é criado pelo programa.
O F0 oferece 2 milhões de caracteres/mês segundo a tabela oficial consultada; confirme no portal.
Tags de proteção e textos reenviados também podem consumir a franquia. Não é ilimitado.

## Implementação e evidências

- `utils/microsoft.py`: POST oficial v3 no domínio Microsoft; chave em cabeçalho, nunca na URL.
- Lotes de até 100 textos/16 mil caracteres de origem; validação adicional do limite de 50 mil
  caracteres UTF-16 do HTML enviado. Uma língua de destino por pedido.
- `utils/sims_tokens.py`: reutiliza o analisador de chaves, tags, escapes e ramos M/F do Gemini.
  Markers são envolvidos em `span class="notranslate"`, conforme contrato HTML do serviço.
  O HTML da resposta, quantidade de resultados, língua e sequência de tokens são validados antes
  de aplicar qualquer tradução do lote. Respostas inválidas são rejeitadas, sem aplicar resultado parcial.
- `utils/http_policy.py`: serialização, intervalo de 2 s, timeout 5/60 s, até 2 retries de
  429/5xx/conexão/timeout; Retry-After respeitado. Não há proxies nem troca automática de chave.
- `windows/translate_dialog.py`: integra o provedor ao mesmo fluxo de recuperação e cancelamento.
- `windows/ui/options_dialog.py`: remove a aba separada; Geral usa rolagem para manter todos os controles acessíveis.
- `singletons/config.py`: gravação atômica; caminho absoluto fixado ao iniciar; valores de chaves
  continuam strings ao carregar, inclusive sintéticos numéricos.
- `windows/options_dialog.py`: agora salva ao fechar Opções, além do salvamento já existente ao fechar
  a janela principal; falha de gravação apresenta aviso e mantém Opções aberta.

## Relato de chave não salva

Confirmado por código: antes, mudanças ficavam na memória até o fechamento normal da janela principal.
Encerramento forçado ou falha antes dessa etapa podia perder as mudanças. Não foi reproduzida a perda
relatada em um fechamento normal no computador do usuário. Uma pasta sem permissão ou executar uma
nova cópia extraída do ZIP também pode explicar o relato, mas essas hipóteses não foram confirmadas.
A correção torna o salvamento antecipado ao fechar Opções explícito; não protege alterações ainda não
salvas contra desligamento abrupto. Testes verificam reabertura, mudança de diretório e falha de escrita
mantendo o arquivo anterior. Não houve leitura/modificação de chaves reais do usuário.

## Validação

146 testes locais passaram, incluindo requisições simuladas, 429/503, erros permanentes, timeouts,
falhas de conexão, Unicode, gênero, corrupção de tokens, resultado incompleto, integração com registros
reais da aplicação, opções e persistência atômica. Os testes não fazem chamadas reais à Microsoft.
Não há chave Azure disponível neste ambiente. Autenticação real, qualidade semântica e o comportamento
real dos spans precisam do botão Testar tradução e de um pequeno mod revisado pelo usuário.

Fontes oficiais:
- https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/reference/v3/translate
- https://learn.microsoft.com/en-us/azure/ai-services/translator/service-limits
- https://azure.microsoft.com/en-us/pricing/details/translator/

## Tamanho dos lotes

Opções → Geral → Textos por lote permite de 1 a 100, padrão 50. Vale no modo de várias linhas
para Gemini e Microsoft; DeepL é limitado automaticamente a 50. O limite de 16 mil caracteres
continua valendo. O limite considera textos, não arquivos de mods. Mais textos no mesmo pedido
não garante menor tempo e não aumenta a franquia do serviço.
