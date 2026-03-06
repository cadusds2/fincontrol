# Finance Agent

Sistema web para controle de gastos pessoais com foco em **importação de extratos/faturas em CSV**, **classificação assistida por regras** e **revisão manual**.

> Status: documentação de base do projeto (fase de definição do MVP).

## Objetivo do projeto

O Finance Agent nasce para resolver um fluxo prático de finanças pessoais:

1. importar arquivos CSV de bancos e cartões;
2. classificar transações automaticamente sem LLM;
3. revisar os casos ambíguos;
4. visualizar gastos de consumo por categoria.

O MVP prioriza previsibilidade, rastreabilidade e simplicidade operacional.

## Escopo do MVP

### Funcionalidades principais
- Importação manual de CSV com escolha explícita de:
  - tipo de arquivo (ex.: extrato conta, fatura cartão);
  - conta/cartão de destino.
- Suporte inicial para:
  - Extrato da conta Nubank;
  - Fatura do cartão Nubank;
  - Extrato da conta Itaú;
  - Fatura do cartão Itaú.
- Pipeline de classificação sem LLM:
  1. normalização;
  2. MerchantMap;
  3. regras YAML;
  4. similaridade fuzzy;
  5. fila de revisão.
- Revisão manual com aprendizado incremental via MerchantMap.
- Visualização simples de gastos por categoria.

### Fora do MVP
- Classificação por LLM.
- Autodetecção do tipo de arquivo e da conta/cartão.
- Integrações bancárias por API.

## Stack tecnológica do MVP
- **Backend:** Django
- **Banco de dados:** SQLite
- **Interface:** Django Templates
- **Interatividade opcional:** HTMX
- **Classificação:** regras YAML + MerchantMap + similaridade fuzzy

## Princípios de domínio já definidos
- Pagamento de fatura **não é gasto**.
- Transferência entre contas próprias **não é gasto**.
- Categorias técnicas obrigatórias:
  - `Pagamento de Fatura`
  - `Transferência Interna`
- Categorias técnicas não entram nos relatórios principais de consumo.
- Parcelamento em cartão no MVP será em **cash basis** (transações mensais reais da fatura).

## Estrutura de documentação

A documentação central do projeto está em `docs/`:

- [Visão geral do produto](docs/product_overview.md)
- [Arquitetura](docs/architecture.md)
- [Modelo de domínio](docs/domain_model.md)
- [Pipeline de importação](docs/import_pipeline.md)
- [Estratégia de classificação](docs/classification_strategy.md)
- [Categorias](docs/categories.md)
- [Decisões registradas](docs/decisions.md)
- [Roadmap](docs/roadmap.md)
- [Plano de implementação](docs/implementation_plan.md)
- [Glossário](docs/glossary.md)

## Como começar (porta de entrada)

Para se situar rápido no projeto e evitar retrabalho, siga esta trilha curta:

1. Leia este `README.md` para entender escopo e limites do MVP.
2. Leia o [`AGENTS.md`](AGENTS.md) para regras operacionais de implementação.
3. Avance para `docs/product_overview.md` e `docs/decisions.md` para consolidar contexto de produto e decisões já fechadas.
4. Só então entre nos documentos de execução (`domain_model`, `import_pipeline`, `classification_strategy` e `implementation_plan`).

Essa sequência reduz risco de contradições e mantém aderência ao domínio definido.

## Uso por agentes (Codex e similares)

1. Leia [`AGENTS.md`](AGENTS.md) antes de iniciar qualquer tarefa.
2. Siga a ordem de leitura indicada no AGENTS para alinhar contexto funcional e técnico.
3. Use os prompts em [`prompts/codex/`](prompts/codex/) para tarefas recorrentes.

## Próximos passos sugeridos

1. Consolidar schema inicial do banco com base no `domain_model.md`.
2. Implementar fluxo de importação manual (`import_pipeline.md`).
3. Implementar classificação sem LLM (`classification_strategy.md`).
4. Entregar tela de revisão e primeiros relatórios de consumo.
