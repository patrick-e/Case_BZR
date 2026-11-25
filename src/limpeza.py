import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.normalizacao import Normalizacao


@dataclass
class RegistroAuditoria:
    categoria: str  # "corrigido", "descartado", "duvida"
    origem: str
    identificador: str
    campo: str
    valor_original: Any
    valor_final: Any
    motivo: str


@dataclass
class ResultadoLimpeza:
    precatorios: list[dict[str, Any]] = field(default_factory=list)
    pagamentos: list[dict[str, Any]] = field(default_factory=list)
    corrigidos: list[RegistroAuditoria] = field(default_factory=list)
    descartados: list[RegistroAuditoria] = field(default_factory=list)
    duvidas: list[RegistroAuditoria] = field(default_factory=list)


def _ler_texto_com_fallback(caminho: Path) -> tuple[str, str]:
    """Lê o arquivo tentando UTF-8 e fazendo fallback para Windows-1252/Latin-1 (padrão Excel PT-BR)."""
    raw = caminho.read_bytes()
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252 (Windows-1252 / Latin-1)"


def _detectar_delimitador_csv(texto: str) -> str:
    primeira_linha = texto.splitlines()[0]
    if ";" in primeira_linha and "," not in primeira_linha:
        return ";"
    return ","


def carregar_apresentacoes(caminho: Path, resultado: ResultadoLimpeza) -> dict[str, dict[str, str]]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    mapa: dict[str, dict[str, str]] = {}

    for idx, item in enumerate(dados, start=1):
        proc_raw = item.get("processo")
        apres_raw = item.get("apresentado_em")

        proc_norm, proc_alt = Normalizacao.processo(proc_raw)
        if not proc_norm:
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="apresentacoes.json",
                    identificador=f"item#{idx}",
                    campo="processo",
                    valor_original=proc_raw,
                    valor_final=None,
                    motivo="Número de processo ausente ou fora do padrão CNJ (20 dígitos).",
                )
            )
            continue

        if proc_alt:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="apresentacoes.json",
                    identificador=proc_norm,
                    campo="processo",
                    valor_original=proc_raw,
                    valor_final=proc_norm,
                    motivo="Normalizado número do processo para máscara CNJ (25 caracteres).",
                )
            )

        data_brt, prazo, teve_tz = Normalizacao.apresentado_em_prazo(apres_raw)
        if not data_brt or not prazo:
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="apresentacoes.json",
                    identificador=proc_norm,
                    campo="apresentado_em",
                    valor_original=apres_raw,
                    valor_final=None,
                    motivo="Data de apresentação inválida.",
                )
            )
            continue

        if teve_tz:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="apresentacoes.json",
                    identificador=proc_norm,
                    campo="apresentado_em",
                    valor_original=apres_raw,
                    valor_final=data_brt.isoformat(),
                    motivo="Timestamp convertido para fuso America/Sao_Paulo (-03:00) e extraída data civil.",
                )
            )

        mapa[proc_norm] = {
            "apresentado_em": data_brt.isoformat(),
            "prazo_pagamento": prazo.isoformat(),
            "apresentado_em_raw": str(apres_raw),
        }

    return mapa


