# Estratégia de Classificação (MVP)

## Princípios

- Pipeline determinístico e auditável.
- Sem LLM no MVP.
- Toda transação termina classificada ou em `ReviewQueue`.
- Origem da classificação registrada em `Transaction.classification_source`.

## Pipeline oficial (ordem obrigatória)

1. **Normalização**
2. **Regra técnica de aliases do titular (transferência interna)**
3. **MerchantMap**
4. **Regras YAML**
5. **Similaridade fuzzy**
6. **ReviewQueue**

## Por que MerchantMap vem antes das regras YAML

`MerchantMap` é aplicado antes porque:
- é mais específico para o histórico real do usuário;
- tende a ter maior precisão para merchants recorrentes;
- evita custo de avaliação de regras mais genéricas quando já existe mapeamento confiável.

## Etapas detalhadas

### 1) Normalização
- Gerar `description_norm` e `merchant_norm` a partir de `description_raw`.
- Aplicar normalizações estáveis (casefold, remoção de ruído textual e espaços redundantes).
- Na construção de `merchant_norm`, após o saneamento semântico e antes da normalização final, remover prefixos genéricos de canal no início do trecho com `remover_prefixos_canal(trecho)`.
- Lista inicial de prefixos descartáveis: `via`, `app`, `site`, `online`, `checkout`.
- Justificativa: esses prefixos aparecem como artefatos de canal de compra e pioram o match em `MerchantMap`, regras e similaridade quando mantidos no início.
- Segurança contra falso positivo: manter lista explícita de exceções para nomes legítimos (ex.: `app store`, `via varejo`) e preservar o trecho original quando a remoção não for segura.
- Após remover prefixos de canal, limpar padrões temporais residuais somente quando estiverem no final do trecho, como `05jan`, `21h22min`, `21h22` e `21:22`.
- Depois da limpeza temporal, normalizar espaços e pontuação residual para preservar uma chave estável de merchant.

### 2) Regra técnica de aliases do titular (transferência interna)
- Comparar `merchant_norm` com aliases conhecidos do titular em configuração explícita por ambiente/conta.
- Em match forte, classificar como `Transferência Interna` (`Category.kind=tecnica`, `Category.is_reportable=false`).
- Registrar `classification_source=rule`.

### 3) MerchantMap
- Buscar `merchant_norm` no mapa.
- Em caso de match, atribuir categoria diretamente.
- Registrar `classification_source=merchant_map`.

### 4) Regras YAML
- Avaliar regras declarativas por prioridade.
- Primeira regra válida vence.
- Registrar `classification_source=rule`.

### 5) Similaridade fuzzy
- Comparar `merchant_norm` com base conhecida.
- Aplicar categoria apenas se score >= limiar definido em configuração.
- Registrar `classification_source=similarity`.

### 6) ReviewQueue
- Se nenhuma etapa anterior produzir classificação confiável, criar item pendente.
- Registrar `classification_source=unclassified` até decisão humana.

## Classificação manual

Ao revisar uma pendência:
- usuário define categoria final;
- sistema atualiza a transação com `classification_source=manual`;
- sistema pode inserir/atualizar `MerchantMap` para aprendizado futuro.

## Regras de transparência

- Toda classificação deve ser explicável por fonte (`merchant_map`, `rule`, `similarity`, `manual`, `unclassified`).
- Logs não devem expor dados sensíveis completos.
- Mudanças de comportamento devem ser rastreáveis por versão de regras YAML.
## Proteções técnicas prioritárias

Algumas descrições técnicas têm prioridade sobre `MerchantMap` para impedir dupla contagem ou aprendizado indevido:
- `Pagamento de fatura` permanece em `Pagamento de Fatura`.
- `Aplicação RDB` permanece em `Movimentação de Investimentos`.
- Pares de Pix no Crédito detectados por mesmo `external_id`, mesma data e valores opostos permanecem em categoria técnica não reportável.
- Revisões manuais de transferências/Pix não criam `MerchantMap` de consumo automaticamente.
