# Design: RAG de Planilhas, Pesos por Estado e Sugestões de Produtos

**Data:** 2026-02-24
**Status:** Aprovado

## Contexto

O agente qualificador da Aço Cearense opera com regras de negócio fixas (peso mínimo de 1.500kg para todos os estados) e sem acesso ao catálogo real de produtos. Este design adiciona:

1. Pesos mínimos reais por estado (da planilha oficial)
2. RAG do catálogo de produtos agrupado por família
3. Sugestões de produto (variações e complemento de peso)
4. CPF aceito para clientes do CE

---

## Arquitetura

### Componentes Novos

| Componente | Tipo | Responsabilidade |
|---|---|---|
| `src/data/weight_rules.py` | Novo | Dict Python com peso mínimo CIF por estado |
| `scripts/generate_catalog_rag.py` | Novo | Processa planilha → 22 arquivos .txt por grupo |
| `knowledge/catalog_groups/` | Novo | 22 arquivos .txt para indexação no RAG |

### Componentes Modificados

| Componente | O que muda |
|---|---|
| `src/knowledge_builder.py` | Adiciona suporte a `.txt` além de PDF |
| `src/agents/qualifier_agent.py` | Pesos por estado + CPF/CE + sugestões |
| `src/agents/product_specialist_agent.py` | RAG do catálogo + lógica de sugestões |
| `scripts/build_knowledge.py` | Indexa também os `.txt` do catálogo |

### Fluxo de Dados

```
Planilha de pesos (Range de Aprovação - Peso Final.xlsx)
  → Extração manual (tipo: Peso Carbono MTS, frete: CIF)
  → src/data/weight_rules.py (dict Python, determinístico)
  → qualifier_agent usa direto nas instruções

Planilha de produtos (produtos_informações_sem_inox.xlsx)
  → scripts/generate_catalog_rag.py
  → knowledge/catalog_groups/*.txt (22 arquivos, 1 por grupo)
  → knowledge_builder indexa no LanceDB (mesmo índice)
  → product_specialist_agent busca via search_knowledge
```

---

## Seção 1: Pesos Mínimos por Estado

**Arquivo:** `src/data/weight_rules.py`
**Fonte:** Planilha `Range de Aprovação - Peso Final.xlsx`, tipo `Peso Carbono MTS`, frete `CIF`.
**Decisão:** Dados críticos de negócio → dicionário Python (sem RAG, sem risco de alucinação).

```python
PESO_MINIMO_CIF_POR_ESTADO = {
    # Nordeste
    "CE": 250,    "AL": 1500,   "MA": 1500,
    "PB": 1500,   "PI": 1500,   "SE": 1500,
    "BA": 1500,   "PE": 1500,   "RN": 1500,
    # Centro-Oeste / Sudeste
    "GO": 4000,   "DF": 4000,   "MG": 4000,
    "SP": 4000,   "RJ": 4000,   "ES": 4000,
    "MT": 4000,   "MS": 4000,   "TO": 4000,
    # Norte
    "PA": 1500,   "AC": 10000,  "AM": 10000,
    "AP": 8000,   "RO": 10000,  "RR": 10000,
    # Sul
    "RS": 8000,   "SC": 8000,   "PR": 4000,
}
```

---

## Seção 2: Catálogo de Produtos no RAG

**Script:** `scripts/generate_catalog_rag.py`
**Entrada:** `produtos_informações_sem_inox.xlsx` (14.029 SKUs, 22 grupos)
**Saída:** `knowledge/catalog_groups/<grupo>.txt` (um arquivo por grupo)

### Formato de cada arquivo

```
GRUPO: CA-50 (Vergalhão de Construção Civil)

DESCRIÇÃO:
Aço carbono CA-50 para construção civil, estruturas de concreto armado.

APLICAÇÕES:
Lajes, vigas, pilares, fundações, sapatas, cintas de amarração.

SUB-GRUPOS DISPONÍVEIS:
- CA-50 Reto: barras retas, bitolas 5mm a 32mm
- CA-50 Rolo: bobina, bitolas 5mm a 10mm
- CA-50 Dobrado: pré-conformado conforme projeto
- CA-50 Corte Dobra: cortado e dobrado sob medida
- CA-50 Spooler: contínuo para produção industrial

PRODUTOS REPRESENTATIVOS:
[5-10 exemplos com código SAP, descrição, dimensões e peso unitário]
```

