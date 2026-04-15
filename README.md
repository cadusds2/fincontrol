# Finance Agent

Sistema web para controle de gastos pessoais com foco em **importação manual de CSV**, **classificação determinística sem LLM** e **revisão manual**.

> Status: documentação-base do MVP para execução incremental por agentes de IA.

## Objetivo do projeto

Entregar um fluxo prático para:
1. importar extratos/faturas em CSV;
2. classificar transações sem LLM;
3. revisar casos ambíguos;
4. visualizar consumo por categoria.

## Escopo do MVP

### Funcionalidades principais
- Importação manual com seleção explícita de `file_type` e `account_id`.
- Suporte inicial a 4 layouts:
  - extrato_conta_nubank
  - fatura_cartao_nubank
  - extrato_conta_itau
  - fatura_cartao_itau
- Pipeline oficial de classificação:
  1. normalização
  2. `MerchantMap`
  3. regras YAML
  4. similaridade fuzzy
  5. `ReviewQueue`
- Relatórios de consumo usando apenas categorias reportáveis.

### Taxonomia oficial do MVP

**Consumo (`Category.kind=consumo`, `Category.is_reportable=true`):**
Moradia, Alimentação, Transporte, Saúde, Lazer, Assinaturas, Educação, Compras, Contas/Serviços, Investimentos, Outros.

**Técnicas (`Category.kind=tecnica`, `Category.is_reportable=false`):**
Pagamento de Fatura, Transferência Interna, Movimentação de Investimentos.

### Fora do MVP
- LLM para classificação.
- Autodetecção de tipo de arquivo.
- Autodetecção de conta/cartão.
- Integrações por API bancária.

## Restrições de domínio já definidas

- Categorias técnicas não entram no relatório principal de consumo.
- Parcelamento no cartão segue **cash basis** no MVP.
- Deduplicação de transação priorizando `external_id` combinado ao hash canônico (`account_id + external_id + raw_hash`) quando disponível, com fallback no hash canônico (`account_id + raw_hash`).

Consulte o registro formal em [`docs/decisions.md`](docs/decisions.md).

## Trilha de leitura obrigatória para agentes

1. [`README.md`](README.md)
2. [`docs/product_overview.md`](docs/product_overview.md)
3. [`docs/decisions.md`](docs/decisions.md)
4. [`docs/architecture.md`](docs/architecture.md)
5. [`docs/domain_model.md`](docs/domain_model.md)
6. [`docs/import_pipeline.md`](docs/import_pipeline.md)
7. [`docs/classification_strategy.md`](docs/classification_strategy.md)
8. [`docs/categories.md`](docs/categories.md)
9. [`docs/implementation_plan.md`](docs/implementation_plan.md)

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


## Setup do ambiente

1. Crie e ative um ambiente virtual Python.
2. Instale as dependências do projeto:

```bash
pip install -r requirements.txt
```

Dependências base do setup atual:
- `Django>=5.1,<6.0`
- `psycopg[binary]>=3.1,<4.0`

## Banco PostgreSQL

Pré-requisito: servidor PostgreSQL em execução.

1. Copie o arquivo de exemplo e ajuste os valores:

```bash
cp .env.exemplo .env
```

Exemplo de variáveis (ver `.env.exemplo`):

```env
TIPO_BANCO=postgres
POSTGRES_BANCO=fincontrol
POSTGRES_USUARIO=fincontrol
POSTGRES_SENHA=fincontrol
POSTGRES_HOST=localhost
POSTGRES_PORTA=5432
```

2. Execute os comandos:

```bash
python manage.py migrate
python manage.py seed_inicial_mvp
```

> Observação: o banco padrão continua SQLite quando `TIPO_BANCO` não for `postgres`.

## Seed inicial do MVP

Para preparar o ambiente para validação manual do domínio:

```bash
python manage.py migrate
python manage.py seed_inicial_mvp
```

O comando `seed_inicial_mvp` é idempotente: em execuções repetidas ele atualiza registros existentes sem criar duplicações de categorias e contas iniciais.