def carregar_hub(caminho: Path, resultado: ResultadoLimpeza) -> dict[str, dict[str, Any]]:
    texto, _ = _ler_texto_com_fallback(caminho)
    delimitador = _detectar_delimitador_csv(texto)
    mapa: dict[str, dict[str, Any]] = {}

    leitor = csv.DictReader(texto.splitlines(), delimiter=delimitador)
    for linha_num, row in enumerate(leitor, start=2):
        proc_raw = row.get("processo")
        ente_raw = row.get("ente")
        valor_raw = row.get("valor_face")
        apres_raw = row.get("apresentado_em")
        prazo_raw = row.get("prazo_pagamento")

        proc_norm, proc_alt = Normalizacao.processo(proc_raw)
        if not proc_norm:
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="hub.csv",
                    identificador=f"linha#{linha_num}",
                    campo="processo",
                    valor_original=proc_raw,
                    valor_final=None,
                    motivo="Número de processo inválido no hub.csv.",
                )
            )
            continue

        if proc_alt:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="hub.csv",
                    identificador=proc_norm,
                    campo="processo",
                    valor_original=proc_raw,
                    valor_final=proc_norm,
                    motivo="Adicionada pontuação do padrão CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO).",
                )
            )

        ente_norm, ente_alt = Normalizacao.ente(ente_raw)
        if ente_alt:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="hub.csv",
                    identificador=proc_norm,
                    campo="ente",
                    valor_original=ente_raw,
                    valor_final=ente_norm,
                    motivo="Padronizada grafia/acentuação e caixa do nome do ente devedor.",
                )
            )

        valor_dec, _ = Normalizacao.valor_monetario(valor_raw)
        data_brt, prazo_calc, _ = Normalizacao.apresentado_em_prazo(apres_raw)

        if prazo_calc and prazo_raw and prazo_calc.isoformat() != prazo_raw.strip():
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="hub.csv",
                    identificador=proc_norm,
                    campo="prazo_pagamento",
                    valor_original=prazo_raw,
                    valor_final=prazo_calc.isoformat(),
                    motivo=(
                        f"Recalculado prazo constitucional (corte <= 02/04 no fuso de Brasília "
                        f"para apresentação em {data_brt.isoformat() if data_brt else apres_raw})."
                    ),
                )
            )

        mapa[proc_norm] = {
            "numero_processo": proc_norm,
            "ente_devedor": ente_norm,
            "valor_face": valor_dec,
            "apresentado_em": data_brt.isoformat() if data_brt else None,
            "prazo_pagamento": prazo_calc.isoformat() if prazo_calc else prazo_raw,
        }

    return mapa


def carregar_tribunal(caminho: Path, resultado: ResultadoLimpeza) -> dict[str, dict[str, Any]]:
    texto, codificacao = _ler_texto_com_fallback(caminho)
    if codificacao != "utf-8":
        resultado.corrigidos.append(
            RegistroAuditoria(
                categoria="corrigido",
                origem="tribunal.csv",
                identificador="arquivo",
                campo="encoding",
                valor_original=codificacao,
                valor_final="utf-8",
                motivo="Arquivo salvo em Windows-1252/Latin-1 (pelo Excel) em vez de UTF-8 previsto na documentação.",
            )
        )

    delimitador = _detectar_delimitador_csv(texto)
    if delimitador != ",":
        resultado.corrigidos.append(
            RegistroAuditoria(
                categoria="corrigido",
                origem="tribunal.csv",
                identificador="arquivo",
                campo="delimitador",
                valor_original=delimitador,
                valor_final=",",
                motivo="Detectado delimitador ';' (gerado pelo Excel) em vez de ',' previsto na documentação.",
            )
        )

    mapa: dict[str, dict[str, Any]] = {}
    leitor = csv.DictReader(texto.splitlines(), delimiter=delimitador)
    for linha_num, row in enumerate(leitor, start=2):
        proc_raw = row.get("numero_processo")
        ente_raw = row.get("ente_devedor")
        valor_raw = row.get("valor_face")

        proc_norm, proc_alt = Normalizacao.processo(proc_raw)
        if not proc_norm:
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="tribunal.csv",
                    identificador=f"linha#{linha_num}",
                    campo="numero_processo",
                    valor_original=proc_raw,
                    valor_final=None,
                    motivo="Número de processo inválido em tribunal.csv.",
                )
            )
            continue

        if proc_alt:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="tribunal.csv",
                    identificador=proc_norm,
                    campo="numero_processo",
                    valor_original=proc_raw,
                    valor_final=proc_norm,
                    motivo="Normalizado número do processo para máscara CNJ.",
                )
            )

        ente_norm, ente_alt = Normalizacao.ente(ente_raw)
        if ente_alt:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="tribunal.csv",
                    identificador=proc_norm,
                    campo="ente_devedor",
                    valor_original=ente_raw,
                    valor_final=ente_norm,
                    motivo="Padronizada grafia do ente devedor.",
                )
            )

        valor_dec, foi_ptbr = Normalizacao.valor_monetario(valor_raw)
        if foi_ptbr and valor_dec is not None:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="tribunal.csv",
                    identificador=proc_norm,
                    campo="valor_face",
                    valor_original=valor_raw,
                    valor_final=str(valor_dec),
                    motivo="Convertido valor monetário do formato PT-BR (ponto de milhar e vírgula decimal) para Decimal.",
                )
            )

        mapa[proc_norm] = {
            "numero_processo": proc_norm,
            "ente_devedor": ente_norm,
            "valor_face": valor_dec,
        }

    return mapa