### Grupos de Produtos (22 total)

Arame, Articulada, Barra Laminada, Bobina, Bobina Slitter, Bobininha,
CA-50, CA-60, Caixilho, Chapa A-36, Chapa Plana, FM, Lambril,
Perfil W, Perfis, Tarugo, Tela, Tela Coluna, Telha, Treliça, Tubo.

### Atualização do knowledge_builder.py

Adicionar `TxtReader` ou processamento nativo de `.txt` para indexar os arquivos gerados no mesmo índice LanceDB (`steel_sales_knowledge`).

---

## Seção 3: Atualização do Qualifier Agent

**Arquivo:** `src/agents/qualifier_agent.py`

### Mudança 1 — Documento de identificação por estado

```
- CE: aceita CPF (11 dígitos) OU CNPJ (14 dígitos)
  → Perguntar: "Pode me informar seu CPF ou CNPJ?"
- Demais estados: somente CNPJ (14 dígitos)
```

### Mudança 2 — Volume mínimo dinâmico

As instruções incluirão a tabela completa de pesos mínimos CIF por estado. O agente valida o volume **após** conhecer o estado do cliente.

### Mudança 3 — Fluxo de coleta atualizado

```
Nome → WhatsApp → E-mail → CPF/CNPJ (conforme UF)
→ UF → Cidade → Produto → Volume (≥ mínimo do estado)
```

Se volume < mínimo: informa o mínimo e aciona fluxo de sugestões antes de classificar.

---

## Seção 4: Lógica de Sugestões (3-4 opções)

Implementada nas instruções do agente, com base no RAG do catálogo.

### Gatilho 1 — Variações de produto

**Quando:** Cliente menciona produto de forma genérica ("quero vergalhão", "preciso de tubo").
**Ação:** Agente sugere 3-4 variações específicas do produto com breve descrição de uso.

Exemplo:
> "Temos algumas opções de vergalhão:
> 1. CA-50 Reto — barras para obra convencional
> 2. CA-50 Rolo — prático para pequenas bitolas
> 3. CA-60 Reto — maior resistência, pode usar menos aço
> 4. Treliça Leve — ideal para lajes"

### Gatilho 2 — Complemento de peso

**Quando:** Volume informado < peso mínimo do estado.
**Ação:** Informa o mínimo, calcula a diferença e sugere 3-4 produtos complementares ao produto principal.

Exemplo:
> "O mínimo para PE é 1.500kg. Seu pedido de 500kg de tubo está 1.000kg abaixo.
> Para completar o pedido, posso sugerir:
> 1. Mais tubos em outras bitolas/comprimentos
> 2. Barras laminadas (Chata, Redonda, Cantoneira)
> 3. Perfis estruturais (U, Enrijecido)
> 4. Arames industriais"

---

## Fontes dos Arquivos

Os arquivos de origem estão em:
`/Users/igorsouza/Downloads/OneDrive_1_13-02-2026/`

- `Range de Aprovação - Peso Final.xlsx` → `src/data/weight_rules.py`
- `produtos_informações_sem_inox.xlsx` → `knowledge/catalog_groups/*.txt`
- `Catálogo_45 anos (1).pdf` → `knowledge/` (indexar junto com os demais PDFs)

---

## Ordem de Implementação

1. Criar `src/data/weight_rules.py` com o dict de pesos
2. Criar script `scripts/generate_catalog_rag.py` e gerar os 22 arquivos `.txt`
3. Atualizar `src/knowledge_builder.py` para suportar `.txt`
4. Atualizar `scripts/build_knowledge.py` para indexar os novos arquivos
5. Copiar `Catálogo_45 anos (1).pdf` para `knowledge/`
6. Reindexar a base de conhecimento (`python scripts/build_knowledge.py`)
7. Atualizar `src/agents/qualifier_agent.py` (pesos + CPF/CE + sugestões)
8. Atualizar `src/agents/product_specialist_agent.py` (catálogo RAG + sugestões)
9. Rodar testes
