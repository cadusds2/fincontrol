# AGENTS.md — Contrato operacional para agentes no Finance Agent

Este documento é a **fonte de execução obrigatória** para qualquer agente de IA neste repositório.

## 1) Protocolo obrigatório antes de qualquer implementação

Antes de editar arquivos, executar na ordem exata:

1. [`README.md`](README.md)
2. [`docs/product_overview.md`](docs/product_overview.md)
3. [`docs/decisions.md`](docs/decisions.md)
4. [`docs/architecture.md`](docs/architecture.md)
5. [`docs/domain_model.md`](docs/domain_model.md)
6. [`docs/import_pipeline.md`](docs/import_pipeline.md)
7. [`docs/classification_strategy.md`](docs/classification_strategy.md)
8. [`docs/categories.md`](docs/categories.md)
9. [`docs/implementation_plan.md`](docs/implementation_plan.md)

Se houver conflito, prevalece essa ordem e as decisões de `docs/decisions.md`.

## 2) Restrições invioláveis do MVP

Sem instrução explícita do mantenedor, não quebrar:

- Não introduzir LLM no MVP.
- Não implementar autodetecção de tipo de arquivo no MVP.
- Não implementar autodetecção de conta/cartão no MVP.
- Manter suporte explícito a múltiplas contas e múltiplos cartões por banco.
- Tratar `Pagamento de Fatura`, `Transferência Interna` e `Movimentação de Investimentos` como categorias técnicas.
- Excluir categorias técnicas dos relatórios principais de consumo.
- Preservar estratégia **cash basis** para parcelas no MVP.
- Preservar deduplicação canônica por `raw_hash` com unicidade em `account_id + raw_hash`.

## 3) Padrões obrigatórios de terminologia

Usar de forma consistente:
- `Category.kind` (`consumo` ou `tecnica`)
- `Category.is_reportable` (define presença em relatório principal)

Evitar nomenclaturas paralelas (`include_in_reports`, `is_technical`) na documentação do MVP.

## 4) Fluxo operacional padrão para tarefas

### 4.1 Planejamento
1. Identificar fase-alvo em [`docs/implementation_plan.md`](docs/implementation_plan.md).
2. Mapear decisões relevantes em [`docs/decisions.md`](docs/decisions.md).
3. Declarar no resultado quais documentos guiaram a implementação.

### 4.2 Implementação
1. Implementar o menor incremento funcional aderente ao plano.
2. Evitar abstrações pós-MVP sem justificativa.
3. Preservar rastreabilidade por `ImportBatch` e transparência da classificação.

### 4.3 Validação
1. Executar testes/checks aplicáveis ao escopo alterado.
2. Verificar regressões nas regras críticas de domínio.
3. Confirmar que não houve violação das restrições invioláveis.

### 4.4 Fechamento
1. Atualizar documentação impactada no mesmo commit.
2. Registrar decisão nova em [`docs/decisions.md`](docs/decisions.md), quando aplicável.
3. Descrever limites, riscos e próximos passos no resumo final.

## 5) Qualidade mínima

- Coerência com domínio e decisões registradas.
- Idempotência de importação no nível esperado para MVP.
- Transparência da origem da classificação (`classification_source`).
- Logs sem exposição de dados sensíveis.
- Entrega incremental e auditável.
