# AGENTS.md — Contrato operacional para agentes no Finance Agent

Este documento é a **fonte de execução obrigatória** para qualquer agente de IA (ex.: Codex) neste repositório.

> Objetivo: reduzir ambiguidade, evitar quebra de decisões do MVP e padronizar entregas.

## 1) Protocolo obrigatório antes de qualquer implementação

Antes de escrever código, editar arquivos ou propor arquitetura, execute esta leitura **na ordem exata**:

1. [`README.md`](README.md) — visão geral, escopo e mapa da documentação.
2. [`docs/product_overview.md`](docs/product_overview.md) — objetivos funcionais e não funcionais.
3. [`docs/decisions.md`](docs/decisions.md) — decisões fechadas do MVP (não reabrir sem solicitação explícita).
4. [`docs/architecture.md`](docs/architecture.md) — camadas e fluxo ponta a ponta.
5. [`docs/domain_model.md`](docs/domain_model.md) — entidades, relacionamentos e restrições de domínio.
6. [`docs/import_pipeline.md`](docs/import_pipeline.md) — contrato da importação manual.
7. [`docs/classification_strategy.md`](docs/classification_strategy.md) — pipeline de classificação sem LLM.
8. [`docs/categories.md`](docs/categories.md) — taxonomia de consumo e categorias técnicas.
9. [`docs/implementation_plan.md`](docs/implementation_plan.md) — sequência tática de execução.

Se houver conflito de interpretação, prevalece a ordem acima e as decisões em `docs/decisions.md`.

## 2) Restrições invioláveis do MVP

Estas restrições **não podem ser quebradas** sem instrução explícita do mantenedor:

- Não introduzir LLM no MVP.
- Não implementar autodetecção de tipo de arquivo no MVP.
- Não implementar autodetecção de conta/cartão no MVP.
- Manter suporte explícito a múltiplas contas e múltiplos cartões por banco.
- Tratar `Pagamento de Fatura` e `Transferência Interna` como categorias técnicas.
- Excluir categorias técnicas dos relatórios principais de consumo.
- Preservar estratégia **cash basis** para parcelas no MVP.

## 3) Fluxo operacional padrão para tarefas

### 3.1 Planejamento
1. Identificar fase-alvo em [`docs/implementation_plan.md`](docs/implementation_plan.md).
2. Mapear decisões relevantes em [`docs/decisions.md`](docs/decisions.md).
3. Declarar explicitamente, no resultado, quais documentos guiaram a implementação.

### 3.2 Implementação
1. Implementar o menor incremento funcional aderente ao plano.
2. Evitar abstrações antecipadas de pós-MVP sem justificativa.
3. Preservar rastreabilidade por `ImportBatch` e transparência da classificação.

### 3.3 Validação
1. Executar testes/checks aplicáveis ao escopo alterado.
2. Verificar regressões nas regras críticas de domínio.
3. Confirmar que não houve violação das restrições invioláveis.

### 3.4 Fechamento
1. Atualizar documentação impactada **no mesmo commit**.
2. Registrar decisão nova em [`docs/decisions.md`](docs/decisions.md), quando aplicável.
3. Descrever limites, riscos e próximos passos no resumo final.

## 4) Critérios mínimos de qualidade

- Coerência integral com domínio e decisões já registradas.
- Idempotência razoável na importação (evitar duplicação acidental).
- Transparência da origem da categoria atribuída (`MerchantMap`, regra, similaridade ou manual).
- Segurança de dados: logs sem exposição de dados sensíveis.
- Entrega incremental e auditável.

## 5) Sequência técnica recomendada (macro)

1. Modelo de dados e migrações.
2. Importação de CSV com validações e persistência por lote.
3. Classificação em camadas (normalização → `MerchantMap` → regras → similaridade → revisão).
4. Interface de revisão manual.
5. Relatórios básicos de consumo (excluindo categorias técnicas).

Referência: [`docs/implementation_plan.md`](docs/implementation_plan.md).

## 6) Prompts oficiais do repositório

Use os prompts em `prompts/codex/` conforme a etapa:

- Inicialização: [`prompts/codex/prompt_initialize_repo.md`](prompts/codex/prompt_initialize_repo.md)
- Modelos: [`prompts/codex/prompt_create_models.md`](prompts/codex/prompt_create_models.md)
- Importação: [`prompts/codex/prompt_create_import_pipeline.md`](prompts/codex/prompt_create_import_pipeline.md)
- Revisão técnica: [`prompts/codex/prompt_review_code.md`](prompts/codex/prompt_review_code.md)

## 7) Definição de pronto (DoD) para tarefas de agente

Uma tarefa só é considerada concluída quando:

1. respeita todas as restrições invioláveis do MVP;
2. está alinhada com `docs/decisions.md` e `docs/implementation_plan.md`;
3. possui validação executada e reportada;
4. inclui atualização de documentação impactada;
5. mantém rastreabilidade e auditabilidade do fluxo alterado.