def conciliar_precatorios(
    apresentacoes: dict[str, dict[str, str]],
    hub: dict[str, dict[str, Any]],
    tribunal: dict[str, dict[str, Any]],
    resultado: ResultadoLimpeza,
) -> dict[str, dict[str, Any]]:
    todos_processos = sorted(set(apresentacoes) | set(hub) | set(tribunal))
    base_precatorios: dict[str, dict[str, Any]] = {}

    for proc in todos_processos:
        reg_hub = hub.get(proc)
        reg_trib = tribunal.get(proc)
        reg_apres = apresentacoes.get(proc, {})

        status_conciliacao = "conciliado"

        if reg_hub and reg_trib:
            # Verifica divergência de ente devedor após normalização
            if reg_hub["ente_devedor"] != reg_trib["ente_devedor"]:
                status_conciliacao = "em_duvida"
                resultado.duvidas.append(
                    RegistroAuditoria(
                        categoria="duvida",
                        origem="hub.csv vs tribunal.csv",
                        identificador=proc,
                        campo="ente_devedor",
                        valor_original={"hub": reg_hub["ente_devedor"], "tribunal": reg_trib["ente_devedor"]},
                        valor_final=reg_trib["ente_devedor"],
                        motivo=(
                            f"Ente devedor diverge entre Hub ('{reg_hub['ente_devedor']}') e Tribunal "
                            f"('{reg_trib['ente_devedor']}'). Adotado valor do Tribunal e marcado para revisão."
                        ),
                    )
                )

            # Verifica divergência de valor de face
            if reg_hub["valor_face"] != reg_trib["valor_face"]:
                status_conciliacao = "em_duvida"
                resultado.duvidas.append(
                    RegistroAuditoria(
                        categoria="duvida",
                        origem="hub.csv vs tribunal.csv",
                        identificador=proc,
                        campo="valor_face",
                        valor_original={"hub": str(reg_hub["valor_face"]), "tribunal": str(reg_trib["valor_face"])},
                        valor_final=str(reg_trib["valor_face"]),
                        motivo=(
                            f"Valor de face diverge entre Hub ({reg_hub['valor_face']}) e Tribunal "
                            f"({reg_trib['valor_face']}). Adotado valor do Tribunal e marcado para revisão."
                        ),
                    )
                )

            ente_final = reg_trib["ente_devedor"]
            valor_face_final = reg_trib["valor_face"]

        elif reg_trib and not reg_hub:
            status_conciliacao = "em_duvida"
            ente_final = reg_trib["ente_devedor"]
            valor_face_final = reg_trib["valor_face"]
            resultado.duvidas.append(
                RegistroAuditoria(
                    categoria="duvida",
                    origem="tribunal.csv (ausente no hub.csv)",
                    identificador=proc,
                    campo="cadastro_precatorio",
                    valor_original=None,
                    valor_final=proc,
                    motivo=(
                        "Processo existe em tribunal.csv, apresentacoes.json e possui pagamento, "
                        "mas não estava cadastrado no hub.csv. Incluído na base limpa para confirmação."
                    ),
                )
            )
        elif reg_hub and not reg_trib:
            status_conciliacao = "em_duvida"
            ente_final = reg_hub["ente_devedor"]
            valor_face_final = reg_hub["valor_face"]
            resultado.duvidas.append(
                RegistroAuditoria(
                    categoria="duvida",
                    origem="hub.csv (ausente no tribunal.csv)",
                    identificador=proc,
                    campo="cadastro_precatorio",
                    valor_original=proc,
                    valor_final=proc,
                    motivo=(
                        "Processo consta no hub.csv e apresentacoes.json, mas não veio no arquivo "
                        "semanal tribunal.csv. Mantido na base com status 'em_duvida'."
                    ),
                )
            )
        else:
            continue

        apresentado_em = reg_apres.get("apresentado_em") or (reg_hub.get("apresentado_em") if reg_hub else None)
        prazo_pagamento = reg_apres.get("prazo_pagamento") or (reg_hub.get("prazo_pagamento") if reg_hub else None)

        base_precatorios[proc] = {
            "numero_processo": proc,
            "ente_devedor": ente_final,
            "valor_face": valor_face_final,
            "apresentado_em": apresentado_em,
            "prazo_pagamento": prazo_pagamento,
            "total_pago_liquido": Decimal("0.00"),
            "status_conciliacao": status_conciliacao,
        }

    return base_precatorios


