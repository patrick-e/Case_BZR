# Case Técnico — Análise e Conciliação de Precatórios

Este repositório documenta a investigação, o diagnóstico (em ordem decrescente de gravidade) e o mapeamento de impactos realizados a partir do [Contexto e Fluxo Operacional do Enunciado](case-candidato/ENUNCIADO.md#o-fluxo-operacional), confrontando o [Leiaute da Documentação do Tribunal](case-candidato/DOCUMENTACAO_TRIBUNAL.md#leiaute-dos-arquivos-de-integra%C3%A7%C3%A3o) e o [Esquema do Banco (`schema.sql`)](case-candidato/schema.sql) com os arquivos de dados recebidos.

---

## 1. Diagnóstico (Ordem Decrescente de Gravidade)

Atendendo ao que foi pedido no [item de Diagnóstico do Enunciado](case-candidato/ENUNCIADO.md#o-que-pedimos), os problemas foram classificados do mais grave ao menos grave em [diagnostico.md](investigacoes/diagnostico.md):

- **[Nível Crítico](investigacoes/diagnostico.md#critico):**
  - Como exploramos na investigação de [`pagamentos.json`](investigacoes/investigacao.md#pagamentosjson), o arquivo viola o contrato definido para [`pagamentos.json` na Documentação do Tribunal](case-candidato/DOCUMENTACAO_TRIBUNAL.md#pagamentosjson): há `evento_id` repetidos (que deveriam ser identificadores únicos), tipos inconsistentes em `valor` (strings formatadas em PT-BR, números negativos como `-200` e `null`) e eventos de `estorno` onde a documentação garante sempre `"pagamento"`.
  - Quando cruzamos isso com o [Fluxo Operacional (itens 1, 2 e 5)](case-candidato/ENUNCIADO.md#o-fluxo-operacional) — onde o tribunal reenvia os últimos 7 dias diariamente, o script apenas soma os valores sem `UNIQUE` em [`schema.sql`](case-candidato/schema.sql) e ignora erros silenciosamente — além das divergências temporais em [`apresentacoes.json`](investigacoes/investigacao.md#apresenta%C3%A7oesjson), o saldo financeiro da carteira fica severamente distorcido.

- **[Nível Razoável / Moderado](investigacoes/diagnostico.md#razoavel):**
  - Como levantado na investigação de [`hub.csv`](investigacoes/investigacao.md#hubcsv) e [`tribunal.csv`](investigacoes/investigacao.md#tribunalcsv), os dados reais divergem da especificação de [`tribunal.csv` na Documentação do Tribunal](case-candidato/DOCUMENTACAO_TRIBUNAL.md#tribunalcsv) (que prevê separador por vírgula, ponto decimal e padrão CNJ formatado).
  - Essas quebras de leiaute, somadas ao processo manual em Excel e à regra constitucional de 2 de abril descritos no [Contexto e Fluxo Operacional (itens 3 e 4)](case-candidato/ENUNCIADO.md#contexto), explicam os [problemas interligados](investigacoes/investigacao.md#problemas-interligados) de conciliação entre `hub.csv` e `tribunal.csv` e os erros no cálculo do prazo de pagamento.

---

## 2. Trilha da Documentação e Investigação

1. **Base de Referência (Case):**
   - [Enunciado — Contexto, Fluxo Operacional e Entregáveis](case-candidato/ENUNCIADO.md)
   - [Documentação do Tribunal — Especificação de `pagamentos.json` e `tribunal.csv`](case-candidato/DOCUMENTACAO_TRIBUNAL.md)
   - [Schema do Banco de Dados (`schema.sql`)](case-candidato/schema.sql)
2. **Nossa Análise:**
   - [Investigação Exploratória por Arquivo](investigacoes/investigacao.md) ([`pagamentos.json`](investigacoes/investigacao.md#pagamentosjson) | [`apresentacoes.json`](investigacoes/investigacao.md#apresenta%C3%A7oesjson) | [`hub.csv`](investigacoes/investigacao.md#hubcsv) | [`tribunal.csv`](investigacoes/investigacao.md#tribunalcsv) | [Problemas Interligados](investigacoes/investigacao.md#problemas-interligados))
   - [Diagnóstico por Severidade](investigacoes/diagnostico.md) ([Crítico](investigacoes/diagnostico.md#critico) | [Razoável](investigacoes/diagnostico.md#razoavel))
   - [Impactos no Negócio](investigacoes/Impactos.md)
   - [Dúvidas para o Tribunal e a Operação](investigacoes/perguntas.md#perguntas)
