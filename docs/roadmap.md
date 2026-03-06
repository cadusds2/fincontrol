# Roadmap do Produto

## MVP (fase atual)

### Objetivo
Disponibilizar fluxo completo de controle de gastos com importação CSV e classificação sem LLM.

### Entregas previstas
- Cadastro de contas/cartões.
- Importação manual de CSV para Nubank/Itaú (conta e fatura).
- Persistência por lote (`ImportBatch`) e transações (`Transaction`).
- Classificação por pipeline determinístico.
- Fila de revisão manual (`ReviewQueue`).
- Aprendizado via `MerchantMap`.
- Relatório simples por categoria (excluindo técnicas).

## Pós-MVP (curto prazo)

### Objetivo
Aumentar confiabilidade e produtividade do fluxo operacional.

### Evoluções previstas
- Melhorias de UX na revisão (atalhos, filtros e priorização).
- Regras YAML mais ricas com versionamento explícito.
- Estratégias mais robustas de deduplicação.
- Dashboard mensal com comparação orçamento x realizado.
- Ampliação de bancos/formatos de importação.

## Evoluções futuras (médio/longo prazo)

### Objetivo
Escalar inteligência e automação sem perder governança.

### Possibilidades
- Classificação híbrida com LLM (assistiva, não obrigatória).
- Sugestões explicáveis de recategorização por contexto.
- Conectores por API bancária.
- Detecção automática de tipo de arquivo/conta com confirmação humana.
- Projeções e alertas financeiros avançados.

## Critérios para avançar de fase

- MVP → Pós-MVP:
  - Importação e classificação estáveis em uso real.
  - Baixa taxa de erro crítico de ingestão.
  - Fluxo de revisão operacionalmente viável.
- Pós-MVP → Futuro:
  - Base histórica suficiente para modelos mais inteligentes.
  - Governança de dados e métricas de qualidade maduras.