def limpar_pagamentos(
    caminho: Path,
    base_precatorios: dict[str, dict[str, Any]],
    resultado: ResultadoLimpeza,
) -> list[dict[str, Any]]:
    registros = json.loads(caminho.read_text(encoding="utf-8"))
    por_evento_id: dict[str, dict[str, Any]] = {}

    for idx, item in enumerate(registros, start=1):
        ev_id = str(item.get("evento_id") or "").strip() or f"sem_id#{idx}"
        proc_raw = item.get("processo")
        valor_raw = item.get("valor")
        data_raw = item.get("data_pagamento")
        tipo_raw = str(item.get("tipo") or "").strip().lower()
        atualizado_raw = str(item.get("atualizado_em") or "").strip()

        # 1. Valida processo
        proc_norm, proc_alt = Normalizacao.processo(proc_raw)
        if not proc_norm:
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="processo",
                    valor_original=proc_raw,
                    valor_final=None,
                    motivo="Evento descartado: campo 'processo' vazio ou fora do padrão CNJ.",
                )
            )
            continue

        if proc_alt:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="processo",
                    valor_original=proc_raw,
                    valor_final=proc_norm,
                    motivo="Adicionada máscara CNJ ao número do processo no evento de pagamento.",
                )
            )

        # 2. Valida valor monetário
        valor_dec, foi_ptbr = Normalizacao.valor_monetario(valor_raw)
        if valor_dec is None:
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="valor",
                    valor_original=valor_raw,
                    valor_final=None,
                    motivo="Evento descartado: valor nulo ou não numérico.",
                )
            )
            continue

        if valor_dec <= Decimal("0.00"):
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="valor",
                    valor_original=valor_raw,
                    valor_final=None,
                    motivo=(
                        f"Evento descartado e enviado para auditoria: valor <= 0 ({valor_dec}) "
                        f"com tipo='{tipo_raw}' (viola CHECK valor > 0 do banco)."
                    ),
                )
            )
            resultado.duvidas.append(
                RegistroAuditoria(
                    categoria="duvida",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="valor",
                    valor_original=valor_raw,
                    valor_final=None,
                    motivo=(
                        f"Evento {ev_id} do processo {proc_norm} veio com tipo='{tipo_raw}' e valor negativo "
                        f"({valor_dec}). Confirmar com tribunal se é um estorno mal classificado."
                    ),
                )
            )
            continue

        if foi_ptbr:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="valor",
                    valor_original=valor_raw,
                    valor_final=str(valor_dec),
                    motivo="Convertido valor em string PT-BR ('2.500,50') para Decimal.",
                )
            )

        # 3. Valida data de pagamento
        data_pag, data_alt = Normalizacao.data_iso(data_raw)
        if not data_pag:
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="data_pagamento",
                    valor_original=data_raw,
                    valor_final=None,
                    motivo="Data de pagamento inválida.",
                )
            )
            continue

        if data_alt:
            resultado.corrigidos.append(
                RegistroAuditoria(
                    categoria="corrigido",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="data_pagamento",
                    valor_original=data_raw,
                    valor_final=data_pag.isoformat(),
                    motivo="Convertida data de pagamento de DD/MM/AAAA para AAAA-MM-DD.",
                )
            )

        # 4. Valida tipo ('pagamento' ou 'estorno')
        if tipo_raw not in ("pagamento", "estorno"):
            resultado.descartados.append(
                RegistroAuditoria(
                    categoria="descartado",
                    origem="pagamentos.json",
                    identificador=ev_id,
                    campo="tipo",
                    valor_original=tipo_raw,
                    valor_final=None,
                    motivo="Tipo de evento desconhecido (esperado 'pagamento' ou 'estorno').",
                )
            )
            continue

        ts_atualizado = datetime.fromisoformat(atualizado_raw)

        candidato = {
            "evento_id": ev_id,
            "numero_processo": proc_norm,
            "tipo": tipo_raw,
            "valor": valor_dec,
            "data_pagamento": data_pag.isoformat(),
            "atualizado_em": atualizado_raw,
            "_ts": ts_atualizado,
        }

        # 5. Deduplicação e retificação por evento_id
        if ev_id in por_evento_id:
            existente = por_evento_id[ev_id]
            if (
                existente["numero_processo"] == candidato["numero_processo"]
                and existente["valor"] == candidato["valor"]
                and existente["data_pagamento"] == candidato["data_pagamento"]
                and existente["tipo"] == candidato["tipo"]
                and existente["atualizado_em"] == candidato["atualizado_em"]
            ):
                resultado.descartados.append(
                    RegistroAuditoria(
                        categoria="descartado",
                        origem="pagamentos.json",
                        identificador=ev_id,
                        campo="evento_id",
                        valor_original=ev_id,
                        valor_final=None,
                        motivo="Duplicata exata de evento_id descartada.",
                    )
                )
                continue

            if candidato["_ts"] >= existente["_ts"]:
                resultado.corrigidos.append(
                    RegistroAuditoria(
                        categoria="corrigido",
                        origem="pagamentos.json",
                        identificador=ev_id,
                        campo="valor",
                        valor_original=str(existente["valor"]),
                        valor_final=str(candidato["valor"]),
                        motivo=(
                            f"Evento retificado pelo tribunal: mantida versão mais recente "
                            f"(atualizado_em {candidato['atualizado_em']} > {existente['atualizado_em']})."
                        ),
                    )
                )
                resultado.duvidas.append(
                    RegistroAuditoria(
                        categoria="duvida",
                        origem="pagamentos.json",
                        identificador=ev_id,
                        campo="valor",
                        valor_original=str(existente["valor"]),
                        valor_final=str(candidato["valor"]),
                        motivo=(
                            f"Mesmo evento_id ({ev_id}) enviado com valor alterado de {existente['valor']} "
                            f"para {candidato['valor']}. Assumida substituição pelo mais recente; confirmar com tribunal."
                        ),
                    )
                )
                por_evento_id[ev_id] = candidato
            else:
                resultado.descartados.append(
                    RegistroAuditoria(
                        categoria="descartado",
                        origem="pagamentos.json",
                        identificador=ev_id,
                        campo="atualizado_em",
                        valor_original=candidato["atualizado_em"],
                        valor_final=existente["atualizado_em"],
                        motivo="Versão antiga de evento_id descartada em favor de versão mais recente.",
                    )
                )
        else:
            por_evento_id[ev_id] = candidato

    # 6. Consolida pagamentos limpos, verifica anomalia temporal e calcula saldo líquido por precatório
    pagamentos_limpos: list[dict[str, Any]] = []
    for ev_id, reg in sorted(por_evento_id.items(), key=lambda x: x[0]):
        reg_limpo = {k: v for k, v in reg.items() if k != "_ts"}
        proc = reg_limpo["numero_processo"]
        prec = base_precatorios.get(proc)

        if prec:
            # Verifica se o pagamento ocorreu antes da data de apresentação
            apres_str = prec.get("apresentado_em")
            if apres_str and reg_limpo["data_pagamento"] < apres_str:
                resultado.duvidas.append(
                    RegistroAuditoria(
                        categoria="duvida",
                        origem="pagamentos.json vs apresentacoes.json",
                        identificador=ev_id,
                        campo="data_pagamento",
                        valor_original=reg_limpo["data_pagamento"],
                        valor_final=reg_limpo["data_pagamento"],
                        motivo=(
                            f"Data de pagamento ({reg_limpo['data_pagamento']}) do processo {proc} "
                            f"é anterior à data de apresentação ({apres_str})."
                        ),
                    )
                )

            if reg_limpo["tipo"] == "pagamento":
                prec["total_pago_liquido"] += reg_limpo["valor"]
            elif reg_limpo["tipo"] == "estorno":
                prec["total_pago_liquido"] -= reg_limpo["valor"]
                resultado.corrigidos.append(
                    RegistroAuditoria(
                        categoria="corrigido",
                        origem="pagamentos.json",
                        identificador=ev_id,
                        campo="tipo",
                        valor_original=f"+{reg_limpo['valor']} (soma indevida)",
                        valor_final=f"-{reg_limpo['valor']} (estorno abatido)",
                        motivo=f"Evento de estorno ({ev_id}) subtraído do total pago do processo {proc}.",
                    )
                )

        reg_limpo["valor"] = str(reg_limpo["valor"])
        pagamentos_limpos.append(reg_limpo)

    return pagamentos_limpos


