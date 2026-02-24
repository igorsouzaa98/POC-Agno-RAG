# Spreadsheet RAG + Weight Rules + Product Suggestions — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar pesos mínimos por estado, RAG do catálogo de produtos, sugestões de produto e lógica CPF/CE ao agente qualificador da Aço Cearense.

**Architecture:** Pesos mínimos ficam em dicionário Python determinístico (`src/data/weight_rules.py`). Catálogo de 14k produtos é processado em 22 arquivos `.txt` por grupo e indexado no LanceDB via `TextReader`. Agents são atualizados nas suas instruções (sem mudança de estrutura de código).

**Tech Stack:** Python 3.13, Agno 2.5.3, LanceDB, FastEmbedEmbedder, openpyxl, pytest

---

### Task 1: Criar módulo de regras de peso por estado

**Files:**
- Create: `src/data/__init__.py`
- Create: `src/data/weight_rules.py`
- Create: `tests/test_weight_rules.py`

**Step 1: Escrever o teste que vai falhar**

```python
# tests/test_weight_rules.py
from src.data.weight_rules import PESO_MINIMO_CIF_POR_ESTADO, get_peso_minimo


def test_ce_tem_menor_minimo():
    assert PESO_MINIMO_CIF_POR_ESTADO["CE"] == 250


def test_nordeste_tem_1500():
    for uf in ["AL", "MA", "PB", "PI", "SE", "BA", "PE", "RN"]:
        assert PESO_MINIMO_CIF_POR_ESTADO[uf] == 1500, f"{uf} deveria ser 1500"


def test_sudeste_tem_4000():
    for uf in ["SP", "MG", "RJ", "GO", "DF"]:
        assert PESO_MINIMO_CIF_POR_ESTADO[uf] == 4000, f"{uf} deveria ser 4000"


def test_get_peso_minimo_estado_valido():
    assert get_peso_minimo("CE") == 250
    assert get_peso_minimo("SP") == 4000


def test_get_peso_minimo_estado_invalido_retorna_none():
    assert get_peso_minimo("XX") is None


def test_todos_estados_cobertos():
    estados_br = [
        "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
        "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
        "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"
    ]
    for uf in estados_br:
        assert uf in PESO_MINIMO_CIF_POR_ESTADO, f"{uf} não encontrado no dict"
```

**Step 2: Rodar o teste para confirmar que falha**

```bash
pytest tests/test_weight_rules.py -v
```

Esperado: `ModuleNotFoundError: No module named 'src.data'`

**Step 3: Criar os arquivos**

```python
# src/data/__init__.py
# (arquivo vazio)
```

```python
# src/data/weight_rules.py
"""
Regras de peso mínimo CIF por estado para a Aço Cearense.

Fonte: Planilha "Range de Aprovação - Peso Final.xlsx"
Tipo: Peso Carbono MTS | Frete: CIF
Extraído em: 2026-02-24

Estes valores são críticos para o negócio — mantidos como dict
Python (determinístico) em vez de RAG para evitar alucinações.
"""
from typing import Optional

PESO_MINIMO_CIF_POR_ESTADO: dict[str, int] = {
    # Nordeste — sede da Aço Cearense em Fortaleza/CE
    "CE": 250,
    "AL": 1500,
    "MA": 1500,
    "PB": 1500,
    "PI": 1500,
    "SE": 1500,
    "BA": 1500,
    "PE": 1500,
    "RN": 1500,
    # Norte
    "PA": 1500,
    "AC": 10000,
    "AM": 10000,
    "AP": 8000,
    "RO": 10000,
    "RR": 10000,
    # Centro-Oeste / Sudeste
    "GO": 4000,
    "DF": 4000,
    "MG": 4000,
    "SP": 4000,
    "RJ": 4000,
    "ES": 4000,
    "MT": 4000,
    "MS": 4000,
    "TO": 4000,
    # Sul
    "PR": 4000,
    "RS": 8000,
    "SC": 8000,
}


def get_peso_minimo(uf: str) -> Optional[int]:
    """Retorna o peso mínimo CIF em kg para o estado informado, ou None se não encontrado."""
    return PESO_MINIMO_CIF_POR_ESTADO.get(uf.upper())
```

