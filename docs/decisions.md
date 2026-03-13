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
- **Decisão:** calcular `raw_hash = sha256(account_id + transaction_date + amount + description_norm)` após normalização canônica.
- **Motivo:** criar assinatura estável por lançamento para impedir duplicações acidentais.

## D-016 — Parsers dedicados por tipo de arquivo
- **Decisão:** manter parser específico para cada `file_type` suportado no MVP.
- **Motivo:** tornar validação e manutenção previsíveis quando layouts mudarem.
