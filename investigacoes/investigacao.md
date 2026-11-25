# Investigação dos Arquivos

Erros encontrados nos arquivos de `case-candidato/dados/` em comparação com a [Documentação do Tribunal](../case-candidato/DOCUMENTACAO_TRIBUNAL.md) e o [`schema.sql`](../case-candidato/schema.sql).

---

<a id="pagamentosjson"></a>
## `pagamentos.json`

- **`evento_id` repetido:**
  - `ev-002` (linhas 11 e 27): registro duplicado.
  - `ev-001` (linhas 3 e 67): mesmo ID enviado duas vezes, mudando o valor de `15000.0` (`10/03`) para `15500.0` (`11/03`).
- **`valor` fora do padrão:**
  - `ev-002`: texto no formato brasileiro (`"2.500,50"`).
  - `ev-004` (linha 37): valor nulo (`null`).
  - `ev-009` (linha 85): valor negativo (`-200`) com `"tipo": "pagamento"`.
- **`data_pagamento` fora do padrão `AAAA-MM-DD`:**
  - `ev-002`: formato `DD/MM/AAAA` (`"10/04/2025"`).
- **`processo` inválido ou sem máscara:**
  - `ev-005` (linha 44): sem pontos e traço (`"00234562120208260053"`).
  - `ev-010` (linha 92): vazio (`""`).
- **`tipo` fora do documentado:**
  - `ev-007` (linha 63): `"estorno"` de `5000` (a documentação diz que esse campo é sempre `"pagamento"`).

---

<a id="apresentaçoesjson"></a>
## `apresentacoes.json`

- **Não documentado:** o arquivo não consta em `DOCUMENTACAO_TRIBUNAL.md`.
- **Formatos de data misturados:** mistura `AAAA-MM-DD`, timestamp com fuso de Brasília (`-03:00`) e timestamp em UTC (`Z`).
- **Virada de dia pelo fuso UTC:** o processo `0056789-54.2017.4.03.6100` traz `2025-04-03T01:00:00Z`, que em Brasília equivale a **`2025-04-02` às 22h** (dentro do corte de 2 de abril).
- **Pagamento antes da apresentação:** o processo `0012345-10.2019.8.26.0053` foi apresentado em `2025-04-02`, mas o pagamento `ev-001` é de `2025-03-10`.

---

<a id="hubcsv"></a>
## `hub.csv`

- **Processo sem pontuação:** `00234562120208260053` (linha 3) tem apenas os 20 dígitos.
- **Ente sem padrão:** `MUNICIPIO DE SAO PAULO` (linha 2) e `Município de São Paulo` (linha 3).
- **Prazo de pagamento errado (regra de 2 de abril):**
  - `0012345-10.2019.8.26.0053`: apresentado em `2025-04-02`. Deveria vencer em **`2026-12-31`**, mas foi calculado como `2027-12-31`.
  - `0056789-54.2017.4.03.6100`: apresentado em `2025-04-03T01:00:00Z` (`02/04` em Brasília). Deveria vencer em **`2026-12-31`**, mas o sistema usou a data UTC e calculou `2027-12-31`.

---

<a id="tribunalcsv"></a>
## `tribunal.csv`

Alterações causadas ao abrir e salvar o arquivo no Excel em português:
- **Codificação:** mudou de `UTF-8` para `Windows-1252 / Latin-1`.
- **Separador:** mudou de vírgula (`,`) para ponto e vírgula (`;`).
- **Números:** `valor_face` mudou de `45000.00` para `45.000,00`.

---

<a id="problemas-interligados"></a>
## Cruzamento entre as Bases e o `schema.sql`

- **Valor de face divergente:** `0023456-21.2020.8.26.0053` vale `31000.00` no Hub e `30.000,00` no Tribunal.
- **Ente devedor divergente:** `0045678-43.2021.5.02.0011` está como `Município de Santos` no Hub e `União` no Tribunal.
- **Processos em apenas uma base:**
  - `0056789-54.2017.4.03.6100`: está no Hub, mas não veio no `tribunal.csv`.
  - `0067890-65.2016.8.26.0053`: está no Tribunal e teve pagamento (`ev-011` de R\$ 4.000,00), mas não existe no Hub.
- **Problemas no `schema.sql`:**
  - `numero_processo CHAR(20)` não comporta os 25 caracteres do padrão CNJ com pontuação.
  - `pagamento.evento_id` não tem `UNIQUE`, permitindo duplicatas.
  - `precatorio` não tem as colunas `apresentado_em` e `prazo_pagamento`.
