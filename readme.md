# Case Técnico — Análise e Conciliação de Precatórios

Este repositório documenta a investigação, o diagnóstico (em ordem decrescente de gravidade), o mapeamento de impactos, o pipeline de limpeza em Python e a proposta de prevenção em SQL realizados a partir do [Contexto e Fluxo Operacional do Enunciado](case-candidato/ENUNCIADO.md#o-fluxo-operacional), confrontando o [Leiaute da Documentação do Tribunal](case-candidato/DOCUMENTACAO_TRIBUNAL.md#leiaute-dos-arquivos-de-integra%C3%A7%C3%A3o) e o [Esquema do Banco (`schema.sql`)](case-candidato/schema.sql) com os arquivos de dados recebidos.

---

## 1. Diagnóstico (Ordem Decrescente de Gravidade)

Atendendo ao que foi pedido no [item de Diagnóstico do Enunciado](case-candidato/ENUNCIADO.md#o-que-pedimos), os problemas foram classificados do mais grave ao menos grave em [diagnostico.md](investigacoes/diagnostico.md):

- **[Nível Crítico](investigacoes/diagnostico.md#critico):**
  - Como exploramos na investigação de [`pagamentos.json`](investigacoes/investigacao.md#pagamentosjson), o arquivo viola o contrato definido para [`pagamentos.json` na Documentação do Tribunal](case-candidato/DOCUMENTACAO_TRIBUNAL.md#pagamentosjson): há `evento_id` repetidos (duplicatas exatas como `ev-002` e retificações como `ev-001`), tipos inconsistentes em `valor` (strings formatadas em PT-BR, números negativos como `-200` e `null`) e eventos de `estorno` (`ev-007`) onde a documentação garante sempre `"pagamento"`.
  - Quando cruzamos isso com o [Fluxo Operacional (itens 1, 2 e 5)](case-candidato/ENUNCIADO.md#o-fluxo-operacional) — onde o tribunal reenvia os últimos 7 dias diariamente, o script apenas soma os valores sem `UNIQUE` em [`schema.sql`](case-candidato/schema.sql) e ignora erros silenciosamente — além das divergências temporais em [`apresentacoes.json`](investigacoes/investigacao.md#apresenta%C3%A7oesjson), o saldo financeiro da carteira fica severamente distorcido.

- **[Nível Razoável / Moderado](investigacoes/diagnostico.md#razoavel):**
  - Como levantado na investigação de [`hub.csv`](investigacoes/investigacao.md#hubcsv) e [`tribunal.csv`](investigacoes/investigacao.md#tribunalcsv), os dados reais divergem da especificação de [`tribunal.csv` na Documentação do Tribunal](case-candidato/DOCUMENTACAO_TRIBUNAL.md#tribunalcsv) (que prevê `UTF-8`, separador por vírgula, ponto decimal e padrão CNJ formatado com 25 caracteres, enquanto o arquivo real veio em `Windows-1252`, separado por `;` e o banco define `CHAR(20)`).
  - Essas quebras de leiaute, somadas ao processo manual em Excel e à regra constitucional de 2 de abril descritos no [Contexto e Fluxo Operacional (itens 3 e 4)](case-candidato/ENUNCIADO.md#contexto), explicam os [problemas interligados](investigacoes/investigacao.md#problemas-interligados) de conciliação entre `hub.csv` e `tribunal.csv` e os erros no cálculo do prazo de pagamento.

---

## 2. Trilha da Documentação e Investigação

1. **Base de Referência (Case):**
   - [Enunciado — Contexto, Fluxo Operacional e Entregáveis](case-candidato/ENUNCIADO.md)
   - [Documentação do Tribunal — Especificação de `pagamentos.json` e `tribunal.csv`](case-candidato/DOCUMENTACAO_TRIBUNAL.md)
   - [Schema do Banco de Dados (`schema.sql`)](case-candidato/schema.sql)
2. **Nossa Análise e Entregáveis:**
   - [Investigação Exploratória por Arquivo](investigacoes/investigacao.md) ([`pagamentos.json`](investigacoes/investigacao.md#pagamentosjson) | [`apresentacoes.json`](investigacoes/investigacao.md#apresenta%C3%A7oesjson) | [`hub.csv`](investigacoes/investigacao.md#hubcsv) | [`tribunal.csv`](investigacoes/investigacao.md#tribunalcsv) | [Problemas Interligados](investigacoes/investigacao.md#problemas-interligados))
   - [Diagnóstico por Severidade](investigacoes/diagnostico.md) ([Crítico](investigacoes/diagnostico.md#critico) | [Razoável](investigacoes/diagnostico.md#razoavel))
   - [Impactos no Negócio](investigacoes/Impactos.md)
   - [Proposta de Prevenção e Novo Schema SQL](investigacoes/prevencao.md#prevencao)
   - [Dúvidas para o Tribunal e a Operação](investigacoes/perguntas.md#perguntas)
   - [Relatório Gerado pela Limpeza (`output/relatorio_limpeza.md`)](output/relatorio_limpeza.md)

---

## 3. Como Rodar o Projeto e os Testes

O pipeline utiliza apenas a biblioteca padrão do Python 3.10+ (`csv`, `json`, `decimal`, `datetime`, `zoneinfo`, `unittest`), sem exigir dependências externas para executar a limpeza, mantendo os arquivos originais em `case-candidato/dados/` intactos.

```bash
# 1. Executar o pipeline de limpeza e gerar os arquivos em output/
python3 main.py

# 2. Executar os testes automatizados das regras críticas
python3 -m unittest discover -s tests -v
```

Arquivos gerados em `output/`:
- `output/precatorios_limpos.csv`: base consolidada de precatórios com CNJ formatado (25 caracteres), ente padronizado, prazo constitucional recalculado no fuso de Brasília (`America/Sao_Paulo`) e saldo pago líquido (abatendo estornos).
- `output/pagamentos_limpos.json`: eventos de pagamento válidos, normalizados e deduplicados por `evento_id` (mantendo a versão mais recente por `atualizado_em`).
- `output/relatorio_limpeza.md` e `output/relatorio_limpeza.json`: auditoria detalhada do que foi **corrigido**, **descartado** ou ficou **em dúvida** e por quê.

---

## 4. Uso de IA e Conferência

- **Como a IA foi utilizada:** A IA foi usada como par na revisão da investigação exploratória (ajudando a cruzar os impactos entre o fluxo operacional, o `schema.sql` e os 4 arquivos de dados), na organização dos documentos em Markdown e na estruturação do pipeline de limpeza (`src/normalizacao.py` e `src/limpeza.py`) e testes unitários (`tests/test_limpeza.py`).
- **Como o resultado foi conferido:**
  1. Inspeção manual linha a linha dos arquivos pequenos (`pagamentos.json`, `apresentacoes.json`, `hub.csv` e `tribunal.csv`), validando cada `evento_id` (`ev-001` a `ev-011`) e cada processo CNJ contra o relatório gerado em `output/relatorio_limpeza.md`.
  2. Execução e verificação dos testes unitários (`tests/test_limpeza.py`) cobrindo os casos de borda: corte de 2 de abril com timestamp UTC (`2025-04-03T01:00:00Z` → `2025-04-02` BRT → prazo `2026-12-31`), retificação de `ev-001` (`15000.0` → `15500.0`), deduplicação de `ev-002`, abatimento do estorno `ev-007` e leitura do `tribunal.csv` codificado em `Windows-1252`.
