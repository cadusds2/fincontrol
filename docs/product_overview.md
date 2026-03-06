# Visão Geral do Produto

## Problema

Usuários com múltiplas contas e cartões têm dificuldade para consolidar gastos em uma visão única, principalmente quando os dados vêm de extratos/faturas CSV com formatos distintos por banco.

## Proposta do Finance Agent

O Finance Agent é um sistema web que centraliza importações de CSV bancários, classifica transações automaticamente por regras determinísticas e direciona casos ambíguos para revisão manual.

## Objetivo do MVP

Entregar um fluxo completo e utilizável para:

1. importar CSVs de fontes suportadas;
2. classificar transações sem LLM;
3. revisar pendências;
4. gerar visão simples de gastos por categoria.

## Usuário-alvo inicial

Pessoa física que:
- usa Nubank e/ou Itaú;
- possui múltiplos cartões/contas;
- quer controle mensal de consumo com baixo esforço operacional.

## Fontes suportadas no MVP

- Extrato da conta Nubank.
- Fatura do cartão Nubank.
- Extrato da conta Itaú.
- Fatura do cartão Itaú.

## Premissas operacionais do MVP

- Tipo de arquivo é informado manualmente no upload.
- Conta/cartão é selecionado manualmente no upload.
- Não haverá integração por API bancária.
- Não haverá LLM na classificação.

## Requisitos funcionais de alto nível

- Cadastrar e manter múltiplas contas/cartões por banco.
- Importar arquivo CSV associado a um `ImportBatch`.
- Persistir transações com rastreabilidade de origem.
- Classificar transações por pipeline determinístico.
- Encaminhar baixa confiança para `ReviewQueue`.
- Permitir revisão manual e retroalimentar `MerchantMap`.
- Exibir relatórios básicos de consumo por categoria.

## Requisitos não funcionais de alto nível

- Simplicidade de operação local (Django + SQLite).
- Reprodutibilidade do processo de classificação.
- Transparência de regra aplicada por transação.
- Base preparada para evolução futura com LLM, sem dependência no MVP.
