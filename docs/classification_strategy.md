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

As regras YAML do MVP são gerenciadas pelo Django Admin em `ClassificationRuleSet`.
Cada ruleset possui `status` (`draft`, `active`, `archived`), `version`, conteúdo YAML,
`checksum` e erros de validação. Apenas um ruleset fica ativo por vez.

Formato mínimo:

```yaml
version: 1
rules:
  - id: pagamento_fatura
    priority: 100
    category_slug: pagamento-de-fatura
    confidence: "0.95"
    when:
      all:
        - field: description_norm
          contains_all:
            - pagamento
            - fatura
```

Campos permitidos na primeira versão: `description_norm`, `merchant_norm`, `direction`, `currency`.
Operadores permitidos: `contains`, `contains_all`, `equals`, `in`.
`all` exige todas as condições; `any` permite alternativas. Regex, regras relacionais e expressões customizadas ficam fora do MVP.

Fluxo de atualização pelo Admin:
1. Criar ou duplicar um ruleset como `draft`.
2. Editar `version` e `yaml_content` manualmente ou usar "Adicionar regra via formulario".
3. O editor YAML aceita `Tab` para inserir indentacao, `Shift+Tab` para remover indentacao e `Ctrl+Enter` para salvar.
4. O formulario guiado exige um ruleset ja salvo como rascunho; nele, informar `id`, prioridade, categoria, confianca, combinador (`all`/`any`) e ate 3 condicoes.
5. Para operadores `contains_all` e `in`, informar um valor por linha; o Admin converte para lista YAML.
6. Executar a ação "Validar YAML".
7. Corrigir `validation_errors`, se houver.
8. Executar a ação "Ativar ruleset".

Rulesets ativos devem ser tratados como somente leitura. Para mudar comportamento, criar uma nova versão em rascunho.

### 5) Similaridade fuzzy
- Comparar apenas `Transaction.merchant_norm` com `MerchantMap.merchant_norm`.
- Usar somente `MerchantMap` de categorias ativas, `Category.kind=consumo` e `Category.is_reportable=true`.
- Usar RapidFuzz como motor de comparação textual.
- Limiares iniciais configuráveis:
  - `CLASSIFICACAO_FUZZY_AUTO_THRESHOLD = 90`
  - `CLASSIFICACAO_FUZZY_REVIEW_THRESHOLD = 80`
- Score >= 90 classifica automaticamente, com `classification_source=similarity` e `classification_confidence = score / 100`.
- Score entre 80 e 89 mantém a transação como `unclassified`, cria `ReviewQueue` com `reason=low_confidence` e preenche `suggested_category`.
- Score menor que 80 segue para `ReviewQueue` sem sugestão.
- Empate final entre categorias diferentes não classifica automaticamente; cria revisão com `reason=conflict`.
- Categorias técnicas não são usadas pelo fuzzy nesta versão.

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