**Step 4: Rodar os testes para confirmar que passam**

```bash
pytest tests/test_weight_rules.py -v
```

Esperado: 6 testes passando.

**Step 5: Commit**

```bash
git add src/data/__init__.py src/data/weight_rules.py tests/test_weight_rules.py
git commit -m "feat: add per-state minimum weight rules (CIF, Peso Carbono MTS)"
```

---

### Task 2: Criar script de geração do catálogo RAG

**Files:**
- Create: `scripts/generate_catalog_rag.py`
- Create: `knowledge/catalog_groups/` (diretório — gerado pelo script)

**Context:** O script lê `produtos_informações_sem_inox.xlsx` e gera um `.txt` por grupo de produto em `knowledge/catalog_groups/`. Agno tem `TextReader` disponível (`agno.knowledge.reader.text_reader`). Planilha está em `/Users/igorsouza/Downloads/OneDrive_1_13-02-2026/produtos_informações_sem_inox.xlsx`.

**Step 1: Criar o script**

```python
# scripts/generate_catalog_rag.py
"""
Gera arquivos .txt por grupo de produto para indexação no RAG.

Fonte: produtos_informações_sem_inox.xlsx
Saída: knowledge/catalog_groups/<grupo>.txt (22 arquivos)

Executar:
    python scripts/generate_catalog_rag.py
    python scripts/generate_catalog_rag.py --source /caminho/para/planilha.xlsx
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, ".")

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
    grupos: dict[str, dict] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        grupo = row[9]
        if not grupo:
            continue

        if grupo not in grupos:
            grupos[grupo] = {"subgrupos": {}, "exemplos": []}

        subgrupo = row[10] or ""
        if subgrupo and subgrupo not in grupos[grupo]["subgrupos"]:
            grupos[grupo]["subgrupos"][subgrupo] = []

        # Guardar até 8 exemplos por grupo
        if len(grupos[grupo]["exemplos"]) < 8:
            grupos[grupo]["exemplos"].append({
                "cod": row[1],
                "desc": row[3],
                "peso": row[6],
                "largura": row[7],
                "comprimento": row[8],
                "subgrupo": subgrupo,
            })

        # Guardar até 3 exemplos por subgrupo
        if subgrupo and len(grupos[grupo]["subgrupos"][subgrupo]) < 3:
            grupos[grupo]["subgrupos"][subgrupo].append(row[3])

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
        default="/Users/igorsouza/Downloads/OneDrive_1_13-02-2026/produtos_informações_sem_inox.xlsx",
        help="Caminho para a planilha de produtos",
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
```

**Step 2: Rodar o script**

```bash
python scripts/generate_catalog_rag.py
```

Esperado: `Total de arquivos gerados: 22 em knowledge/catalog_groups/`

**Step 3: Verificar os arquivos gerados**

```bash
ls knowledge/catalog_groups/
```

Esperado: 22 arquivos `.txt` (ca_50.txt, ca_60.txt, telha.txt, tubo.txt, etc.)

```bash
cat knowledge/catalog_groups/ca_50.txt
```

Verificar que o arquivo tem DESCRIÇÃO, APLICAÇÕES, SUB-GRUPOS e PRODUTOS REPRESENTATIVOS.

