"""
Gera arquivos .txt por grupo de produto para indexação no RAG.

Fonte: produtos_informações_sem_inox.xlsx
Saída: knowledge/catalog_groups/<grupo>.txt (22 arquivos)

Executar:
    python scripts/generate_catalog_rag.py --source /caminho/para/planilha.xlsx
"""
import sys
import argparse
from pathlib import Path

# Índices das colunas na planilha produtos_informações_sem_inox.xlsx
_COL_SAP = 1
_COL_DESC = 3
_COL_PESO = 6
_COL_LARGURA = 7
_COL_COMPRIMENTO = 8
_COL_GRUPO = 9
_COL_SUBGRUPO = 10

# Metadados de aplicação por grupo (enriquecimento manual — não está na planilha)
APLICACOES_POR_GRUPO = {
    "CA-50": (
        "Vergalhão de aço carbono CA-50 para construção civil. "
        "Usado em estruturas de concreto armado.",
        "Lajes, vigas, pilares, fundações, sapatas, cintas de amarração, "
        "escadas, muros de contenção."
    ),
    "CA-60": (
        "Vergalhão de aço carbono CA-60 de alta resistência. "
        "Permite uso de bitolas menores com mesma resistência.",
        "Pilares, estruturas de alta carga, obras especiais, "
        "construções que demandam maior resistência mecânica."
    ),
    "Telha": (
        "Telhas metálicas galvanizadas para cobertura industrial e residencial.",
        "Galpões industriais, armazéns, coberturas residenciais, "
        "agropecuária, postos de gasolina, feiras."
    ),
    "Tubo": (
        "Tubos de aço carbono para estruturas e conduções industriais.",
        "Estruturas metálicas, móveis (camas, armários), grades, "
        "cercas, conduções de fluidos, construção civil."
    ),
    "Barra Laminada": (
        "Barras de aço laminadas a quente em diferentes perfis.",
        "Serralheria, grades, portões, escadas, estruturas leves, "
        "reforço de alvenaria, fabricação de ferramentas."
    ),
    "Perfis": (
        "Perfis de aço conformados a frio para estruturas e acabamentos.",
        "Drywall, galpões, mezaninos, estruturas leves, "
        "forros, divisórias, sistemas construtivos industrializados."
    ),
    "Perfil W": (
        "Perfis W (duplo T) laminados para estruturas pesadas.",
        "Galpões de grande vão, pontes rolantes, mezaninos pesados, "
        "estruturas industriais de alta carga."
    ),
    "Chapa A-36": (
        "Chapas grossas de aço A-36 para uso estrutural e industrial.",
        "Tanques, reservatórios, estruturas navais, implementos agrícolas, "
        "equipamentos industriais, caldeiras."
    ),
    "Chapa Plana": (
        "Chapas planas de aço para corte e dobramento.",
        "Estamparia, fabricação de peças, fechamento de estruturas, "
        "painéis, caixas metálicas, peças sob medida."
    ),
    "Bobina": (
        "Bobinas de aço laminado a frio e quente.",
        "Indústria metalmecânica, estamparia, fabricação de peças, "
        "alimentação de linhas de produção automatizadas."
    ),
    "Bobina Slitter": (
        "Bobinas fendidas (slitadas) em larguras menores.",
        "Perfis, tubos, arames, peças estampadas de largura específica."
    ),
    "Bobininha": (
        "Bobinas de aço em formato reduzido para uso industrial e artesanal.",
        "Pequenas peças, artesanato em metal, mola, molas industriais."
    ),
    "Tela": (
        "Telas soldadas de aço para lajes e pisos.",
        "Lajes nervuradas, pisos industriais, calçadas de concreto, "
        "piscinas, revestimentos."
    ),
    "Tela Coluna": (
        "Telas especiais para reforço de colunas e pilares.",
        "Reforço de pilares de concreto armado, colunas estruturais."
    ),
    "Trelica": (
        "Treliças de aço para lajes treliçadas.",
        "Lajes treliçadas (sistema EPS + treliça), "
        "lajes de concreto para construção civil residencial e comercial."
    ),
    "Arame": (
        "Arames de aço para amarração e uso industrial.",
        "Amarração de vergalhões, construção civil, cercas, embalagens, "
        "artesanato, uso agrícola."
    ),
    "FM": (
        "Fio-máquina de aço para trefilação industrial.",
        "Fabricação de parafusos, porcas, arames, molas, "
        "eletrodos de solda, produtos trefilados."
    ),
    "Caixilho": (
        "Perfis para esquadrias e caixilharia metálica.",
        "Janelas, portas, portões, grades, esquadrias metálicas."
    ),
    "Lambril": (
        "Chapas onduladas para fechamento e cobertura.",
        "Fechamento lateral de galpões, cercas, muros, "
        "cobertura secundária, proteção contra vento."
    ),
    "Articulada": (
        "Telas articuladas para cercamento rural.",
        "Cercas para fazendas, pastagens, propriedades rurais, "
        "contenção de animais."
    ),
    "Tarugo": (
        "Tarugos de aço para usinagem e forjamento.",
        "Fabricação de eixos, buchas, pinos, peças usinadas, "
        "ferramentaria, indústria metalúrgica."
    ),
    "Sucata": (
        "Sucata de aço para reciclagem industrial.",
        "Reciclagem, reaproveitamento, indústrias siderúrgicas."
    ),
}


