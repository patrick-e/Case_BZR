<a id="prevencao"></a>
# Prevenção e Novo Esquema SQL

Ajustes no processo, no script e no banco de dados para evitar que os erros se repitam.

---

## Processo Operacional

- **Ler o `tribunal.csv` direto no script, sem passar pelo Excel:** evita a conversão para `Windows-1252`, a troca de `,` por `;` e a alteração dos números.
- **Atualizar o contrato com o Tribunal:** documentar `apresentacoes.json`, o envio de `"tipo": "estorno"` e a retificação de valores via `atualizado_em`.

---

## Script de Importação

- **Upsert por `evento_id`:** usar `ON CONFLICT (evento_id) DO UPDATE` atualizando apenas quando `atualizado_em` for mais novo. Isso torna o reenvio de 7 dias e as reexecuções seguras.
- **Abater estornos:** somar `pagamento` e subtrair `estorno`.
- **Padronizar na entrada e registrar erros:** formatar CNJ com 25 caracteres, converter datas/timestamps para Brasília (`America/Sao_Paulo`) e gravar registros inválidos em uma tabela de quarentena em vez de ignorá-los em silêncio.

---

## Banco de Dados (`schema.sql`)

Mudanças aplicadas no SQL abaixo:
- `numero_processo`: de `CHAR(20)` para `CHAR(25)` com validação do formato CNJ.
- `ente_devedor`: movido para tabela própria, evitando grafias duplicadas.
- `precatorio`: adicionadas as colunas `apresentado_em` e `prazo_pagamento`.
- `pagamento`: adicionado `UNIQUE` em `evento_id` e coluna `atualizado_em`.
- `importacao_quarentena`: nova tabela para guardar eventos com erro.

```sql
CREATE TABLE ente_devedor (
    id           BIGSERIAL PRIMARY KEY,
    nome_oficial TEXT      NOT NULL UNIQUE,
    esfera       TEXT      NOT NULL CHECK (esfera IN ('federal', 'estadual', 'municipal'))
);

CREATE TABLE precatorio (
    id                 BIGSERIAL     PRIMARY KEY,
    numero_processo    CHAR(25)      NOT NULL UNIQUE
        CHECK (numero_processo ~ '^[0-9]{7}-[0-9]{2}\.[0-9]{4}\.[0-9]\.[0-9]{2}\.[0-9]{4}$'),
    ente_devedor_id    BIGINT        NOT NULL REFERENCES ente_devedor (id),
    valor_face         NUMERIC(15,2) NOT NULL CHECK (valor_face > 0),
    apresentado_em     DATE          NOT NULL,
    prazo_pagamento    DATE          NOT NULL,
    status_conciliacao TEXT          NOT NULL DEFAULT 'conciliado'
        CHECK (status_conciliacao IN ('conciliado', 'em_duvida')),
    atualizado_em      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE pagamento (
    id            BIGSERIAL     PRIMARY KEY,
    precatorio_id BIGINT        NOT NULL REFERENCES precatorio (id),
    evento_id     TEXT          NOT NULL UNIQUE,
    tipo          TEXT          NOT NULL CHECK (tipo IN ('pagamento', 'estorno')),
    valor         NUMERIC(15,2) NOT NULL CHECK (valor > 0),
    pago_em       DATE          NOT NULL,
    atualizado_em TIMESTAMPTZ   NOT NULL,
    criado_em     TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE importacao_quarentena (
    id             BIGSERIAL   PRIMARY KEY,
    arquivo_origem TEXT        NOT NULL,
    identificador  TEXT        NOT NULL,
    payload_bruto  JSONB       NOT NULL,
    motivo_erro    TEXT        NOT NULL,
    resolvido      BOOLEAN     NOT NULL DEFAULT FALSE,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Saldo líquido por precatório (pagamentos - estornos)
CREATE VIEW vw_saldo_precatorio AS
SELECT
    p.id AS precatorio_id,
    p.numero_processo,
    p.valor_face,
    p.apresentado_em,
    p.prazo_pagamento,
    COALESCE(
        SUM(CASE WHEN pg.tipo = 'pagamento' THEN pg.valor ELSE -pg.valor END),
        0.00
    )::NUMERIC(15,2) AS total_pago_liquido
FROM precatorio p
LEFT JOIN pagamento pg ON pg.precatorio_id = p.id
GROUP BY p.id, p.numero_processo, p.valor_face, p.apresentado_em, p.prazo_pagamento;

-- Upsert usado na importação de pagamentos:
INSERT INTO pagamento (precatorio_id, evento_id, tipo, valor, pago_em, atualizado_em)
VALUES (:precatorio_id, :evento_id, :tipo, :valor, :pago_em, :atualizado_em)
ON CONFLICT (evento_id) DO UPDATE
SET
    tipo          = EXCLUDED.tipo,
    valor         = EXCLUDED.valor,
    pago_em       = EXCLUDED.pago_em,
    atualizado_em = EXCLUDED.atualizado_em
WHERE EXCLUDED.atualizado_em > pagamento.atualizado_em;
```
