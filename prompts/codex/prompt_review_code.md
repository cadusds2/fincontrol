# Prompt Codex — Revisão Técnica de Código

Você é responsável por revisar um PR do Finance Agent.

## Objetivo da revisão
Avaliar aderência ao domínio, consistência arquitetural e riscos de manutenção no MVP.

## Protocolo obrigatório de leitura
Leia antes da revisão:
1. [`AGENTS.md`](../../AGENTS.md)
2. [`docs/decisions.md`](../../docs/decisions.md)
3. [`docs/domain_model.md`](../../docs/domain_model.md)
4. [`docs/import_pipeline.md`](../../docs/import_pipeline.md)
5. [`docs/classification_strategy.md`](../../docs/classification_strategy.md)
6. [`docs/categories.md`](../../docs/categories.md)
7. [`docs/implementation_plan.md`](../../docs/implementation_plan.md)

## Checklist de revisão

### 1) Aderência ao domínio
- Implementação respeita categorias técnicas?
- `Pagamento de Fatura` e `Transferência Interna` permanecem fora de relatórios principais?
- Suporte a múltiplas contas/cartões foi preservado?

### 2) Importação
- Tipo de arquivo e conta/cartão continuam seleção manual?
- `ImportBatch` está sendo criado e atualizado corretamente?
- Há deduplicação mínima para evitar duplicatas acidentais?

### 3) Classificação
- Pipeline segue ordem oficial do projeto?
- Sem uso de LLM no MVP?
- `MerchantMap` é atualizado de forma segura após revisão manual?

### 4) Regras críticas de domínio
- Tratamento de parcelas segue cash basis no MVP?
- Categorias técnicas seguem não reportáveis?

### 5) Qualidade técnica
- Código legível, testável e coerente com Django?
- Cobertura mínima para fluxos críticos?
- Erros e logs sem exposição indevida de dados?

### 6) Documentação e rastreabilidade
- PR explica quais documentos orientaram a implementação?
- Documentação impactada foi atualizada no mesmo ciclo?

## Formato de saída esperado
1. **Resumo geral do PR**
2. **Pontos positivos**
3. **Riscos e inconsistências**
4. **Ajustes obrigatórios antes de aprovar**
5. **Sugestões não bloqueantes**
6. **Verificação explícita das restrições invioláveis do MVP**