def slugify(nome: str) -> str:
    """Converte nome do grupo em nome de arquivo válido."""
    return (
        nome.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ç", "c")
        .replace("ó", "o")
        .replace("í", "i")
        .replace("ú", "u")
        .replace("â", "a")
        .replace("ê", "e")
    )


def gerar_catalogo(source_path: str, output_dir: str = "knowledge/catalog_groups"):
    try:
        import openpyxl
    except ImportError:
        print("ERRO: openpyxl não instalado. Execute: pip install openpyxl")
        sys.exit(1)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    print(f"Lendo planilha: {source_path}")
    wb = openpyxl.load_workbook(source_path)
    ws = wb.active

    # Coletar produtos por grupo
    grupos: dict = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        grupo = row[_COL_GRUPO]
        if not grupo:
            continue

        if grupo not in grupos:
            grupos[grupo] = {"subgrupos": {}, "exemplos": []}

        subgrupo = row[_COL_SUBGRUPO] or ""
        if subgrupo and subgrupo not in grupos[grupo]["subgrupos"]:
            grupos[grupo]["subgrupos"][subgrupo] = []

        # Guardar até 8 exemplos por grupo
        if len(grupos[grupo]["exemplos"]) < 8:
            grupos[grupo]["exemplos"].append({
                "cod": row[_COL_SAP],
                "desc": row[_COL_DESC],
                "peso": row[_COL_PESO],
                "largura": row[_COL_LARGURA],
                "comprimento": row[_COL_COMPRIMENTO],
                "subgrupo": subgrupo,
            })

        # Guardar até 3 exemplos por subgrupo
        if subgrupo and len(grupos[grupo]["subgrupos"][subgrupo]) < 3:
            grupos[grupo]["subgrupos"][subgrupo].append(row[_COL_DESC])

    print(f"Grupos encontrados: {len(grupos)}")

    for grupo, dados in grupos.items():
        desc, aplicacoes = APLICACOES_POR_GRUPO.get(
            grupo,
            (f"Produtos do grupo {grupo}.", "Uso industrial e comercial.")
        )

        linhas = [
            f"GRUPO: {grupo}",
            "",
            "DESCRIÇÃO:",
            desc,
            "",
            "APLICAÇÕES:",
            aplicacoes,
            "",
            "SUB-GRUPOS DISPONÍVEIS:",
        ]

        for subgrupo, exemplos in dados["subgrupos"].items():
            exemplos_str = ", ".join(exemplos[:2]) if exemplos else ""
            linhas.append(f"- {subgrupo}: {exemplos_str}")

        linhas += [
            "",
            "PRODUTOS REPRESENTATIVOS:",
        ]

        for ex in dados["exemplos"]:
            peso = f"{ex['peso']}kg/un" if ex["peso"] else ""
            dims = " | ".join(filter(None, [
                str(ex.get("largura") or ""),
                str(ex.get("comprimento") or ""),
            ]))
            linha = f"- Cód {ex['cod']}: {ex['desc']}"
            if dims:
                linha += f" [{dims}]"
            if peso:
                linha += f" — {peso}"
            linhas.append(linha)

        arquivo = output / f"{slugify(grupo)}.txt"
        arquivo.write_text("\n".join(linhas), encoding="utf-8")
        print(f"  Gerado: {arquivo.name} ({len(dados['exemplos'])} produtos, {len(dados['subgrupos'])} sub-grupos)")

    print(f"\nTotal de arquivos gerados: {len(grupos)} em {output}/")


def main():
    parser = argparse.ArgumentParser(description="Gera arquivos .txt do catálogo por grupo para RAG")
    parser.add_argument(
        "--source",
        required=True,
        help="Caminho para a planilha de produtos (ex: /path/to/produtos_informações_sem_inox.xlsx)",
    )
    parser.add_argument(
        "--output",
        default="knowledge/catalog_groups",
        help="Diretório de saída dos arquivos .txt",
    )
    args = parser.parse_args()
    gerar_catalogo(args.source, args.output)


if __name__ == "__main__":
    main()
