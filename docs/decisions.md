# Registro de Decisões

Este documento consolida decisões formais já tomadas para o MVP do Finance Agent.

## D-001 — Stack do MVP
- **Decisão:** usar Django + SQLite + Django Templates, com HTMX opcional.
- **Motivo:** simplicidade de desenvolvimento, operação e manutenção no início.

## D-002 — Sem LLM no MVP
- **Decisão:** classificação sem LLM na primeira versão.
- **Motivo:** previsibilidade, custo baixo e comportamento determinístico.

## D-003 — Seleção manual no upload
- **Decisão:** o upload exige seleção manual de tipo de arquivo e de conta/cartão.
- **Motivo:** reduzir ambiguidade e evitar heurísticas frágeis no começo.

## D-004 — Suporte a múltiplas contas/cartões
- **Decisão:** modelar explicitamente múltiplas contas e múltiplos cartões por banco.
- **Motivo:** refletir cenário real do usuário e evitar limitações de expansão.

## D-005 — Entidades obrigatórias do domínio
- **Decisão:** incluir `Account`, `ImportBatch`, `Transaction`, `MerchantMap`, `ReviewQueue`, `Budget` e `Category` no MVP.
- **Motivo:** cobrir núcleo funcional de importação, classificação, revisão e relatório.

## D-006 — Pipeline de classificação oficial
- **Decisão:** normalização → MerchantMap → regras YAML → similaridade fuzzy → ReviewQueue.
- **Motivo:** combinar precisão em casos conhecidos com fallback gradual auditável.

## D-007 — MerchantMap como aprendizado incremental
- **Decisão:** revisões manuais retroalimentam MerchantMap para próximas classificações.
- **Motivo:** reduzir retrabalho e aumentar assertividade com histórico do usuário.

## D-008 — Taxonomia simples no MVP
- **Decisão:** adotar taxonomia de consumo enxuta com categorias amplas e conjunto fixo de categorias técnicas.
- **Motivo:** facilitar implementação, revisão manual e consistência dos relatórios no início.

## D-009 — Modelo canônico de categorias
- **Decisão:** padronizar categoria com `Category.kind` (`consumo`/`tecnica`) e `Category.is_reportable`.
- **Motivo:** remover ambiguidade de nomenclatura e manter regra explícita de reportabilidade.

## D-010 — Pagamento de fatura não é gasto de consumo
- **Decisão:** classificar em categoria técnica `Pagamento de Fatura`.
- **Motivo:** evitar dupla contagem no consumo do cartão.

## D-011 — Transferência interna não é gasto de consumo
- **Decisão:** classificar em categoria técnica `Transferência Interna`.
- **Motivo:** evitar distorção de consumo em movimentações entre contas próprias.

## D-012 — Categorias técnicas fora do relatório principal
- **Decisão:** categorias técnicas não entram nos relatórios principais de consumo.
- **Motivo:** preservar leitura real de despesas de consumo.

## D-013 — Parcelamento em cash basis no MVP
- **Decisão:** compras parceladas são reconhecidas pelos movimentos mensais reais da fatura.
- **Motivo:** aderência ao fluxo prático de pagamento e simplificação inicial.

## D-014 — Deduplicação por hash canônico
- **Decisão:** deduplicar por `raw_hash` canônico com escopo de unicidade em `account_id + raw_hash`.
- **Motivo:** garantir idempotência prática sem heurísticas temporais frágeis.

## D-015 — Composição do raw_hash
- **Decisão:** calcular `raw_hash = sha256(account_id + transaction_date + amount + description_norm + direction)` após normalização canônica.
- **Motivo:** criar assinatura estável por lançamento para impedir duplicações acidentais, distinguindo movimentos de mesma data/valor/descrição com direções opostas.

## D-016 — Parsers dedicados por tipo de arquivo
- **Decisão:** manter parser específico para cada `file_type` suportado no MVP.
- **Motivo:** tornar validação e manutenção previsíveis quando layouts mudarem.

## D-017 — Prioridade de deduplicação com identificador externo
- **Decisão:** quando o arquivo fornecer identificador externo confiável por transação, deduplicar por `account_id + external_id + raw_hash`; na ausência desse identificador, manter fallback por `account_id + raw_hash`.
- **Motivo:** permitir lançamentos legítimos com mesmo `external_id` e conteúdo canônico diferente (casos reais de pares +/-), sem abrir mão da idempotência.

## D-018 — Deduplicação obrigatória por identificador no extrato Nubank conta
- **Decisão:** para o layout `extrato_conta_nubank`, o campo `Identificador` é obrigatório e a deduplicação ocorre por `account_id + external_id + raw_hash`, sem fallback por `account_id + raw_hash` quando o identificador não existir (linha inválida no parser).
- **Motivo:** o layout já oferece identificador externo confiável por lançamento; torná-lo obrigatório reduz ambiguidade e evita aceitar linhas inválidas sem chave de idempotência adequada.

## D-019 — Aliases explícitos do titular para transferência interna
- **Decisão:** adicionar configuração explícita `CLASSIFICACAO_ALIASES_TITULAR` por ambiente (com suporte por conta via `external_ref` ou `account_id`) para detectar `Transferência Interna` por match forte com `merchant_norm`.
- **Motivo:** separar com mais precisão transferências entre contas próprias versus transferências para terceiros, mantendo rastreabilidade em `classification_source=rule` e sem quebrar taxonomia técnica do MVP.
## D-020 — Pares de Pix no Crédito são movimento técnico no MVP
- **Decisão:** quando o extrato Nubank conta trouxer par com mesmo `external_id`, mesma data, valores opostos e descrições `Valor adicionado ... Pix no Crédito` + `Transferência enviada pelo Pix ...`, classificar ambos como categoria técnica `Transferência Interna`.
- **Motivo:** evitar que operações internas de crédito-para-Pix contaminem consumo e `MerchantMap`, sem criar nova categoria técnica fora da taxonomia do MVP.

## D-021 - Importacao em massa preserva um ImportBatch por arquivo
- **Decisao:** a importacao em massa no MVP recebe varios CSVs com `account` e `file_type` informados uma vez, cria um `ImportBatch` independente por arquivo e infere apenas `reference_month` pelo conteudo do CSV.
- **Motivo:** permitir operacao mensal mais rapida sem autodetectar conta ou tipo de arquivo, preservando rastreabilidade, deduplicacao e auditoria por lote.

## D-022 - Regras YAML editaveis pelo Admin
- **Decisao:** regras declarativas do MVP ficam em `ClassificationRuleSet`, com YAML versionado, editavel pelo Django Admin e validacao obrigatoria antes da ativacao.
- **Motivo:** permitir ajustes auditaveis de classificacao sem alterar codigo, mantendo pipeline deterministico, sem LLM e com primeira regra valida vencendo por prioridade.
- **Limite:** a primeira versao aceita apenas regras por campos da propria `Transaction`; aliases do titular, pares de Pix no Credito e orquestracao do pipeline permanecem em Python.

## D-023 - Similaridade fuzzy conservadora baseada em MerchantMap
- **Decisao:** a etapa de similaridade fuzzy compara apenas `Transaction.merchant_norm` contra merchants existentes em `MerchantMap`, usando RapidFuzz, e considera somente categorias de consumo ativas e reportaveis.
- **Motivo:** aproveitar aprendizado manual sem introduzir LLM, mantendo baixo risco de falso positivo em categorias tecnicas.
- **Limite:** score >= 90 classifica automaticamente com `classification_source=similarity`; score entre 80 e 89 cria `ReviewQueue` com sugestao; score menor segue sem sugestao.
