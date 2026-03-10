# Finance Agent

Sistema web para controle de gastos pessoais com foco em **importação manual de extratos/faturas em CSV**, **classificação determinística sem LLM** e **revisão manual**.

> Status: documentação-base do projeto para execução incremental do MVP por agentes de IA.

## Objetivo do projeto

O Finance Agent resolve um fluxo prático de finanças pessoais:

1. importar arquivos CSV de bancos e cartões;
2. classificar transações automaticamente sem LLM;
3. revisar casos ambíguos com intervenção humana;
4. visualizar gastos de consumo por categoria.

## Escopo do MVP

### Funcionalidades principais
- Importação manual de CSV com escolha explícita de:
  - tipo de arquivo (`extrato_conta` ou `fatura_cartao`);
  - conta/cartão de destino.
- Suporte inicial para:
  - Extrato da conta Nubank;
  - Fatura do cartão Nubank;
  - Extrato da conta Itaú;
  - Fatura do cartão Itaú.
- Pipeline de classificação sem LLM:
  1. normalização;
  2. `MerchantMap`;
  3. regras YAML;
  4. similaridade fuzzy;
  5. fila de revisão.
- Revisão manual com aprendizado incremental via `MerchantMap`.
- Relatórios simples de consumo por categoria.

### Fora do MVP
- Classificação por LLM.
- Autodetecção de tipo de arquivo.
- Autodetecção de conta/cartão.
- Integrações bancárias por API.

## Restrições de domínio já definidas

- `Pagamento de Fatura` **não é gasto de consumo**.
- `Transferência Interna` **não é gasto de consumo**.
- Categorias técnicas obrigatórias:
  - `Pagamento de Fatura`
  - `Transferência Interna`
- Categorias técnicas não entram nos relatórios principais.
- Parcelamento no cartão no MVP segue **cash basis** (movimentos mensais reais da fatura).

Consulte o registro oficial em [`docs/decisions.md`](docs/decisions.md).

## Trilha de leitura obrigatória para agentes

> Antes de qualquer implementação, seguir esta sequência:

1. [`README.md`](README.md)
2. [`docs/product_overview.md`](docs/product_overview.md)
3. [`docs/decisions.md`](docs/decisions.md)
4. [`docs/architecture.md`](docs/architecture.md)
5. [`docs/domain_model.md`](docs/domain_model.md)
6. [`docs/import_pipeline.md`](docs/import_pipeline.md)
7. [`docs/classification_strategy.md`](docs/classification_strategy.md)
8. [`docs/categories.md`](docs/categories.md)
9. [`docs/implementation_plan.md`](docs/implementation_plan.md)

> Ordem canônica alinhada ao contrato em [`AGENTS.md`](AGENTS.md).

## Fluxo de trabalho esperado para implementações

1. **Ler e alinhar contexto** (trilha obrigatória acima).
2. **Selecionar fase ativa** em [`docs/implementation_plan.md`](docs/implementation_plan.md).
3. **Implementar incremento mínimo** sem violar restrições do MVP.
4. **Validar** com testes/checks do escopo alterado.
5. **Atualizar documentação impactada no mesmo commit**.
6. **Registrar decisão nova** em [`docs/decisions.md`](docs/decisions.md), quando aplicável.

## Estrutura de documentação

- Produto: [`docs/product_overview.md`](docs/product_overview.md)
- Decisões: [`docs/decisions.md`](docs/decisions.md)
- Arquitetura: [`docs/architecture.md`](docs/architecture.md)
- Modelo de domínio: [`docs/domain_model.md`](docs/domain_model.md)
- Importação: [`docs/import_pipeline.md`](docs/import_pipeline.md)
- Classificação: [`docs/classification_strategy.md`](docs/classification_strategy.md)
- Categorias: [`docs/categories.md`](docs/categories.md)
- Plano de implementação: [`docs/implementation_plan.md`](docs/implementation_plan.md)
- Roadmap: [`docs/roadmap.md`](docs/roadmap.md)
- Glossário: [`docs/glossary.md`](docs/glossary.md)

## Prompts operacionais para Codex

- [`prompts/codex/prompt_initialize_repo.md`](prompts/codex/prompt_initialize_repo.md)
- [`prompts/codex/prompt_create_models.md`](prompts/codex/prompt_create_models.md)
- [`prompts/codex/prompt_create_import_pipeline.md`](prompts/codex/prompt_create_import_pipeline.md)
- [`prompts/codex/prompt_review_code.md`](prompts/codex/prompt_review_code.md)

Use sempre em conjunto com [`AGENTS.md`](AGENTS.md).
