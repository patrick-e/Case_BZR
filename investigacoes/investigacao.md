# *pagamentos.json*

Confrontando o arquivo [`pagamentos.json`](../case-candidato/dados/pagamentos.json) com a [especificação da Documentação do Tribunal](../case-candidato/DOCUMENTACAO_TRIBUNAL.md#pagamentosjson):

- **`evento_id` repetindo valores (quebra de unicidade):**
  - `ev-002` (linhas 11 e 27): duplicata exata do mesmo registro.
  - `ev-001` (linhas 3 e 67): mesmo `evento_id`, porém com retificação de valor (`15000.0` em `2025-03-10` → `15500.0` em `2025-03-11` no campo `atualizado_em`).
- **Inconsistência de tipos e domínio no campo `valor`** (documentado como *número com ponto decimal*):
  - `string` formatada no padrão PT-BR: `"2.500,50"` (`ev-002`, linhas 13 e 29).
  - `int` negativo: `-200` (`ev-009`, linha 85) mesmo com `"tipo": "pagamento"`.
  - `null`: (`ev-004`, linha 37).
  - Variação entre `float` (`15000.0`, `1200.0`) e `int` (`8000`, `5000`, `3000`, `750`, `4000`).
- **Inconsistência de formato em `data_pagamento`** (documentado como `AAAA-MM-DD`):
  - `ev-002` (linhas 14 e 30) vem no formato `DD/MM/AAAA` (`"10/04/2025"`).
- **Inconsistência no campo `processo`** (documentado como formato CNJ `NNNNNNN-DD.AAAA.J.TR.OOOO`):
  - `ev-005` (linha 44): número sem pontuação/máscara (`"00234562120208260053"`).
  - `ev-010` (linha 92): string vazia (`""`), pagamento órfão de processo.
- **Violação de contrato no campo `tipo`** (documentado como *Sempre "pagamento"*):
  - `ev-007` (linha 63): aparece como `"estorno"` de `5000` (referente ao processo `0034567-32.2018.8.26.0405`).

---

# *apresentaçoes.json*

Analisando [`apresentacoes.json`](../case-candidato/dados/apresentacoes.json) em relação ao restante da base:

- **Arquivo não documentado:** Não consta em [`DOCUMENTACAO_TRIBUNAL.md`](../case-candidato/DOCUMENTACAO_TRIBUNAL.md).
- **Datas de apresentação e pagamento divergem cronologicamente:**
  - O processo `0012345-10.2019.8.26.0053` consta como apresentado em `2025-04-02` (linha 4), mas possui pagamento (`ev-001`) registrado em `2025-03-10` — quase um mês antes da apresentação.
- **Mistura de formatos de data e fusos horários em `apresentado_em`:**
  - Datas simples (`AAAA-MM-DD`): linhas 4, 8, 12 e 24.
  - Data/hora com fuso de Brasília (`-03:00`): `"2025-04-02T23:30:00-03:00"` (linha 16).
  - Data/hora em UTC (`Z`): `"2025-04-03T01:00:00Z"` (linha 20), que no horário de Brasília equivale a `2025-04-02T22:00:00-03:00` (mudando o dia civil na virada do corte constitucional de 2 de abril).

---

# *hub.csv*

Analisando a exportação do sistema interno [`hub.csv`](../case-candidato/dados/hub.csv):

- **Inconsistência no campo `processo`:**
  - Pode estar com máscara CNJ (25 caracteres) ou apenas os 20 dígitos sem pontuação e hífens (`00234562120208260053` na linha 3).
- **Inconsistência de grafia no campo `ente`:**
  - Variação entre caixa alta sem acentuação (`MUNICIPIO DE SAO PAULO`, linha 2) e caixa mista com acentuação (`Município de São Paulo`, linha 3) para o mesmo ente devedor.
- **Inconsistência no campo `apresentado_em`:**
  - Reproduz a mistura de `AAAA-MM-DD`, timestamp com offset `-03:00` e timestamp UTC `Z` vinda de `apresentacoes.json`.
- **Erros no cálculo de `prazo_pagamento` (regra constitucional de 2 de abril do [Enunciado](../case-candidato/ENUNCIADO.md#contexto)):**
  - Linha 2 (`0012345-10.2019.8.26.0053`): apresentado em `2025-04-02` (dentro do limite de *até 2 de abril*), deveria vencer em `2026-12-31`, mas o sistema calculou `2027-12-31`.
  - Linha 6 (`0056789-54.2017.4.03.6100`): apresentado em `2025-04-03T01:00:00Z` (`02/04/2025` às 22h BRT), deveria vencer em `2026-12-31`, mas o sistema usou a data UTC sem converter o fuso e calculou `2027-12-31`.

---

# *tribunal.csv*

Confrontando [`tribunal.csv`](../case-candidato/dados/tribunal.csv) com a [especificação da Documentação do Tribunal](../case-candidato/DOCUMENTACAO_TRIBUNAL.md#tribunalcsv):

- **Codificação de caracteres (`encoding`) divergente:** A documentação especifica `UTF-8`, mas o arquivo real está codificado em `Windows-1252 / Latin-1` (o caractere `í` de `Município` é o byte `0xED`, que quebra leitores estritos de UTF-8) — consequência direta de o operador abrir e salvar no Excel no Windows.
- **Separador de colunas divergente:** A documentação especifica campos separados por vírgula (`,`), mas o arquivo está separado por ponto e vírgula (`;`) — efeito colateral de o operador abrir e salvar o CSV no Excel em PT-BR ([item 3 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional)).
- **Formato numérico de `valor_face` divergente:** A documentação especifica ponto como separador decimal, mas o arquivo usa ponto de milhar e vírgula decimal (`45.000,00`, `30.000,00`, etc.).

---

# Problemas interligados

Cruzando [`schema.sql`](../case-candidato/schema.sql), os 4 arquivos de dados e o [Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional):

- **Tamanho do campo `numero_processo` no banco vs padrão CNJ:**
  - O [`schema.sql`](../case-candidato/schema.sql#L3) define `numero_processo CHAR(20)`, mas o número no padrão CNJ com pontuação (`NNNNNNN-DD.AAAA.J.TR.OOOO`) possui **25 caracteres** (20 dígitos + 5 separadores). Isso explica por que alguns processos aparecem sem máscara (`00234562120208260053`) e impede a inserção direta de processos formatados.
- **Falta de idempotência no banco e no script de importação:**
  - A tabela `pagamento` em [`schema.sql`](../case-candidato/schema.sql#L8-L16) não possui `UNIQUE (evento_id)`. Como o tribunal envia os últimos 7 dias todos os dias e o operador reexecuta o script em caso de falha, o mesmo pagamento é somado múltiplas vezes.
- **Soma indevida de estornos:**
  - O banco aceita `tipo IN ('pagamento', 'estorno')` com `CHECK (valor > 0)`, mas o [Fluxo Operacional (item 2)](../case-candidato/ENUNCIADO.md#o-fluxo-operacional) diz que o script *soma cada valor ao total pago*, somando o estorno `ev-007` (`+5000`) em vez de abater.
- **Divergências cadastrais entre `hub.csv` e `tribunal.csv`:**
  - **Valor de face divergente:** Processo `0023456-21.2020.8.26.0053` tem `valor_face` de `31000.00` no `hub.csv` (linha 3) e `30.000,00` no `tribunal.csv` (linha 3).
  - **Ente devedor conflitante:** Processo `0045678-43.2021.5.02.0011` consta como `Município de Santos` no `hub.csv` (linha 5) e como `União` no `tribunal.csv` (linha 5).
  - **Processos ausentes entre as bases:**
    - `0056789-54.2017.4.03.6100`: existe no `hub.csv`, em `apresentacoes.json` e tem evento em `pagamentos.json` (`ev-009`), mas **não existe** em `tribunal.csv`.
    - `0067890-65.2016.8.26.0053`: existe em `tribunal.csv`, em `apresentacoes.json` e recebeu pagamento em `pagamentos.json` (`ev-011`), mas **não está cadastrado** no `hub.csv`.
- **Ausência de colunas de apresentação e prazo no banco:**
  - O [`schema.sql`](../case-candidato/schema.sql#L1-L6) da tabela `precatorio` não possui colunas para `apresentado_em` nem `prazo_pagamento`, embora esses dados apareçam na exportação do `hub.csv`.
