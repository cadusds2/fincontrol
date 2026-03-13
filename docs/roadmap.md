# Roadmap do Produto

## MVP (fase atual)

### Objetivo
Disponibilizar fluxo completo de controle de gastos com importação manual, classificação sem LLM e revisão manual.

### Entregas
- Cadastro de contas/cartões.
- Importação manual CSV para 4 layouts iniciais.
- Persistência por `ImportBatch` e `Transaction`.
- Deduplicação por `raw_hash` canônico.
- Pipeline oficial de classificação.
- `ReviewQueue` para pendências.
- Aprendizado incremental via `MerchantMap`.
- Relatório por categoria com filtro `Category.is_reportable=true`.

## Pós-MVP (curto prazo)

### Objetivo
Aumentar produtividade e cobertura sem quebrar o modelo do MVP.

### Evoluções previstas
- Melhorias de UX na revisão manual.
- Versionamento mais robusto de regras YAML.
- Ampliação de bancos e formatos suportados.
- Relatórios comparativos mais ricos (orçamento x realizado).
- Eventual detalhamento de taxonomia por subcategorias.

## Futuro (médio/longo prazo)

### Objetivo
Escalar automação com governança.

### Possibilidades
- Classificação assistida por LLM (opcional, fora do MVP).
- Conectores via API bancária.
- Detecção automática com confirmação humana.

## Critérios de avanço

- MVP → Pós-MVP: fluxos de importação, classificação e revisão estáveis em uso real.
- Pós-MVP → Futuro: métricas maduras de qualidade e governança de dados.