def executar_pipeline_limpeza(diretorio_dados: Path, diretorio_saida: Path | None = None) -> ResultadoLimpeza:
    """Executa a limpeza completa sobre os arquivos originais sem modificá-los
    e salva a base limpa e o relatório no diretório de saída (se fornecido).
    """
    resultado = ResultadoLimpeza()

    apresentacoes = carregar_apresentacoes(diretorio_dados / "apresentacoes.json", resultado)
    hub = carregar_hub(diretorio_dados / "hub.csv", resultado)
    tribunal = carregar_tribunal(diretorio_dados / "tribunal.csv", resultado)

    base_precatorios = conciliar_precatorios(apresentacoes, hub, tribunal, resultado)
    pagamentos_limpos = limpar_pagamentos(diretorio_dados / "pagamentos.json", base_precatorios, resultado)

    precatorios_lista: list[dict[str, Any]] = []
    for proc in sorted(base_precatorios):
        item = dict(base_precatorios[proc])
        item["valor_face"] = str(item["valor_face"])
        item["total_pago_liquido"] = str(item["total_pago_liquido"])
        precatorios_lista.append(item)

    resultado.precatorios = precatorios_lista
    resultado.pagamentos = pagamentos_limpos

    if diretorio_saida is not None:
        salvar_artefatos_saida(resultado, diretorio_saida)

    return resultado


