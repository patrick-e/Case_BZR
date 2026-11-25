# critico

Os problemas abaixo distorcem diretamente o saldo financeiro pago, descartam eventos válidos sem alerta ou corrompem a priorização da carteira de precatórios. Estão ordenados do mais grave para o menos grave:

1. **Multiplicação de pagamentos por falta de idempotência (`evento_id` sem `UNIQUE` + janela de 7 dias + reexecução manual)**
   - **Evidência:** Em [`pagamentos.json`](../case-candidato/dados/pagamentos.json), `ev-002` aparece duplicado (linhas 11 e 27) e `ev-001` aparece duas vezes com valores diferentes (`15000.0` na linha 3 e retificado para `15500.0` na linha 67). Em [`schema.sql`](../case-candidato/schema.sql#L11), a coluna `evento_id` da tabela `pagamento` não possui constraint `UNIQUE`.
   - **Causa ou Consequência:** **Causa raiz** da divergência financeira entre o sistema e o tribunal, agravada pelos [itens 1 e 2 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional) (reenvio diário dos últimos 7 dias e reprocessamento manual do arquivo inteiro quando o script falha).
   - **Impacto:** Veja [Inflação do saldo pago](Impactos.md#1-infla%C3%A7%C3%A3o-e-distor%C3%A7%C3%A3o-do-saldo-pago-impacto-financeiro-direto).

2. **Soma indevida de estornos como se fossem pagamentos**
   - **Evidência:** O registro `ev-007` em [`pagamentos.json`](../case-candidato/dados/pagamentos.json#L59-L65) possui `"tipo": "estorno"` e `"valor": 5000` (anulando o pagamento `ev-006` do processo `0034567-32.2018.8.26.0405`), contrariando a [`DOCUMENTACAO_TRIBUNAL.md`](../case-candidato/DOCUMENTACAO_TRIBUNAL.md#L15) que afirma que `tipo` é sempre `"pagamento"`.
   - **Causa ou Consequência:** **Causa** de erro de saldo (regra de negócio do script no [item 2 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional) que *"soma cada valor ao total pago"* sem verificar o `tipo`), induzida por documentação desatualizada frente ao [`schema.sql`](../case-candidato/schema.sql#L12) (`CHECK (tipo IN ('pagamento', 'estorno'))`).

3. **Descarte silencioso de eventos por falha de validação, tipo ou chave estrangeira**
   - **Evidência:** Pelo [item 5 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional), qualquer erro faz o script ignorar o evento sem avisar ninguém. Isso afeta:
     - `ev-002` (linhas 11 e 27): `valor` em string PT-BR (`"2.500,50"`) e `data_pagamento` em `DD/MM/AAAA` (`"10/04/2025"`).
     - `ev-004` (linha 35): `valor: null` (viola `NOT NULL` em [`schema.sql`](../case-candidato/schema.sql#L13)).
     - `ev-005` (linha 43): `processo` sem máscara (`"00234562120208260053"`), que pode falhar no lookup se a busca exigir formatação idêntica.
     - `ev-009` (linha 83): `valor: -200` com `"tipo": "pagamento"` (viola `CHECK (valor > 0)` em [`schema.sql`](../case-candidato/schema.sql#L13)).
     - `ev-010` (linha 91): `processo: ""` (vazio, impossível vincular a `precatorio_id`).
     - `ev-011` (linha 99): pagamento de `4000` para o processo `0067890-65.2016.8.26.0053`, que **não existe** no [`hub.csv`](../case-candidato/dados/hub.csv) (falha de FK `precatorio_id`).
   - **Causa ou Consequência:** **Consequência** da falta de validação/normalização na entrada somada à política de *fail-silent* (ignorar erros sem log/alerta).

4. **Divergências cadastrais graves entre `hub.csv` e `tribunal.csv` (processos faltantes, valor de face e ente devedor)**
   - **Evidência:**
     - **Processos ausentes:** `0067890-65.2016.8.26.0053` consta em [`tribunal.csv`](../case-candidato/dados/tribunal.csv#L6), [`apresentacoes.json`](../case-candidato/dados/apresentacoes.json#L23) e [`pagamentos.json`](../case-candidato/dados/pagamentos.json#L100), mas não no [`hub.csv`](../case-candidato/dados/hub.csv). Já `0056789-54.2017.4.03.6100` está no [`hub.csv`](../case-candidato/dados/hub.csv#L6), mas não em [`tribunal.csv`](../case-candidato/dados/tribunal.csv).
     - **Conflito de Ente Devedor:** `0045678-43.2021.5.02.0011` está como `Município de Santos` no [`hub.csv`](../case-candidato/dados/hub.csv#L5) e como `União` no [`tribunal.csv`](../case-candidato/dados/tribunal.csv#L5) (nota: o segmento `5.02` do CNJ indica TRT da 2ª Região / Justiça do Trabalho).
     - **Conflito de Valor de Face:** `0023456-21.2020.8.26.0053` vale `31000.00` no [`hub.csv`](../case-candidato/dados/hub.csv#L3) e `30.000,00` no [`tribunal.csv`](../case-candidato/dados/tribunal.csv#L3).
   - **Causa ou Consequência:** **Consequência** da conciliação manual frágil ([item 3 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional)) e da falta de sincronização automatizada do cadastro de precatórios.

5. **Cálculo incorreto do prazo constitucional de pagamento (Regra de 2 de abril e fuso horário UTC)**
   - **Evidência:** Pela [regra constitucional do Enunciado](../case-candidato/ENUNCIADO.md#contexto), precatórios apresentados **até** 2 de abril vencem em `31/12` do ano seguinte. Em [`hub.csv`](../case-candidato/dados/hub.csv):
     - Linha 2 (`0012345-10.2019.8.26.0053`): `apresentado_em = 2025-04-02`, mas `prazo_pagamento` foi calculado como `2027-12-31` (erro de condição `< 02/04` em vez de `<= 02/04`; o correto é `2026-12-31`).
     - Linha 6 (`0056789-54.2017.4.03.6100`): `apresentado_em = 2025-04-03T01:00:00Z`. Convertendo de UTC para Brasília (`-03:00`), foi apresentado em `2025-04-02T22:00:00-03:00` (ainda dia 2 de abril!), mas o sistema usou a data UTC e jogou o prazo para `2027-12-31` em vez de `2026-12-31`.
   - **Causa ou Consequência:** **Causa** de priorização errada da carteira ([item 4 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional)).

---

# razoavel

Problemas estruturais, de modelagem, formatação e documentação que atuam como catalisadores das falhas críticas ou quebram a rotina de conciliação:

1. **Modelagem `CHAR(20)` incompatível com o formato CNJ formatado (25 caracteres) e falta de normalização**
   - **Evidência:** [`schema.sql`](../case-candidato/schema.sql#L3) define `numero_processo CHAR(20)`, mas o formato CNJ (`NNNNNNN-DD.AAAA.J.TR.OOOO`) tem 25 caracteres (20 dígitos + 5 separadores). No [`hub.csv`](../case-candidato/dados/hub.csv#L3) e em [`pagamentos.json`](../case-candidato/dados/pagamentos.json#L44) (`ev-005`), o processo `00234562120208260053` aparece sem pontuação (20 dígitos), enquanto em [`tribunal.csv`](../case-candidato/dados/tribunal.csv#L3) está formatado com 25 caracteres.
   - **Causa ou Consequência:** **Causa** da falha na comparação exata feita pelo operador ([item 3 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional)).

2. **Falta de padronização do nome do `ente_devedor` (`TEXT` livre)**
   - **Evidência:** Em [`hub.csv`](../case-candidato/dados/hub.csv#L2-L3), o mesmo ente aparece como `MUNICIPIO DE SAO PAULO` (caixa alta, sem acento) e `Município de São Paulo` (caixa mista, com acento).
   - **Causa ou Consequência:** **Causa** de falso negativo na conciliação manual exata entre `hub.csv` e `tribunal.csv`.

3. **Corrupção de leiaute do `tribunal.csv` pelo uso do Excel**
   - **Evidência:** [`DOCUMENTACAO_TRIBUNAL.md`](../case-candidato/DOCUMENTACAO_TRIBUNAL.md#tribunalcsv) especifica separador `,` e ponto decimal, mas [`tribunal.csv`](../case-candidato/dados/tribunal.csv) está separado por `;` e com números no formato `45.000,00`.
   - **Causa ou Consequência:** **Consequência** do [item 3 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional), em que o operador abre e salva o arquivo no Excel em PT-BR antes da comparação.

4. **Inconsistência temporal entre data de pagamento e data de apresentação**
   - **Evidência:** O processo `0012345-10.2019.8.26.0053` tem pagamento em `2025-03-10` (`ev-001` em [`pagamentos.json`](../case-candidato/dados/pagamentos.json#L6)), anterior à sua data de apresentação `2025-04-02` em [`apresentacoes.json`](../case-candidato/dados/apresentacoes.json#L4).
   - **Causa ou Consequência:** Possível **consequência** de erro cadastral na data de apresentação ou pagamento lançado no processo errado.

5. **Defasagem entre `schema.sql`, `DOCUMENTACAO_TRIBUNAL.md` e os dados reais**
   - **Evidência:** [`apresentacoes.json`](../case-candidato/dados/apresentacoes.json) não está documentado em [`DOCUMENTACAO_TRIBUNAL.md`](../case-candidato/DOCUMENTACAO_TRIBUNAL.md); a tabela `precatorio` em [`schema.sql`](../case-candidato/schema.sql#L1-L6) não possui as colunas `apresentado_em` e `prazo_pagamento` presentes em [`hub.csv`](../case-candidato/dados/hub.csv).
   - **Causa ou Consequência:** **Causa** de acoplamento frágil e falta de contrato de integração entre tribunal e operação.


Problemas estruturais, de modelagem, formatação e documentação que atuam como catalisadores das falhas críticas ou quebram a rotina de conciliação:

1. **Modelagem `CHAR(20)` incompatível com o formato CNJ formatado (25 caracteres) e falta de normalização**
   - **Evidência:** [`schema.sql`](../case-candidato/schema.sql#L3) define `numero_processo CHAR(20)`, mas o formato CNJ (`NNNNNNN-DD.AAAA.J.TR.OOOO`) tem 25 caracteres (20 dígitos + 5 separadores). No [`hub.csv`](../case-candidato/dados/hub.csv#L3) e em [`pagamentos.json`](../case-candidato/dados/pagamentos.json#L44) (`ev-005`), o processo `00234562120208260053` aparece sem pontuação (20 dígitos), enquanto em [`tribunal.csv`](../case-candidato/dados/tribunal.csv#L3) está formatado com 25 caracteres.
   - **Causa ou Consequência:** **Causa** da falha na comparação exata feita pelo operador ([item 3 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional)).

2. **Falta de padronização do nome do `ente_devedor` (`TEXT` livre)**
   - **Evidência:** Em [`hub.csv`](../case-candidato/dados/hub.csv#L2-L3), o mesmo ente aparece como `MUNICIPIO DE SAO PAULO` (caixa alta, sem acento) e `Município de São Paulo` (caixa mista, com acento).
   - **Causa ou Consequência:** **Causa** de falso negativo na conciliação manual exata entre `hub.csv` e `tribunal.csv`.

3. **Corrupção de leiaute do `tribunal.csv` pelo uso do Excel**
   - **Evidência:** [`DOCUMENTACAO_TRIBUNAL.md`](../case-candidato/DOCUMENTACAO_TRIBUNAL.md#tribunalcsv) especifica separador `,` e ponto decimal, mas [`tribunal.csv`](../case-candidato/dados/tribunal.csv) está separado por `;` e com números no formato `45.000,00`.
   - **Causa ou Consequência:** **Consequência** do [item 3 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional), em que o operador abre e salva o arquivo no Excel em PT-BR antes da comparação.

4. **Inconsistência temporal entre data de pagamento e data de apresentação**
   - **Evidência:** O processo `0012345-10.2019.8.26.0053` tem pagamento em `2025-03-10` (`ev-001` em [`pagamentos.json`](../case-candidato/dados/pagamentos.json#L6)), anterior à sua data de apresentação `2025-04-02` em [`apresentacoes.json`](../case-candidato/dados/apresentacoes.json#L4).
   - **Causa ou Consequência:** Possível **consequência** de erro cadastral na data de apresentação ou pagamento lançado no processo errado.

5. **Defasagem entre `schema.sql`, `DOCUMENTACAO_TRIBUNAL.md` e os dados reais**
   - **Evidência:** [`apresentacoes.json`](../case-candidato/dados/apresentacoes.json) não está documentado em [`DOCUMENTACAO_TRIBUNAL.md`](../case-candidato/DOCUMENTACAO_TRIBUNAL.md); a tabela `precatorio` em [`schema.sql`](../case-candidato/schema.sql#L1-L6) não possui as colunas `apresentado_em` e `prazo_pagamento` presentes em [`hub.csv`](../case-candidato/dados/hub.csv).
   - **Causa ou Consequência:** **Causa** de acoplamento frágil e falta de contrato de integração entre tribunal e operação.