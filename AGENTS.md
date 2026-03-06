# AGENTS.md — Guia de execução para agentes no repositório Finance Agent

Este arquivo define como agentes de IA devem operar neste repositório.

## Objetivo

Garantir que qualquer implementação siga o domínio do produto, as decisões já tomadas e o plano de evolução do Finance Agent.

## Leitura obrigatória antes de implementar

Antes de criar código, seguir esta sequência:

1. `README.md` — visão geral e escopo do MVP.
2. `docs/product_overview.md` — objetivos funcionais e não funcionais.
3. `docs/decisions.md` — decisões já fechadas (não reabrir sem solicitação explícita).
4. `docs/domain_model.md` — entidades e relações do domínio.
5. `docs/import_pipeline.md` — fluxo de importação manual.
6. `docs/classification_strategy.md` — estratégia de classificação sem LLM.
7. `docs/categories.md` — categorias de consumo e categorias técnicas.
8. `docs/implementation_plan.md` — fase atual e backlog estruturado.

## Regras operacionais

- Não introduzir LLM no MVP.
- Não implementar autodetecção de tipo de arquivo no MVP.
- Não implementar autodetecção de conta/cartão no MVP.
- Manter suporte explícito a múltiplas contas e múltiplos cartões por banco.
- Tratar `Pagamento de Fatura` e `Transferência Interna` como categorias técnicas fora dos relatórios principais.
- Preservar estratégia cash basis para parcelas no MVP.

## Entregas de código

Ao implementar qualquer funcionalidade:

1. Referenciar explicitamente quais documentos orientaram as decisões.
2. Atualizar documentação impactada no mesmo commit.
3. Registrar nova decisão arquitetural em `docs/decisions.md` quando aplicável.
4. Evitar criar abstrações antecipadas para pós-MVP sem justificativa.

## Ordem sugerida de execução técnica

1. Modelo de dados e migrações.
2. Importação de CSV com validações e persistência por lote.
3. Pipeline de classificação em camadas (normalização → MerchantMap → regras → similaridade → review queue).
4. Interface de revisão manual.
5. Relatórios básicos de consumo (excluindo categorias técnicas).

## Prompts prontos para uso

Para tarefas recorrentes com Codex, usar:

- `prompts/codex/prompt_initialize_repo.md`
- `prompts/codex/prompt_create_models.md`
- `prompts/codex/prompt_create_import_pipeline.md`
- `prompts/codex/prompt_review_code.md`

## Critérios de qualidade mínimos

- Coerência total com as decisões de domínio.
- Rastreabilidade por `ImportBatch`.
- Idempotência razoável em importação (evitar duplicação acidental).
- Transparência da classificação (explicar origem da categoria atribuída).
- Segurança de dados (não expor dados sensíveis em logs).