def salvar_artefatos_saida(resultado: ResultadoLimpeza, diretorio_saida: Path) -> None:
    diretorio_saida.mkdir(parents=True, exist_ok=True)

    # 1. precatorios_limpos.csv
    campos_prec = [
        "numero_processo",
        "ente_devedor",
        "valor_face",
        "apresentado_em",
        "prazo_pagamento",
        "total_pago_liquido",
        "status_conciliacao",
    ]
    with (diretorio_saida / "precatorios_limpos.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos_prec)
        writer.writeheader()
        writer.writerows(resultado.precatorios)

    # 2. pagamentos_limpos.json
    (diretorio_saida / "pagamentos_limpos.json").write_text(
        json.dumps(resultado.pagamentos, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # 3. relatorio_limpeza.json
    relatorio_json = {
        "resumo": {
            "total_precatorios_limpos": len(resultado.precatorios),
            "total_eventos_pagamento_validos": len(resultado.pagamentos),
            "total_corrigidos": len(resultado.corrigidos),
            "total_descartados": len(resultado.descartados),
            "total_em_duvida": len(resultado.duvidas),
        },
        "corrigidos": [asdict(r) for r in resultado.corrigidos],
        "descartados": [asdict(r) for r in resultado.descartados],
        "duvidas": [asdict(r) for r in resultado.duvidas],
    }
    (diretorio_saida / "relatorio_limpeza.json").write_text(
        json.dumps(relatorio_json, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # 4. relatorio_limpeza.md
    linhas_md = [
        "# Relatório de Auditoria — Limpeza e Conciliação de Dados",
        "",
        "Relatório gerado automaticamente pelo pipeline de saneamento (`src/limpeza.py`) a partir dos arquivos brutos de `case-candidato/dados/`.",
        "",
        "## 1. Resumo Executivo",
        "",
        "| Métrica de Processamento | Quantidade | Descrição |",
        "|---|---:|---|",
        f"| **Precatórios Consolidados** | `{len(resultado.precatorios)}` | Base unificada (`output/precatorios_limpos.csv`) após cruzamento Hub, Tribunal e Apresentações. |",
        f"| **Eventos Financeiros Válidos** | `{len(resultado.pagamentos)}` | Pagamentos e estornos normalizados e deduplicados (`output/pagamentos_limpos.json`). |",
        f"| **Transformações / Correções** | `{len(resultado.corrigidos)}` | Normalizações de máscara CNJ, encoding, datas, fuso horário, valores PT-BR, retificações e estornos. |",
        f"| **Registros Descartados** | `{len(resultado.descartados)}` | Eventos inválidos (duplicatas exatas, valores nulos/negativos ou sem processo). |",
        f"| **Itens em Dúvida (Revisão)** | `{len(resultado.duvidas)}` | Divergências cadastrais ou anomalias que requerem validação de negócio/tribunal. |",
        "",
        "## 2. Base Consolidada de Precatórios (`precatorios_limpos.csv`)",
        "",
        "| Processo (CNJ) | Ente Devedor | Valor de Face (R$) | Apresentado em (BRT) | Prazo Constitucional | Total Pago Líquido (R$) | Status |",
        "|---|---|---:|---|---|---:|---|",
    ]
    for p in resultado.precatorios:
        linhas_md.append(
            f"| `{p['numero_processo']}` | {p['ente_devedor']} | {p['valor_face']} | "
            f"`{p['apresentado_em']}` | `{p['prazo_pagamento']}` | {p['total_pago_liquido']} | `{p['status_conciliacao']}` |"
        )

    linhas_md.extend(
        [
            "",
            "## 3. Eventos Financeiros Limpos (`pagamentos_limpos.json`)",
            "",
            "| Evento ID | Processo (CNJ) | Tipo | Valor (R$) | Data Pagamento | Atualizado em |",
            "|---|---|---|---:|---|---|",
        ]
    )
    for ev in resultado.pagamentos:
        linhas_md.append(
            f"| `{ev['evento_id']}` | `{ev['numero_processo']}` | `{ev['tipo']}` | "
            f"{ev['valor']} | `{ev['data_pagamento']}` | `{ev['atualizado_em']}` |"
        )

    linhas_md.extend(
        [
            "",
            "## 4. Registros Corrigidos (Transformações Aplicadas)",
            "",
            "| Origem | Identificador | Campo | Valor Original | Valor Final | Motivo da Correção |",
            "|---|---|---|---|---|---|",
        ]
    )
    for r in resultado.corrigidos:
        linhas_md.append(
            f"| `{r.origem}` | `{r.identificador}` | `{r.campo}` | `{r.valor_original}` | `{r.valor_final}` | {r.motivo} |"
        )

    linhas_md.extend(
        [
            "",
            "## 5. Registros Descartados (Quarentena)",
            "",
            "| Origem | Identificador | Campo | Valor Original | Motivo do Descarte |",
            "|---|---|---|---|---|",
        ]
    )
    for r in resultado.descartados:
        linhas_md.append(
            f"| `{r.origem}` | `{r.identificador}` | `{r.campo}` | `{r.valor_original}` | {r.motivo} |"
        )

    linhas_md.extend(
        [
            "",
            "## 6. Registros em Dúvida (Fila de Alinhamento)",
            "",
            "| Origem | Identificador | Campo | Valor Original | Valor Adotado | Justificativa / Ponto de Atenção |",
            "|---|---|---|---|---|---|",
        ]
    )
    for r in resultado.duvidas:
        linhas_md.append(
            f"| `{r.origem}` | `{r.identificador}` | `{r.campo}` | `{r.valor_original}` | `{r.valor_final}` | {r.motivo} |"
        )

    (diretorio_saida / "relatorio_limpeza.md").write_text("\n".join(linhas_md) + "\n", encoding="utf-8")
