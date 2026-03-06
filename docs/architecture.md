# Arquitetura do Sistema

## Visão geral

O MVP adota arquitetura monolítica em Django, com separação por camadas lógicas:

1. **Interface Web** (Django Templates, HTMX opcional)
2. **Aplicação/Serviços** (fluxos de importação, classificação e revisão)
3. **Domínio** (entidades e regras de negócio)
4. **Persistência** (SQLite + ORM do Django)

## Componentes principais

- **Módulo de Cadastro**
  - Gerencia contas/cartões (`Account`) e configurações básicas.
- **Módulo de Importação**
  - Recebe CSV, valida metadados manuais, cria `ImportBatch`, normaliza e persiste `Transaction`.
- **Módulo de Classificação**
  - Aplica pipeline: normalização → MerchantMap → regras YAML → similaridade fuzzy → ReviewQueue.
- **Módulo de Revisão**
  - Exibe itens pendentes, recebe decisão manual, atualiza categoria e opcionalmente aprende via `MerchantMap`.
- **Módulo de Relatórios**
  - Consolida consumo por categoria e período, excluindo categorias técnicas.

## Fluxo principal ponta a ponta

1. Usuário seleciona tipo de arquivo e conta/cartão.
2. Sistema cria `ImportBatch` com status inicial.
3. CSV é lido e transformado em registros normalizados.
4. Cada registro vira uma `Transaction` vinculada ao lote.
5. Classificação automática é executada por etapas.
6. Casos sem confiança mínima entram em `ReviewQueue`.
7. Usuário revisa pendências e confirma categoria.
8. Relatórios refletem dados revisados e excluem categorias técnicas.

## Organização de dados (alto nível)

- `Account` (conta/cartão)
- `ImportBatch` (lote de importação)
- `Transaction` (lançamento financeiro)
- `MerchantMap` (aprendizado por merchant normalizado)
- `ReviewQueue` (pendências de classificação)
- `Budget` (orçamento por categoria/período)
- `Category` (catálogo de categorias de consumo e técnicas)

## Estratégias arquiteturais do MVP

- **Determinismo na classificação:** evitar comportamento não reproduzível.
- **Rastreabilidade completa:** cada transação deve apontar para seu lote de origem.
- **Extensibilidade controlada:** preparar pontos para LLM no futuro, sem acoplamento agora.
- **Simplicidade operacional:** priorizar deploy local e manutenção com baixo custo.

## Pontos de extensão planejados (pós-MVP)

- Estratégia de classificação híbrida com LLM.
- Novos conectores de importação (outros bancos/formados).
- Dashboard analítico avançado.
