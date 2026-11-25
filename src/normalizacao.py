import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

TZ_BRASILIA = ZoneInfo("America/Sao_Paulo")

# Mapa canônico de entes devedores conhecidos (chave normalizada sem acento/caixa alta -> nome oficial)
ENTES_CANONICOS: dict[str, str] = {
    "MUNICIPIO DE SAO PAULO": "Município de São Paulo",
    "ESTADO DE SAO PAULO": "Estado de São Paulo",
    "MUNICIPIO DE SANTOS": "Município de Santos",
    "UNIAO": "União",
}

CNJ_DIGITS_RE = re.compile(r"^\d{20}$")
CNJ_FORMAT_RE = re.compile(r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")


def remover_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


class Normalizacao:
    """Regras de normalização e validação de precatórios e eventos de pagamento."""

    @staticmethod
    def processo(valor: str | None) -> tuple[str | None, bool]:
        """Normaliza um número de processo para o padrão CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO).

        Retorna (processo_normalizado, foi_alterado).
        Se inválido ou vazio, retorna (None, False).
        """
        if valor is None:
            return None, False
        original = str(valor).strip()
        if not original:
            return None, False

        if CNJ_FORMAT_RE.match(original):
            return original, False

        apenas_digitos = re.sub(r"\D", "", original)
        if not CNJ_DIGITS_RE.match(apenas_digitos):
            return None, False

        formatado = (
            f"{apenas_digitos[0:7]}-{apenas_digitos[7:9]}."
            f"{apenas_digitos[9:13]}.{apenas_digitos[13:14]}."
            f"{apenas_digitos[14:16]}.{apenas_digitos[16:20]}"
        )
        return formatado, formatado != original

    @staticmethod
    def ente(nome: str | None) -> tuple[str | None, bool]:
        """Padroniza o nome do ente devedor removendo variações de caixa e acentuação.

        Retorna (ente_padronizado, foi_alterado).
        """
        if nome is None:
            return None, False
        original = str(nome).strip()
        if not original:
            return None, False

        chave = " ".join(remover_acentos(original).upper().split())
        padronizado = ENTES_CANONICOS.get(chave, original)
        return padronizado, padronizado != original

    @staticmethod
    def valor_monetario(valor: str | int | float | Decimal | None) -> tuple[Decimal | None, bool]:
        """Converte valores monetários (float, int, string ISO ou string PT-BR '2.500,50') para Decimal(2 casas).

        Retorna (valor_decimal, foi_convertido_de_string_ptbr).
        """
        if valor is None or isinstance(valor, bool):
            return None, False

        if isinstance(valor, Decimal):
            return valor.quantize(Decimal("0.01")), False

        if isinstance(valor, (int, float)):
            return Decimal(str(valor)).quantize(Decimal("0.01")), False

        texto = str(valor).strip()
        if not texto:
            return None, False

        foi_ptbr = False
        if "," in texto:
            # Formato brasileiro: "2.500,50" ou "45.000,00"
            texto = texto.replace(".", "").replace(",", ".")
            foi_ptbr = True

        try:
            dec = Decimal(texto).quantize(Decimal("0.01"))
            return dec, foi_ptbr
        except InvalidOperation:
            return None, False

    @staticmethod
    def data_iso(valor: str | None) -> tuple[date | None, bool]:
        """Converte uma data em 'AAAA-MM-DD' ou 'DD/MM/AAAA' para datetime.date.

        Retorna (data, foi_convertida_de_dd_mm_aaaa).
        """
        if valor is None:
            return None, False
        texto = str(valor).strip()
        if not texto:
            return None, False

        # Tenta formato oficial AAAA-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", texto):
            try:
                return date.fromisoformat(texto), False
            except ValueError:
                return None, False

        # Tenta formato brasileiro DD/MM/AAAA
        if re.match(r"^\d{2}/\d{2}/\d{4}$", texto):
            try:
                dt = datetime.strptime(texto, "%d/%m/%Y").date()
                return dt, True
            except ValueError:
                return None, False

        return None, False

    @staticmethod
    def apresentado_em_prazo(valor: str | None) -> tuple[date | None, date | None, bool]:
        """Extrai a data civil de apresentação no fuso de Brasília (America/Sao_Paulo)
        e calcula o prazo constitucional de pagamento:
          - Apresentado até 2 de abril (inclusive) do ano A -> paga até 31/12/(A + 1)
          - Apresentado após 2 de abril do ano A           -> paga até 31/12/(A + 2)

        Retorna (data_apresentacao_brt, prazo_pagamento, teve_conversao_timestamp_ou_tz).
        """
        if valor is None:
            return None, None, False
        texto = str(valor).strip()
        if not texto:
            return None, None, False

        teve_timestamp = False
        if re.match(r"^\d{4}-\d{2}-\d{2}$", texto):
            try:
                data_apresentacao = date.fromisoformat(texto)
            except ValueError:
                return None, None, False
        else:
            try:
                dt = datetime.fromisoformat(texto)
                if dt.tzinfo is not None:
                    dt = dt.astimezone(TZ_BRASILIA)
                data_apresentacao = dt.date()
                teve_timestamp = True
            except ValueError:
                return None, None, False

        corte = date(data_apresentacao.year, 4, 2)
        if data_apresentacao <= corte:
            ano_vencimento = data_apresentacao.year + 1
        else:
            ano_vencimento = data_apresentacao.year + 2

        prazo = date(ano_vencimento, 12, 31)
        return data_apresentacao, prazo, teve_timestamp


# Mantém alias em minúsculo para compatibilidade com o rascunho inicial
normalizacao = Normalizacao