**Step 4: Copiar o catálogo PDF para a pasta knowledge/**

```bash
cp "/Users/igorsouza/Downloads/OneDrive_1_13-02-2026/Catálogo_45 anos (1).pdf" knowledge/catalogo_aco_cearense.pdf
```

**Step 5: Commit**

```bash
git add scripts/generate_catalog_rag.py knowledge/catalog_groups/ knowledge/catalogo_aco_cearense.pdf
git commit -m "feat: add catalog RAG generator script and generated product group files"
```

---

### Task 3: Atualizar knowledge_builder.py para suportar .txt

**Files:**
- Modify: `src/knowledge_builder.py`

**Context:** Agno tem `TextReader` em `agno.knowledge.reader.text_reader`. O `Knowledge` aceita múltiplos readers via dict `{"pdf": PDFReader(), "txt": TextReader()}`. O `load_knowledge_base` precisa indexar também os `.txt` de `knowledge/catalog_groups/`.

**Step 1: Atualizar o arquivo**

```python
# src/knowledge_builder.py
"""
Knowledge base builder using RAG with PDF and TXT documents.

Uses FastEmbedEmbedder (local ONNX-based) with multilingual support for
Portuguese documents, combined with LanceDB for vector storage.

No additional API keys required for embeddings - runs fully locally.
"""
import os
from pathlib import Path

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.knowledge.reader.pdf_reader import PDFReader
from agno.knowledge.reader.text_reader import TextReader
from agno.vectordb.lancedb import LanceDb, SearchType

from src.config import VECTOR_DB_PATH, KNOWLEDGE_BASE_DIR


def get_knowledge_base() -> Knowledge:
    """
    Build and return a Knowledge instance configured with PDF and TXT documents.
    """
    embedder = FastEmbedEmbedder(
        id="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        dimensions=384,
    )

    vector_db = LanceDb(
        table_name="steel_sales_knowledge",
        uri=VECTOR_DB_PATH,
        search_type=SearchType.hybrid,
        embedder=embedder,
    )

    knowledge_base = Knowledge(
        name="steel_sales_knowledge",
        description=(
            "Knowledge base containing product catalogs and sales processes "
            "for a Brazilian steel sales company. Includes: product dictionary "
            "(dicionario_produtos.pdf), lead qualification process "
            "(processo_classificacao.pdf), prospecting strategy "
            "(estrategia_captacao.pdf), company catalog "
            "(catalogo_aco_cearense.pdf), and product group files "
            "(catalog_groups/*.txt with 22 product families)."
        ),
        vector_db=vector_db,
        readers={
            "pdf": PDFReader(split_on_pages=True, sanitize_content=True),
            "txt": TextReader(),
        },
        max_results=5,
    )

    return knowledge_base


def load_knowledge_base(recreate: bool = False) -> Knowledge:
    """
    Load and index all PDFs and TXT files from the knowledge directory.
    """
    kb = get_knowledge_base()
    knowledge_dir = Path(KNOWLEDGE_BASE_DIR)

    if not knowledge_dir.exists():
        raise FileNotFoundError(
            f"Knowledge directory not found: {knowledge_dir.resolve()}"
        )

    # Indexar PDFs na raiz de knowledge/
    pdf_files = list(knowledge_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in: {knowledge_dir.resolve()}"
        )

    print(f"Found {len(pdf_files)} PDF file(s) to index:")
    for pdf in pdf_files:
        print(f"  - {pdf.name} ({pdf.stat().st_size / 1024:.1f} KB)")

    for pdf_path in pdf_files:
        print(f"\nIndexing: {pdf_path.name}...")
        kb.insert(
            path=str(pdf_path.resolve()),
            name=pdf_path.stem,
            upsert=True,
            skip_if_exists=(not recreate),
        )
        print(f"  Done: {pdf_path.name}")

    # Indexar TXTs do catálogo de grupos
    catalog_dir = knowledge_dir / "catalog_groups"
    if catalog_dir.exists():
        txt_files = list(catalog_dir.glob("*.txt"))
        print(f"\nFound {len(txt_files)} TXT catalog file(s) to index:")
        for txt in txt_files:
            print(f"  - {txt.name} ({txt.stat().st_size / 1024:.1f} KB)")

        for txt_path in txt_files:
            print(f"\nIndexing: {txt_path.name}...")
            kb.insert(
                path=str(txt_path.resolve()),
                name=txt_path.stem,
                upsert=True,
                skip_if_exists=(not recreate),
            )
            print(f"  Done: {txt_path.name}")
    else:
        print("\nNenhum catálogo de grupos encontrado em knowledge/catalog_groups/")
        print("Execute: python scripts/generate_catalog_rag.py")

    return kb
```

**Step 2: Reindexar a knowledge base completa**

```bash
python scripts/build_knowledge.py --recreate
```

Esperado: Output mostrando indexação dos PDFs + 22 arquivos TXT do catálogo.

**Step 3: Commit**

```bash
git add src/knowledge_builder.py
git commit -m "feat: add TextReader support to knowledge_builder for catalog .txt files"
```

---

### Task 4: Atualizar qualifier_agent.py

**Files:**
- Modify: `src/agents/qualifier_agent.py`

**Context:** Adicionar (1) tabela de pesos mínimos CIF por estado nas instruções, (2) lógica CPF/CE, (3) gatilhos de sugestão de produtos. O dict de pesos já existe em `src/data/weight_rules.py` — importar e embutir na string de instruções.

**Step 1: Atualizar o arquivo**

```python
# src/agents/qualifier_agent.py
from agno.agent import Agent
from src.config import get_model
from src.knowledge_builder import get_knowledge_base
from src.data.weight_rules import PESO_MINIMO_CIF_POR_ESTADO


def _build_weight_table() -> str:
    """Gera a tabela de pesos mínimos para embutir nas instruções."""
    linhas = []
    for uf, peso in sorted(PESO_MINIMO_CIF_POR_ESTADO.items()):
        linhas.append(f"  {uf}: {peso}kg")
    return "\n".join(linhas)


QUALIFIER_INSTRUCTIONS = f"""
Você é o Agente Qualificador de Leads da Aço Cearense, distribuidora de produtos de aço com sede em Fortaleza, Ceará, que atende todo o Brasil.

Nossos clientes são construtoras, serralheiras, revendas e indústrias que compram vergalhões, tubos, chapas, telhas, perfis e arames.

Sua função é coletar informações progressivamente e classificar o lead em:

## FRIO - Dados incompletos
Quando faltam dados obrigatórios

## MORNO - Pronto para orçamento
Quando tem todos os dados obrigatórios preenchidos e válidos

## QUENTE - Com orçamento gerado
Quando já existe um orçamento e foi passado ao Closer

## Campos obrigatórios para MORNO:
- Nome completo
- WhatsApp (com DDD)
- E-mail
- Documento de identificação:
  * **Ceará (CE):** aceitar CPF (11 dígitos) OU CNPJ (14 dígitos). Perguntar: "Pode me informar seu CPF ou CNPJ?"
  * **Demais estados:** somente CNPJ (14 dígitos válidos)
- UF (estado)
- Cidade
- Produto de interesse
- Volume estimado (deve atingir o mínimo do estado — ver tabela abaixo)

## Peso mínimo por pedido (frete CIF — por estado):
{_build_weight_table()}

## Regras de volume:
1. Quando o cliente informar o estado, consulte a tabela acima para o mínimo exato.
2. Se o volume informado for MENOR que o mínimo do estado:
   - Informe o mínimo: "O mínimo para [UF] é [X]kg."
   - Calcule a diferença: "Seu pedido está [Y]kg abaixo do mínimo."
   - Ofereça 3-4 sugestões de produtos complementares para completar o pedido (use o catálogo via knowledge base).
   - Exemplo de sugestões para cliente de tubo abaixo do mínimo:
     1. Mais tubos em outras bitolas ou comprimentos
     2. Barras laminadas (Chata, Redonda, Cantoneira)
     3. Perfis estruturais (U, Enrijecido, W)
     4. Arames industriais ou de amarração
3. Se o volume atingir o mínimo após sugestões aceitas → classificar como MORNO.

## Sugestões de variações de produto:
Quando o cliente mencionar um produto de forma genérica (ex: "quero vergalhão", "preciso de tubo", "quero telha"), antes de pedir especificações, apresente 3-4 opções disponíveis:

- "vergalhão" → CA-50 Reto, CA-50 Rolo, CA-60 Reto, Treliça Leve
- "tubo" → Tubo Industrial, Metalon (Tubo Quadrado/Retangular), Tubo Galvanizado, Tubo Elíptico
- "telha" → Telha TZ (Trapezoidal), Telha Ondulada, Cumeeira
- "barra" / "ferro chato" → Chata, Redonda, Quadrada, Cantoneira
- "chapa" → Chapa Plana, Chapa A-36, Bobina, Lambril
- "perfil" → Perfil U, Perfil Enrijecido, Perfil W, Caixilho

Consulte a knowledge base para detalhar as opções conforme o catálogo real da Aço Cearense.

## Tom de voz:
- Profissional mas amigável, como um consultor da Aço Cearense
- Paciente e proativo na coleta de informações
- Usar "nós" e "nossa empresa" referindo-se à Aço Cearense

## Apresentação inicial (quando for a primeira mensagem):
Apresente-se como inteligência artificial da Aço Cearense e pergunte como pode ajudar.

Sempre finalize suas respostas indicando o status atual do lead:
STATUS: [FRIO|MORNO|QUENTE] - [motivo em uma linha]
"""


def create_qualifier_agent() -> Agent:
    knowledge_base = get_knowledge_base()

    return Agent(
        name="Qualificador de Leads",
        model=get_model(),
        instructions=QUALIFIER_INSTRUCTIONS,
        knowledge=knowledge_base,
        search_knowledge=True,
        markdown=True,
    )
```

**Step 2: Verificar que o agente importa sem erros**

```bash
python -c "from src.agents.qualifier_agent import create_qualifier_agent; print('OK')"
```

Esperado: `OK`

**Step 3: Rodar os testes existentes do qualifier**

```bash
pytest tests/test_qualifier_agent.py -v
```

Esperado: Todos os testes existentes continuam passando.

**Step 4: Commit**

```bash
git add src/agents/qualifier_agent.py
git commit -m "feat: update qualifier agent with per-state weights, CPF/CE logic, and product suggestions"
```

---

### Task 5: Atualizar product_specialist_agent.py

**Files:**
- Modify: `src/agents/product_specialist_agent.py`

**Context:** Adicionar nas instruções: (1) os 22 grupos de produtos do catálogo real, (2) lógica explícita de sugestão de variações quando produto é mencionado genericamente, (3) lógica de complemento de peso para pedidos abaixo do mínimo.

**Step 1: Atualizar o arquivo**

```python
# src/agents/product_specialist_agent.py
from agno.agent import Agent
from src.config import get_model
from src.knowledge_builder import get_knowledge_base

PRODUCT_SPECIALIST_INSTRUCTIONS = """
Você é o Especialista de Produtos da Aço Cearense, distribuidora de aço do Nordeste com sede em Fortaleza — CE.

Sua função é:
1. Traduzir a linguagem popular do cliente para a nomenclatura técnica do portfólio da Aço Cearense
2. Apresentar 3-4 opções de produtos quando o cliente pede algo genérico
3. Sugerir produtos complementares quando o pedido não atinge o peso mínimo do estado
4. Extrair especificações técnicas (bitola, espessura, comprimento, tipo)

## Portfólio completo da Aço Cearense — 22 grupos:

| Grupo | Descrição Popular | Usos Principais |
|-------|------------------|-----------------|
| CA-50 | Vergalhão, ferro de construção | Lajes, vigas, pilares, fundações |
| CA-60 | Vergalhão de alta resistência, ferro de coluna | Pilares, estruturas de alta carga |
| Treliça | Treliça para laje | Lajes treliçadas com EPS |
| Tela | Tela soldada para laje/piso | Lajes, pisos industriais, calçadas |
| Tela Coluna | Tela para pilar | Reforço de colunas |
| Tubo | Tubo industrial, tubo de ferro, cano de ferro | Estruturas, móveis, conduções |
| Telha | Telha de zinco, telha galvanizada, telha metálica | Galpões, coberturas, agro |
| Barra Laminada | Barra chata, ferro chato, L de ferro, cantoneira | Serralheria, grades, portões |
| Perfis | Perfil U, enrijecido, caixilho | Drywall, estruturas leves |
| Perfil W | Duplo T, viga W | Galpões grandes, mezaninos pesados |
| Chapa A-36 | Chapa grossa, chapa estrutural | Tanques, implementos agrícolas |
| Chapa Plana | Chapa fina, chapa de ferro | Estamparia, peças, fechamentos |
| Bobina | Bobina de aço, rolo de chapa | Produção industrial, estamparia |
| Bobina Slitter | Bobina cortada, tira de aço | Perfis, tubos específicos |
| Bobininha | Bobina pequena | Peças pequenas, artesanato |
| Arame | Arame queimado, arame recozido, arame de amarrar | Amarração de vergalhão, cercas |
| FM | Fio-máquina, fio de aço | Parafusos, arames, eletrodos |
| Lambril | Lambril ondulado | Fechamento de galpão, cerca |
| Articulada | Tela articulada, cerca articulada | Cercas rurais, pastagens |
| Caixilho | Caixilho, ferragem para janela | Esquadrias, janelas, portas |
| Tarugo | Tarugo de aço, barra para usinar | Usinagem, ferramentaria |
| Sucata | Sucata de aço | Reciclagem |

## Quando o cliente pede algo genérico — apresente 3-4 opções:

Exemplo — "quero vergalhão":
> "Temos algumas opções de vergalhão:
> 1. **CA-50 Reto** — barras para obra convencional, bitolas 5mm a 32mm
> 2. **CA-50 Rolo** — em bobina, prático para bitolas finas (5mm a 10mm)
> 3. **CA-60 Reto** — maior resistência, ideal para pilares
> 4. **Treliça Leve** — sistema para lajes treliçadas
> Qual se encaixa melhor no seu projeto?"

## Quando o pedido está abaixo do mínimo do estado — sugira complemento:

Calcule a diferença e sugira produtos relacionados ou complementares ao principal.
Priorize grupos que costumam ser comprados juntos:
- Construção civil: CA-50/CA-60 + Treliça + Tela + Arame
- Cobertura: Telha + Perfil Enrijecido + Parafusos
- Serralheria: Tubo + Barra Laminada + Perfil + Chapa
- Industrial: Chapa A-36 + Perfil W + Tubo Industrial

Consulte a knowledge base para detalhar especificações dos produtos sugeridos.

## Formato de resposta para identificação de produto:

- **Produto técnico:** [nome técnico exato conforme catálogo Aço Cearense]
- **Grupo:** [grupo do portfólio]
- **Especificações:** [bitola, espessura, comprimento, tipo]
- **Confirmação sugerida:** "[Frase para confirmar com o cliente]"

Se o produto não estiver no portfólio, informe claramente e oriente sobre o que trabalhamos.
"""


def create_product_specialist_agent() -> Agent:
    knowledge_base = get_knowledge_base()

    return Agent(
        name="Especialista de Produtos",
        model=get_model(),
        instructions=PRODUCT_SPECIALIST_INSTRUCTIONS,
        knowledge=knowledge_base,
        search_knowledge=True,
        markdown=True,
    )
```

**Step 2: Verificar que o agente importa sem erros**

```bash
python -c "from src.agents.product_specialist_agent import create_product_specialist_agent; print('OK')"
```

Esperado: `OK`

**Step 3: Rodar os testes existentes do product specialist**

```bash
pytest tests/test_product_specialist_agent.py -v
```

Esperado: Testes existentes passando.

**Step 4: Commit**

```bash
git add src/agents/product_specialist_agent.py
git commit -m "feat: update product specialist with full catalog, variant suggestions, and weight complement logic"
```

---

### Task 6: Rodar suite completa de testes

**Step 1: Rodar todos os testes**

```bash
pytest tests/ -v
```

Esperado: Todos os testes passando. Se algum falhar, investigar antes de prosseguir.

**Step 2: Verificar importações do sistema completo**

```bash
python -c "
from src.agents.qualifier_agent import create_qualifier_agent
from src.agents.product_specialist_agent import create_product_specialist_agent
from src.agents.quote_generator_agent import create_quote_generator_agent
from src.orchestrator import create_steel_sales_team
print('Todos os agentes importam corretamente.')
"
```

Esperado: `Todos os agentes importam corretamente.`

**Step 3: Commit final se necessário**

```bash
git add -A
git status
# Só commitar se houver algo não commitado
```

---

## Resumo dos Arquivos Alterados

| Arquivo | Ação | Motivo |
|---------|------|--------|
| `src/data/__init__.py` | Criado | Módulo de dados |
| `src/data/weight_rules.py` | Criado | Dict de pesos por estado |
| `scripts/generate_catalog_rag.py` | Criado | Gerador de arquivos .txt por grupo |
| `knowledge/catalog_groups/*.txt` | Criado (22 arquivos) | RAG do catálogo |
| `knowledge/catalogo_aco_cearense.pdf` | Copiado | PDF do catálogo institucional |
| `src/knowledge_builder.py` | Modificado | Suporte a TextReader para .txt |
| `src/agents/qualifier_agent.py` | Modificado | Pesos + CPF/CE + sugestões |
| `src/agents/product_specialist_agent.py` | Modificado | Catálogo + sugestões |
| `tests/test_weight_rules.py` | Criado | Testes das regras de peso |
