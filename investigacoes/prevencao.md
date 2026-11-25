# prevencao

Propostas de mudanças no **processo operacional**, no **script de importação** e no **esquema do banco de dados (SQL)** para impedir que as inconsistências voltem a ocorrer (atendendo ao [item 3 do Enunciado](../case-candidato/ENUNCIADO.md#o-que-pedimos)).

---

## 1. Mudanças no Processo Operacional

1. **Eliminar a edição/salvamento manual do `tribunal.csv` no Excel:**
   - **Problema atual:** O operador abre o CSV no Excel e salva antes de comparar ([item 3 do Fluxo Operacional](../case-candidato/ENUNCIADO.md#o-fluxo-operacional)), o que altera a codificação de `UTF-8` para `Windows-1252/Latin-1`, troca o delimitador `,` por `;` e formata números como `45.000,00`.
   - **Prevenção:** Automatizar a ingestão e a conciliação semanal (`tribunal.csv` vs `hub`) diretamente pelo script Python. Se o operador precisar visualizar o resultado, o script gera uma planilha/relatório de divergências (`output/relatorio_limpeza.md`), mantendo o arquivo original do tribunal intacto (somente leitura).
2. **Formalizar o contrato de integração v2.2 com o Tribunal:**
   - Incluir `apresentacoes.json` na documentação oficial, documentar o tipo `"estorno"` e o comportamento de retificação via `atualizado_em`.

---

## 2. Mudanças no Script de Importação

1. **Idempotência (Upsert por `evento_id` + controle de `atualizado_em`):**
   - Como o tribunal envia sempre os últimos 7 dias e o operador pode rodar o script novamente após falhas, o script nunca deve fazer `SUM` cego ou `INSERT` simples.
   - Deve usar `INSERT ... ON CONFLICT (evento_id) DO UPDATE ... WHERE EXCLUDED.atualizado_em > pagamento.atualizado_em` dentro de uma transação atômica.
2. **Tratamento contábil do campo `tipo` (`pagamento` vs `estorno`):**
   - Ao calcular o total pago de um precatório, somar quando `tipo = 'pagamento'` e **subtrair** quando `tipo = 'estorno'`.
3. **Camada de Normalização e Quarentena (Fim do *Fail-Silent*):**
   - Antes de persistir, passar todos os dados por `Normalizacao` (CNJ formatado com 25 caracteres, datas convertidas para ISO e timestamps convertidos para `America/Sao_Paulo` antes de aplicar o corte `<= 02 de abril`, números PT-BR convertidos para `Decimal`).
   - Substituir o *"ignora e segue sem avisar ninguém"* por uma tabela/relatório de **quarentena (`importacao_erro`)** e disparo de alerta para a operação quando houver `valor <= 0`, `valor IS NULL`, `processo` vazio ou divergência cadastral entre Hub e Tribunal.

---

## 3. Mudanças no Banco de Dados (SQL)

Abaixo está o DDL de evolução do [`schema.sql`](../case-candidato/schema.sql) corrigindo:
- `CHAR(20)` → `CHAR(25)` com validação de máscara CNJ por Regex (`CHECK`);
- Normalização de `ente_devedor` em tabela própria (evitando variações como `MUNICIPIO DE SAO PAULO` vs `Município de São Paulo`);
- Inclusão de `apresentado_em` e `prazo_pagamento` na tabela `precatorio`;
- Inclusão de `UNIQUE (evento_id)` e `atualizado_em` na tabela `pagamento`;
- Criação de view/cálculo do saldo pago líquido (descontando estornos) e tabela de quarentena de erros de importação.

```sql
-- 1. Tabela de domínio para padronizar Entes Devedores (evita texto livre inconsistente)
CREATE TABLE ente_devedor (
    id          BIGSERIAL PRIMARY KEY,
    nome_oficial TEXT NOT NULL UNIQUE,
    esfera       TEXT NOT NULL CHECK (esfera IN ('federal', 'estadual', 'municipal'))
);

-- 2. Tabela de Precatórios corrigida
CREATE TABLE precatorio (
    id              BIGSERIAL     PRIMARY KEY,
    -- Padrão CNJ formatado (NNNNNNN-DD.AAAA.J.TR.OOOO) possui 25 caracteres
    numero_processo CHAR(25)      NOT NULL UNIQUE
        CHECK (numero_processo ~ '^[0-9]{7}-[0-9]{2}\.[0-9]{4}\.[0-9]\.[0-9]{2}\.[0-9]{4}$'),
    ente_devedor_id BIGINT        NOT NULL REFERENCES ente_devedor (id),
    valor_face      NUMERIC(15,2) NOT NULL CHECK (valor_face > 0),
    apresentado_em  DATE          NOT NULL,
    -- Calculado sempre com data de apresentação no fuso America/Sao_Paulo (corte <= 02 de abril)
    prazo_pagamento DATE          NOT NULL,
    status_conciliacao TEXT       NOT NULL DEFAULT 'conciliado'
        CHECK (status_conciliacao IN ('conciliado', 'em_duvida')),
    atualizado_em   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- 3. Tabela de Pagamentos idempotente
CREATE TABLE pagamento (
    id            BIGSERIAL     PRIMARY KEY,
    precatorio_id BIGINT        NOT NULL REFERENCES precatorio (id),
    -- Constraint UNIQUE garante idempotência nos reenvios de 7 dias e reexecuções
    evento_id     TEXT          NOT NULL UNIQUE,
    tipo          TEXT          NOT NULL CHECK (tipo IN ('pagamento', 'estorno')),
    valor         NUMERIC(15,2) NOT NULL CHECK (valor > 0),
    pago_em       DATE          NOT NULL,
    atualizado_em TIMESTAMPTZ   NOT NULL,
    criado_em     TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- 4. Tabela de Quarentena / Auditoria (substitui o descarte silencioso)
CREATE TABLE importacao_quarentena (
    id             BIGSERIAL   PRIMARY KEY,
    arquivo_origem TEXT        NOT NULL,
    identificador  TEXT        NOT NULL,
    payload_bruto  JSONB       NOT NULL,
    motivo_erro    TEXT        NOT NULL,
    resolvido      BOOLEAN     NOT NULL DEFAULT FALSE,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. View para saldo pago líquido por precatório (soma pagamentos e subtrai estornos)
CREATE VIEW vw_saldo_precatorio AS
SELECT
    p.id AS precatorio_id,
    p.numero_processo,
    p.valor_face,
    p.apresentado_em,
    p.prazo_pagamento,
    COALESCE(
        SUM(
            CASE
                WHEN pg.tipo = 'pagamento' THEN pg.valor
                WHEN pg.tipo = 'estorno'   THEN -pg.valor
            END
        ),
        0.00
    )::NUMERIC(15,2) AS total_pago_liquido
FROM precatorio p
LEFT JOIN pagamento pg ON pg.precatorio_id = p.id
GROUP BY p.id, p.numero_processo, p.valor_face, p.apresentado_em, p.prazo_pagamento;

-- 6. Exemplo de UPSERT idempotente usado pelo script de importação
-- Só atualiza se o registro recebido tiver atualizado_em mais recente que o salvo no banco:
/*
INSERT INTO pagamento (precatorio_id, evento_id, tipo, valor, pago_em, atualizado_em)
VALUES (:precatorio_id, :evento_id, :tipo, :valor, :pago_em, :atualizado_em)
ON CONFLICT (evento_id) DO UPDATE
SET
    tipo          = EXCLUDED.tipo,
    valor         = EXCLUDED.valor,
    pago_em       = EXCLUDED.pago_em,
    atualizado_em = EXCLUDED.atualizado_em
WHERE EXCLUDED.atualizado_em > pagamento.atualizado_em;
*/
```
