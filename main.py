from pathlib import Path

from src.limpeza import executar_pipeline_limpeza


def main() -> None:
    raiz = Path(__file__).resolve().parent
    diretorio_dados = raiz / "case-candidato" / "dados"
    diretorio_saida = raiz / "output"

    resultado = executar_pipeline_limpeza(diretorio_dados, diretorio_saida)

    print("=== Limpeza e Conciliação Concluídas ===")
    print(f"Arquivos gerados em: {diretorio_saida}")
    print(f"- Precatórios consolidados : {len(resultado.precatorios)}")
    print(f"- Eventos válidos          : {len(resultado.pagamentos)}")
    print(f"- Correções aplicadas      : {len(resultado.corrigidos)}")
    print(f"- Registros descartados    : {len(resultado.descartados)}")
    print(f"- Registros em dúvida      : {len(resultado.duvidas)}")


if __name__ == "__main__":
    main()
