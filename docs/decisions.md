# Registro de Decisões

Este documento consolida decisões já tomadas para o MVP do Finance Agent.

## D-001 — Stack do MVP
- **Decisão:** usar Django + SQLite + Django Templates, com HTMX opcional.
- **Motivo:** simplicidade de desenvolvimento, operação e manutenção no início.

## D-002 — Sem LLM no MVP
- **Decisão:** classificação sem LLM na primeira versão.
- **Motivo:** previsibilidade, custo baixo e comportamento determinístico.

## D-003 — Importação manual guiada
- **Decisão:** tipo de arquivo e conta/cartão serão escolhidos manualmente na tela de importação.
- **Motivo:** reduzir ambiguidade e evitar heurísticas frágeis no começo.

## D-004 — Suporte a múltiplas contas/cartões
- **Decisão:** modelar explicitamente múltiplas contas e múltiplos cartões por banco.
- **Motivo:** refletir cenário real do usuário e evitar limitações de expansão.

## D-005 — Entidades obrigatórias do domínio
- **Decisão:** incluir `Account`, `ImportBatch`, `Transaction`, `MerchantMap`, `ReviewQueue` e `Budget`.
- **Motivo:** cobrir núcleo funcional de importação, classificação, revisão e planejamento.

## D-006 — Entidade Category
- **Decisão:** `Category` é recomendada para o MVP e considerada parte do desenho-base.
- **Motivo:** padronizar classificação e separar consumo vs técnico.

## D-007 — Pipeline de classificação oficial
- **Decisão:** normalização → MerchantMap → regras YAML → similaridade fuzzy → review queue.
- **Motivo:** combinar precisão em casos conhecidos com fallback gradual auditável.

## D-008 — MerchantMap como aprendizado incremental
- **Decisão:** revisões manuais devem retroalimentar MerchantMap.
- **Motivo:** reduzir retrabalho e melhorar assertividade ao longo do uso.

## D-009 — Pagamento de fatura não é gasto
- **Decisão:** classificar como categoria técnica `Pagamento de Fatura`.
- **Motivo:** evitar dupla contagem de consumo no cartão.

## D-010 — Transferência interna não é gasto
- **Decisão:** classificar como categoria técnica `Transferência Interna`.
- **Motivo:** evitar distorção de consumo em movimentações entre contas próprias.

## D-011 — Categorias técnicas fora do relatório principal
- **Decisão:** categorias técnicas não entram nos relatórios principais de consumo.
- **Motivo:** preservar leitura real de despesas discricionárias e obrigatórias de consumo.

## D-012 — Parcelamento em cash basis no MVP
- **Decisão:** compras parceladas serão registradas como transações mensais reais de fatura.
- **Motivo:** aderência ao fluxo prático de pagamento mensal e simplificação inicial.

## D-013 — Metadados de parcelas em Transaction
- **Decisão:** suportar campos `is_installment`, `installment_current`, `installment_total`, `installment_key`.
- **Motivo:** permitir análise futura de parcelamentos sem alterar histórico base.
