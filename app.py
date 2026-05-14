import streamlit as st
import re
import unicodedata
from datetime import datetime
from io import BytesIO

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import pytesseract
    from pdf2image import convert_from_bytes
except Exception:
    pytesseract = None
    convert_from_bytes = None


st.set_page_config(
    page_title="Raio-X do PPP - PróBenefício",
    page_icon="📄",
    layout="wide"
)

# ============================================================
# RAIO-X DO PPP — VERSÃO PROJETO REAL
# Análise campo a campo conforme especificação técnica enviada
# Base legal e jurisprudencial embarcada no próprio código
# ============================================================


# ============================================================
# BASE LEGAL / JURISPRUDENCIAL EMBARCADA
# ============================================================

BASE_LEGAL = {
    "geral": {
        "lei_8213_art_57": (
            "Lei 8.213/91, art. 57: a aposentadoria especial é devida ao segurado que trabalhou sujeito "
            "a condições especiais que prejudiquem a saúde ou a integridade física, observada a exposição "
            "habitual e permanente, não ocasional nem intermitente, conforme a legislação previdenciária."
        ),
        "lei_8213_art_58": (
            "Lei 8.213/91, art. 58: a comprovação da efetiva exposição aos agentes nocivos deve ser feita "
            "por formulário emitido pela empresa, com base em laudo técnico de condições ambientais do trabalho "
            "expedido por médico do trabalho ou engenheiro de segurança do trabalho."
        ),
        "decreto_3048_art_68": (
            "Decreto 3.048/99, art. 68: a efetiva exposição do segurado a agentes prejudiciais à saúde "
            "será comprovada por formulário PPP emitido pela empresa com base em laudo técnico. O enquadramento "
            "deve observar os agentes previstos no Anexo IV e as exigências metodológicas aplicáveis."
        ),
        "in_128_281": (
            "IN PRES/INSS 128/2022, art. 281: o PPP é o documento histórico-laboral do trabalhador, "
            "emitido pela empresa ou equiparada, destinado a comprovar as condições ambientais de trabalho "
            "e a exposição a fatores de risco."
        ),
        "in_128_283": (
            "IN PRES/INSS 128/2022, art. 283: a profissiografia deve descrever as atividades exercidas "
            "com clareza, em verbos no infinitivo impessoal, permitindo verificar a habitualidade, permanência "
            "e compatibilidade entre função, atividade e agente nocivo."
        ),
        "in_128_284": (
            "IN PRES/INSS 128/2022, art. 284: os registros ambientais devem indicar período, tipo de agente, "
            "fator de risco, intensidade/concentração, técnica utilizada, EPC, EPI, CA e atendimento aos requisitos "
            "das normas de segurança."
        ),
        "in_128_285": (
            "IN PRES/INSS 128/2022, art. 285: os registros ambientais devem estar vinculados a responsável técnico "
            "legalmente habilitado, com identificação profissional e período de responsabilidade."
        ),
        "in_128_286": (
            "IN PRES/INSS 128/2022, art. 286: o PPP deve conter data de emissão e assinatura do representante legal, "
            "mantida a obrigatoriedade de assinatura para PPP físico."
        ),
        "sumula_68_tnu": (
            "Súmula 68 da TNU: o laudo pericial ou PPP deve retratar as condições de trabalho à época em que "
            "a atividade foi exercida. Laudo extemporâneo exige cautela e coerência com o período analisado."
        ),
        "prova_complementar": (
            "Na ausência, incompletude ou inconsistência do PPP, recomenda-se complementação probatória por LTCAT, "
            "laudo técnico, documentos internos da empresa, prova emprestada, perícia judicial ou perícia indireta "
            "por similaridade, quando cabível."
        ),
    },
    "ruido": {
        "limites": (
            "Limites previdenciários para ruído: superior a 80 dB até 05/03/1997; superior a 90 dB de "
            "06/03/1997 a 18/11/2003; superior a 85 dB a partir de 19/11/2003."
        ),
        "tema_555_stf": (
            "Tema 555/STF — ARE 664.335: para ruído acima dos limites legais, a declaração de EPI eficaz "
            "no PPP não descaracteriza automaticamente a especialidade. Há presunção de ineficácia do EPI "
            "para neutralização do agente ruído."
        ),
        "tema_1083_stj": (
            "Tema 1.083/STJ: quando há diferentes níveis de ruído, a especialidade deve ser aferida pelo "
            "NEN — Nível de Exposição Normalizado. Se PPP e LTCAT forem omissos quanto ao método, recomenda-se "
            "complementação técnica ou perícia."
        ),
        "tema_174_tnu": (
            "Tema 174/TNU: a partir de 19/11/2003, a aferição do ruído deve observar a NHO-01 da Fundacentro "
            "ou metodologia equivalente aceita. PPP omisso quanto à técnica deve ser complementado pelo LTCAT."
        ),
        "sumula_9_tnu": (
            "Súmula 9/TNU: o uso de EPI não afasta a nocividade do agente ruído para fins de reconhecimento "
            "de atividade especial."
        ),
    },
    "epi": {
        "irdr15_trf4": (
            "IRDR 15/TRF4: se LTCAT/PPP indicam EPI ineficaz, reconhece-se a especialidade. Se indicam EPI eficaz, "
            "há presunção relativa, cabendo prova em contrário. Exceções: ruído, agentes biológicos, agentes "
            "cancerígenos LINACH e agentes periculosos, nos quais o EPI não afasta automaticamente a especialidade."
        ),
        "tema_213_tnu": (
            "Tema 213/TNU: a mera juntada de PPP com indicação de EPI eficaz não impede o segurado de produzir "
            "prova em sentido contrário acerca da real ineficácia ou insuficiência do equipamento."
        ),
        "nr06": (
            "NR-06: todo EPI deve possuir Certificado de Aprovação — CA, ser adequado ao risco, estar válido, "
            "ser fornecido, fiscalizado, substituído, higienizado e utilizado de forma efetiva."
        ),
        "nr01": (
            "NR-01, item 1.5.5.1.2: deve ser observada a hierarquia das medidas de proteção, priorizando medidas "
            "coletivas, administrativas ou organizacionais antes do EPI individual."
        ),
    },
    "quimicos": {
        "tema_1083_stj": (
            "Para agentes químicos, a simples indicação de EPI eficaz no PPP não deve afastar automaticamente "
            "a especialidade. É necessária análise concreta da efetiva neutralização, considerando concentração, "
            "forma de contato, metodologia, CA, treinamento, troca, fiscalização e compatibilidade do EPI."
        ),
        "linach": (
            "Agentes cancerígenos LINACH — Portaria Interministerial 09/2014: a análise tende a ser qualitativa. "
            "O art. 68, §4º, do Decreto 3.048/99 reforça que a avaliação de agentes reconhecidamente cancerígenos "
            "não se resolve pela simples declaração de EPI eficaz."
        ),
        "nr15_11_12_13": (
            "NR-15: Anexos 11 e 12 tratam de agentes químicos quantitativos, com comparação a limites de tolerância. "
            "Anexo 13 trata de agentes químicos qualitativos, em que a presença/exposição é juridicamente relevante."
        ),
    },
    "biologicos": {
        "nr15_14": (
            "NR-15, Anexo 14: agentes biológicos são avaliados qualitativamente, considerando risco de contato "
            "com pacientes, material infectocontagiante, lixo urbano, esgoto, secreções, sangue, laboratórios, "
            "hospitais e ambientes equivalentes."
        ),
        "tema_211_tnu": (
            "Tema 211/TNU: a exposição a agentes biológicos deve ser analisada qualitativamente, pelo risco "
            "ocupacional de contaminação, sem exigência de mensuração quantitativa."
        ),
        "irdr15": (
            "IRDR 15/TRF4: para agentes biológicos, o EPI não afasta automaticamente a especialidade, dada a "
            "natureza qualitativa do risco de contaminação."
        ),
    },
    "responsavel": {
        "art_195_clt": (
            "CLT, art. 195: a caracterização e classificação da insalubridade ou periculosidade deve ocorrer "
            "por perícia a cargo de médico do trabalho ou engenheiro do trabalho, registrados no Ministério do Trabalho."
        ),
        "in_128_285": (
            "IN 128/2022, art. 285: o responsável pelos registros ambientais no PPP deve ser profissional legalmente "
            "habilitado, com identificação e registro profissional, cobrindo o período de exposição."
        ),
    },
    "trf4": {
        "irdr8": (
            "IRDR 8/TRF4: período de auxílio-doença previdenciário pode ser computado como tempo especial quando "
            "o trabalhador exercia atividade especial antes do afastamento."
        ),
        "irdr15": (
            "IRDR 15/TRF4: principal orientação regional sobre EPI e ônus da prova. Vinculante no RS, SC e PR; "
            "ruído, biológicos, cancerígenos e periculosos são exceções à eficácia neutralizante do EPI."
        ),
    }
}


CAMPOS_PPP = [
    {
        "campo": "1",
        "nome": "CNPJ / CEI / CAEPF / CNO",
        "criticidade": "GRAVE",
        "termos": ["cnpj", "cei", "caepf", "cno"],
        "verificacao": "Verificar se o número existe e se está vinculado ao estabelecimento real onde o trabalhador exercia atividades, não apenas à matriz.",
        "fundamento": "IN 128/2022, art. 281; Decreto 3.048/99, art. 68. CNPJ incorreto fragiliza ou invalida o PPP."
    },
    {
        "campo": "2",
        "nome": "Nome empresarial",
        "criticidade": "MODERADA",
        "termos": ["nome empresarial", "empresa", "empregador"],
        "verificacao": "Verificar se corresponde ao CNPJ informado e se há sucessora quando a empresa foi sucedida/extinta.",
        "fundamento": "IN 128/2022, art. 281, §2º; Súmula 55/TNU."
    },
    {
        "campo": "3",
        "nome": "CNAE",
        "criticidade": "CRÍTICA",
        "termos": ["cnae"],
        "verificacao": "Campo obrigatório. Verificar compatibilidade entre atividade econômica, risco e agentes nocivos declarados.",
        "fundamento": "IN 128/2022, art. 281, I; Decreto 3.048/99, Anexo IV."
    },
    {
        "campo": "4",
        "nome": "Nome do trabalhador",
        "criticidade": "MODERADA",
        "termos": ["nome do trabalhador", "trabalhador", "empregado", "segurado"],
        "verificacao": "Verificar se corresponde ao CPF e documentos previdenciários.",
        "fundamento": "IN 128/2022, art. 281."
    },
    {
        "campo": "6",
        "nome": "CPF",
        "criticidade": "CRÍTICA",
        "termos": ["cpf"],
        "verificacao": "CPF deve corresponder ao trabalhador. CPF incorreto invalida a identificação do segurado.",
        "fundamento": "IN 128/2022, art. 281."
    },
    {
        "campo": "9",
        "nome": "Matrícula eSocial",
        "criticidade": "CRÍTICA",
        "termos": ["matricula", "matrícula", "esocial"],
        "verificacao": "Para PPP emitido a partir de 01/01/2023, matrícula eSocial é obrigatória.",
        "fundamento": "IN 128/2022, art. 291; PPP-e obrigatório a partir de 01/01/2023."
    },
    {
        "campo": "10",
        "nome": "Data de admissão",
        "criticidade": "GRAVE",
        "termos": ["data de admissao", "data de admissão", "admissao", "admissão"],
        "verificacao": "Verificar consistência com CTPS, data de nascimento e períodos de exposição.",
        "fundamento": "CLT, art. 29; IN 128/2022, art. 281."
    },
    {
        "campo": "13",
        "nome": "Lotação e atribuição",
        "criticidade": "GRAVE",
        "termos": ["lotacao", "lotação", "atribuicao", "atribuição", "cbo", "gfip"],
        "verificacao": "Verificar períodos sem lacuna, CNPJ do local real, CBO compatível e GFIP/eSocial coerente.",
        "fundamento": "IN 128/2022, arts. 282-283; CBO vigente à época."
    },
    {
        "campo": "14",
        "nome": "Descrição das atividades",
        "criticidade": "CRÍTICA",
        "termos": ["descricao atividades", "descrição atividades", "descricao das atividades", "descrição das atividades", "profissiografia"],
        "verificacao": "Atividades devem estar em verbos no infinitivo impessoal, evidenciar habitualidade/permanência e compatibilidade com os agentes nocivos.",
        "fundamento": "IN 128/2022, art. 283, §1º; Lei 8.213/91, art. 57, §3º; IRDR 15/TRF4."
    },
    {
        "campo": "15.1",
        "nome": "Período de exposição",
        "criticidade": "GRAVE",
        "termos": ["periodo de exposicao", "período de exposição", "15.1"],
        "verificacao": "Período deve ser compatível com lotação, admissão e alterações de atividade/agente.",
        "fundamento": "IN 128/2022, art. 284; Súmula 68/TNU."
    },
    {
        "campo": "15.3",
        "nome": "Fator de risco",
        "criticidade": "CRÍTICA",
        "termos": ["fator de risco", "agente nocivo", "risco"],
        "verificacao": "Agente deve ser tecnicamente identificado; químicos devem usar nome da substância, não apenas nome comercial.",
        "fundamento": "IN 128/2022, art. 284, IV; Decreto 3.048/99, Anexo IV; LINACH."
    },
    {
        "campo": "15.4",
        "nome": "Intensidade / concentração",
        "criticidade": "CRÍTICA",
        "termos": ["intensidade", "concentracao", "concentração", "db", "nen", "ibutg", "mg/m3", "ppm"],
        "verificacao": "Agentes quantitativos exigem valor mensurado; ruído pós-19/11/2003 exige NEN quando variável; qualitativos podem constar NA.",
        "fundamento": "NR-15; NHO-01; Tema 1083/STJ; Decreto 3.048/99, art. 68."
    },
    {
        "campo": "15.5",
        "nome": "Técnica utilizada",
        "criticidade": "CRÍTICA",
        "termos": ["tecnica utilizada", "técnica utilizada", "nho", "fundacentro", "nr-15", "dosimetria"],
        "verificacao": "Norma metodológica deve estar expressamente indicada. Para ruído pós-19/11/2003, observar NHO-01/Fundacentro ou metodologia admitida.",
        "fundamento": "IN 128/2022, art. 284, V; Tema 174/TNU; Tema 1083/STJ."
    },
    {
        "campo": "15.7",
        "nome": "EPI eficaz",
        "criticidade": "CRÍTICA",
        "termos": ["epi eficaz", "epi", "equipamento de protecao individual", "equipamento de proteção individual"],
        "verificacao": "Analisar eficácia conforme agente. Ruído, biológicos, cancerígenos e periculosos não são automaticamente neutralizados por EPI.",
        "fundamento": "Tema 555/STF; IRDR 15/TRF4; Tema 213/TNU; NR-06."
    },
    {
        "campo": "15.8",
        "nome": "CA do EPI",
        "criticidade": "CRÍTICA",
        "termos": ["ca epi", "certificado de aprovacao", "certificado de aprovação", "ca"],
        "verificacao": "Verificar se há CA, se é adequado ao agente e se estava válido no período.",
        "fundamento": "NR-06; IN 128/2022, art. 284, VIII; Portaria 11.347/2022."
    },
    {
        "campo": "15.9",
        "nome": "Requisitos NR-06 e NR-01",
        "criticidade": "CRÍTICA",
        "termos": ["higienizacao", "higienização", "troca", "validade", "funcionamento", "medida de protecao", "medida de proteção"],
        "verificacao": "Verificar os 5 sub-requisitos: medida de proteção, funcionamento, validade, periodicidade de troca e higienização.",
        "fundamento": "NR-01; NR-06; IN 128/2022, art. 284, IX; Tema 213/TNU; IRDR 15/TRF4."
    },
    {
        "campo": "16",
        "nome": "Responsável pelos registros ambientais",
        "criticidade": "CRÍTICA",
        "termos": ["responsavel pelos registros", "responsável pelos registros", "engenheiro", "medico do trabalho", "médico do trabalho", "crea", "crm"],
        "verificacao": "Responsável deve ser engenheiro de segurança do trabalho ou médico do trabalho, com registro profissional válido.",
        "fundamento": "CLT, art. 195; IN 128/2022, art. 285; Resoluções profissionais aplicáveis."
    },
    {
        "campo": "17",
        "nome": "Data de emissão do PPP",
        "criticidade": "MODERADA",
        "termos": ["data de emissao", "data de emissão", "emissao", "emissão"],
        "verificacao": "Verificar se a emissão é contemporânea/posterior ao período e se o LTCAT é atualizado.",
        "fundamento": "IN 128/2022, art. 286; Súmula 68/TNU."
    },
    {
        "campo": "18",
        "nome": "Representante legal e assinatura",
        "criticidade": "CRÍTICA",
        "termos": ["representante legal", "assinatura", "assinado", "carimbo"],
        "verificacao": "PPP físico exige assinatura do representante legal. Carimbo foi dispensado, mas assinatura permanece obrigatória.",
        "fundamento": "IN 128/2022, art. 286; IN 141/2022; Código Penal, art. 297."
    },
]


AGENTES = {
    "ruido": {
        "grupo": "Físico",
        "termos": ["ruido", "ruído", "db", "decibel"],
        "norma": "NR-15 Anexo 1; NHO-01 Fundacentro",
        "limite": "80/90/85 dB conforme período",
        "metodologia": "NHO-01 / dosimetria / NEN quando aplicável",
        "fundamento": BASE_LEGAL["ruido"]["tema_555_stf"] + " " + BASE_LEGAL["ruido"]["tema_1083_stj"]
    },
    "calor": {
        "grupo": "Físico",
        "termos": ["calor", "ibutg"],
        "norma": "NR-15 Anexo 3",
        "limite": "IBUTG conforme atividade e regime de trabalho",
        "metodologia": "IBUTG",
        "fundamento": "Calor exige avaliação quantitativa conforme NR-15 Anexo 3."
    },
    "frio": {
        "grupo": "Físico",
        "termos": ["frio", "camara fria", "câmara fria"],
        "norma": "NR-15 Anexo 9",
        "limite": "Avaliação qualitativa por inspeção",
        "metodologia": "Laudo de inspeção",
        "fundamento": "Frio é analisado qualitativamente por inspeção e condições ambientais."
    },
    "hidrocarbonetos": {
        "grupo": "Químico",
        "termos": ["hidrocarboneto", "hidrocarbonetos", "oleo mineral", "óleo mineral", "graxa", "solvente", "gasolina", "diesel", "tolueno", "xileno"],
        "norma": "NR-15 Anexo 13",
        "limite": "Qualitativo",
        "metodologia": "Laudo qualitativo",
        "fundamento": BASE_LEGAL["quimicos"]["nr15_11_12_13"] + " " + BASE_LEGAL["quimicos"]["tema_1083_stj"]
    },
    "benzeno": {
        "grupo": "Químico cancerígeno",
        "termos": ["benzeno"],
        "norma": "NR-15 Anexo 13-A; LINACH",
        "limite": "Qualquer nível relevante",
        "metodologia": "Qualitativo / PPEOB",
        "fundamento": BASE_LEGAL["quimicos"]["linach"]
    },
    "silica": {
        "grupo": "Químico cancerígeno",
        "termos": ["silica", "sílica"],
        "norma": "NR-15 Anexo 12; LINACH",
        "limite": "Qualitativo/quantitativo conforme poeira",
        "metodologia": "NHO aplicável / laudo técnico",
        "fundamento": BASE_LEGAL["quimicos"]["linach"]
    },
    "amianto": {
        "grupo": "Químico cancerígeno",
        "termos": ["amianto", "asbesto"],
        "norma": "NR-15 Anexo 12; LINACH",
        "limite": "Qualitativo",
        "metodologia": "Laudo qualitativo",
        "fundamento": BASE_LEGAL["quimicos"]["linach"]
    },
    "biologicos": {
        "grupo": "Biológico",
        "termos": ["biologico", "biológico", "virus", "vírus", "bacteria", "bactéria", "fungo", "hospital", "paciente", "sangue", "secrecao", "secreção", "laboratorio", "laboratório", "lixo urbano", "esgoto", "material infectocontagiante"],
        "norma": "NR-15 Anexo 14",
        "limite": "Qualitativo",
        "metodologia": "Atividade descrita / risco de contato",
        "fundamento": BASE_LEGAL["biologicos"]["nr15_14"] + " " + BASE_LEGAL["biologicos"]["tema_211_tnu"]
    },
    "eletricidade": {
        "grupo": "Periculoso",
        "termos": ["eletricidade", "energia eletrica", "energia elétrica", "alta tensao", "alta tensão"],
        "norma": "Jurisprudência / periculosidade",
        "limite": "Qualitativo",
        "metodologia": "Descrição da atividade",
        "fundamento": "Agentes periculosos, como eletricidade, devem ser descritos na profissiografia. EPI não afasta automaticamente a especialidade conforme IRDR 15/TRF4."
    },
}


# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================

def normalizar(texto):
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


def extrair_texto_pdf(uploaded_file):
    pdf_bytes = uploaded_file.read()
    texto = ""

    if fitz is not None:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                texto += page.get_text("text") + "\n"
        except Exception as e:
            texto += f"\n[Erro na extração PyMuPDF: {e}]\n"

    # OCR fallback se o texto vier muito curto
    if len(texto.strip()) < 300 and pytesseract is not None and convert_from_bytes is not None:
        try:
            imagens = convert_from_bytes(pdf_bytes, dpi=220)
            for img in imagens:
                texto += "\n" + pytesseract.image_to_string(img, lang="por")
        except Exception as e:
            texto += f"\n[OCR não executado ou falhou: {e}]\n"

    return texto


def possui(texto_norm, termos):
    return any(normalizar(t) in texto_norm for t in termos)


def extrair_datas(texto):
    return re.findall(r"\b\d{2}/\d{2}/\d{4}\b", texto)


def extrair_ruidos(texto):
    achados = re.findall(r"(\d{2,3}(?:[,.]\d+)?)\s*(?:dB|db|dB\(A\)|dba)", texto, flags=re.IGNORECASE)
    valores = []
    for a in achados:
        try:
            valores.append(float(a.replace(",", ".")))
        except Exception:
            pass
    return valores


def classificar_alertas(alertas):
    crit = sum(1 for a in alertas if a["criticidade"] == "CRÍTICA")
    grave = sum(1 for a in alertas if a["criticidade"] == "GRAVE")
    mod = sum(1 for a in alertas if a["criticidade"] == "MODERADA")

    if crit >= 3 or (crit >= 1 and grave >= 2):
        return "PPP COM FALHAS RELEVANTES — RECOMENDA-SE IMPUGNAÇÃO OU COMPLEMENTAÇÃO"
    if crit >= 1 or grave >= 2:
        return "PPP COM RISCO JURÍDICO — ANALISAR COMPLEMENTAÇÃO PROBATÓRIA"
    if grave >= 1 or mod >= 2:
        return "PPP COM PONTOS DE ATENÇÃO"
    return "PPP SEM FALHAS CRÍTICAS AUTOMÁTICAS IDENTIFICADAS"


# ============================================================
# MOTOR DE ANÁLISE
# ============================================================

def analisar_campos(texto):
    texto_norm = normalizar(texto)
    resultados = []

    for campo in CAMPOS_PPP:
        encontrado = possui(texto_norm, campo["termos"])

        status = "CONFORME/LOCALIZADO" if encontrado else "AUSENTE OU NÃO LOCALIZADO AUTOMATICAMENTE"
        if not encontrado:
            resultados.append({
                "campo": campo["campo"],
                "nome": campo["nome"],
                "status": status,
                "criticidade": campo["criticidade"],
                "falha": f"Campo {campo['campo']} — {campo['nome']} não foi localizado de forma clara no texto extraído.",
                "verificacao": campo["verificacao"],
                "fundamento": campo["fundamento"],
                "estrategia": "Conferir o PPP original. Se ausente, solicitar complementação documental ao empregador ou impugnar em via administrativa/judicial."
            })
        else:
            resultados.append({
                "campo": campo["campo"],
                "nome": campo["nome"],
                "status": status,
                "criticidade": "OK",
                "falha": "",
                "verificacao": campo["verificacao"],
                "fundamento": campo["fundamento"],
                "estrategia": "Campo localizado. Ainda assim, recomenda-se conferência material da informação."
            })

    return resultados


def analisar_agentes(texto):
    texto_norm = normalizar(texto)
    agentes = []

    for chave, info in AGENTES.items():
        if possui(texto_norm, info["termos"]):
            item = {
                "agente": chave,
                "grupo": info["grupo"],
                "norma": info["norma"],
                "limite": info["limite"],
                "metodologia": info["metodologia"],
                "fundamento": info["fundamento"],
                "enquadramento": "INDÍCIO DE ENQUADRAMENTO — exige conferência do período, intensidade e metodologia."
            }

            if chave == "ruido":
                ruidos = extrair_ruidos(texto)
                item["valores_detectados_db"] = ruidos
                if ruidos:
                    maior = max(ruidos)
                    if maior > 85:
                        item["enquadramento"] = f"Ruído detectado em {maior} dB. Há forte indício de especialidade para períodos posteriores a 19/11/2003, se habitual/permanente."
                    elif maior > 80:
                        item["enquadramento"] = f"Ruído detectado em {maior} dB. Pode ser favorável para períodos até 05/03/1997; exige análise cronológica."
                    else:
                        item["enquadramento"] = f"Ruído detectado em {maior} dB, abaixo do limite atual de 85 dB; risco de indeferimento por ruído."
                else:
                    item["enquadramento"] = "Ruído mencionado, mas sem intensidade numérica clara. Falha crítica no campo 15.4."

            agentes.append(item)

    return agentes


def analisar_epi(texto, agentes):
    texto_norm = normalizar(texto)
    conclusoes = []

    tem_epi = "epi" in texto_norm
    tem_eficaz = "eficaz" in texto_norm or "s" in texto_norm
    tem_ca = " ca " in f" {texto_norm} " or "certificado de aprovacao" in texto_norm or "certificado de aprovação" in texto.lower()

    if not tem_epi:
        conclusoes.append({
            "criticidade": "CRÍTICA",
            "ponto": "EPI não localizado",
            "analise": "O PPP não apresenta informação clara sobre EPI no texto extraído.",
            "fundamento": BASE_LEGAL["epi"]["nr06"] + " " + BASE_LEGAL["epi"]["tema_213_tnu"],
            "estrategia": "Solicitar PPP completo/LTCAT e impugnar eventual presunção de eficácia do EPI."
        })
        return conclusoes

    for ag in agentes:
        agente = ag["agente"]
        grupo = ag["grupo"].lower()

        if agente == "ruido":
            conclusoes.append({
                "criticidade": "CRÍTICA",
                "ponto": "EPI x ruído",
                "analise": "Ainda que o PPP indique EPI eficaz, a especialidade por ruído acima do limite legal não é automaticamente afastada.",
                "fundamento": BASE_LEGAL["ruido"]["tema_555_stf"] + " " + BASE_LEGAL["ruido"]["sumula_9_tnu"],
                "estrategia": "Sustentar irrelevância da eficácia formal do EPI para ruído quando superado o limite legal."
            })
        elif "cancer" in grupo or agente in ["benzeno", "silica", "amianto"]:
            conclusoes.append({
                "criticidade": "CRÍTICA",
                "ponto": "EPI x agente cancerígeno",
                "analise": "Para agentes cancerígenos/LINACH, a simples declaração de EPI eficaz não neutraliza juridicamente o risco.",
                "fundamento": BASE_LEGAL["quimicos"]["linach"] + " " + BASE_LEGAL["epi"]["irdr15_trf4"],
                "estrategia": "Impugnar eficácia do EPI e defender análise qualitativa."
            })
        elif "biologico" in grupo or "biológico" in grupo:
            conclusoes.append({
                "criticidade": "CRÍTICA",
                "ponto": "EPI x biológico",
                "analise": "Para agentes biológicos, o EPI não afasta automaticamente a especialidade, dada a natureza qualitativa do risco.",
                "fundamento": BASE_LEGAL["biologicos"]["tema_211_tnu"] + " " + BASE_LEGAL["biologicos"]["irdr15"],
                "estrategia": "Defender risco ocupacional qualitativo e solicitar prova complementar se necessário."
            })
        else:
            conclusoes.append({
                "criticidade": "GRAVE" if tem_eficaz else "CRÍTICA",
                "ponto": f"EPI x {agente}",
                "analise": "A eficácia do EPI exige comprovação concreta: CA adequado, validade, fornecimento, troca, fiscalização, treinamento e higienização.",
                "fundamento": BASE_LEGAL["epi"]["nr06"] + " " + BASE_LEGAL["epi"]["tema_213_tnu"],
                "estrategia": "Verificar CA e sub-requisitos do campo 15.9. Se incompletos, impugnar a eficácia."
            })

    if tem_epi and not tem_ca:
        conclusoes.append({
            "criticidade": "CRÍTICA",
            "ponto": "CA do EPI não identificado",
            "analise": "Não foi localizado Certificado de Aprovação do EPI de forma clara.",
            "fundamento": BASE_LEGAL["epi"]["nr06"],
            "estrategia": "Solicitar comprovação do CA válido e compatível com o agente."
        })

    return conclusoes


def analisar_ltcat_responsavel(texto):
    texto_norm = normalizar(texto)
    itens = []

    if "ltcat" not in texto_norm:
        itens.append({
            "criticidade": "GRAVE",
            "ponto": "LTCAT não localizado",
            "analise": "O texto extraído não apresenta menção clara ao LTCAT.",
            "fundamento": BASE_LEGAL["geral"]["lei_8213_art_58"] + " " + BASE_LEGAL["geral"]["decreto_3048_art_68"],
            "estrategia": "Solicitar LTCAT, laudo técnico ou perícia indireta."
        })

    tem_resp = any(t in texto_norm for t in ["engenheiro", "medico do trabalho", "médico do trabalho", "crea", "crm"])
    if not tem_resp:
        itens.append({
            "criticidade": "CRÍTICA",
            "ponto": "Responsável técnico não localizado",
            "analise": "Não foi identificado médico do trabalho ou engenheiro de segurança do trabalho com CREA/CRM.",
            "fundamento": BASE_LEGAL["responsavel"]["art_195_clt"] + " " + BASE_LEGAL["responsavel"]["in_128_285"],
            "estrategia": "Impugnar validade técnica do PPP e solicitar documento com responsável habilitado."
        })

    return itens


def gerar_parecer(texto, trf):
    datas = extrair_datas(texto)
    campos = analisar_campos(texto)
    agentes = analisar_agentes(texto)
    epi = analisar_epi(texto, agentes)
    ltcat = analisar_ltcat_responsavel(texto)

    falhas = [c for c in campos if c["criticidade"] in ["CRÍTICA", "GRAVE", "MODERADA"]]
    falhas += epi
    falhas += ltcat

    classificacao = classificar_alertas(falhas)

    linhas = []

    linhas.append("# RAIO-X DO PPP — PARECER TÉCNICO PREVIDENCIÁRIO")
    linhas.append("")
    linhas.append("## 1. IDENTIFICAÇÃO DO DOCUMENTO")
    linhas.append(f"- Datas localizadas no documento: {', '.join(datas) if datas else 'não localizadas automaticamente'}")
    linhas.append(f"- Tipo de análise: PPP físico/PPP-e — identificação automática preliminar")
    linhas.append(f"- TRF selecionado: {trf}")
    linhas.append("")

    linhas.append("## 2. CHECKLIST DE CAMPOS OBRIGATÓRIOS")
    for c in campos:
        linhas.append(f"- Campo {c['campo']} — {c['nome']}: {c['status']}")
    linhas.append("")

    linhas.append("## 3. FALHAS IDENTIFICADAS POR CRITICIDADE")
    if falhas:
        for f in falhas:
            nome = f.get("nome") or f.get("ponto") or "Falha"
            linhas.append(f"### {f.get('criticidade', 'ATENÇÃO')} — {nome}")
            if f.get("falha"):
                linhas.append(f"- Falha: {f['falha']}")
            if f.get("analise"):
                linhas.append(f"- Análise: {f['analise']}")
            if f.get("verificacao"):
                linhas.append(f"- O que verificar: {f['verificacao']}")
            linhas.append(f"- Fundamento: {f.get('fundamento', 'não informado')}")
            linhas.append(f"- Estratégia: {f.get('estrategia', 'Complementar documentação e avaliar impugnação.')}")
            linhas.append("")
    else:
        linhas.append("- Nenhuma falha crítica automática identificada.")
    linhas.append("")

    linhas.append("## 4. ANÁLISE DOS AGENTES NOCIVOS x DECRETO 3.048/99 / NR-15")
    if agentes:
        for a in agentes:
            linhas.append(f"### {a['agente'].upper()} — {a['grupo']}")
            linhas.append(f"- Norma/Anexo: {a['norma']}")
            linhas.append(f"- Limite/Critério: {a['limite']}")
            linhas.append(f"- Metodologia esperada: {a['metodologia']}")
            linhas.append(f"- Enquadramento: {a['enquadramento']}")
            linhas.append(f"- Fundamento: {a['fundamento']}")
            linhas.append("")
    else:
        linhas.append("- Nenhum agente nocivo foi identificado automaticamente. Recomenda-se revisar OCR ou preencher manualmente.")
    linhas.append("")

    linhas.append("## 5. EFICÁCIA DO EPI — TEMA 555/STF, TEMA 213/TNU E IRDR 15/TRF4")
    if epi:
        for e in epi:
            linhas.append(f"- {e['criticidade']} — {e['ponto']}: {e['analise']}")
            linhas.append(f"  Fundamento: {e['fundamento']}")
            linhas.append(f"  Estratégia: {e['estrategia']}")
    else:
        linhas.append("- Sem análise específica de EPI.")
    linhas.append("")

    linhas.append("## 6. LTCAT — REGULARIDADE E ATUALIZAÇÃO")
    if ltcat:
        for l in ltcat:
            linhas.append(f"- {l['criticidade']} — {l['ponto']}: {l['analise']}")
            linhas.append(f"  Fundamento: {l['fundamento']}")
            linhas.append(f"  Estratégia: {l['estrategia']}")
    else:
        linhas.append("- Não foram identificadas falhas automáticas em LTCAT/responsável técnico, mas recomenda-se conferência manual.")
    linhas.append("")

    linhas.append("## 7. eSOCIAL E PPP ELETRÔNICO")
    linhas.append("- Para PPP emitido a partir de 01/01/2023, deve ser verificada a matrícula eSocial e a transmissão do PPP-e.")
    linhas.append("- Fundamento: IN 128/2022, art. 291; obrigatoriedade do PPP eletrônico a partir de 01/01/2023.")
    linhas.append("")

    linhas.append("## 8. ESTRATÉGIA — VIA JUDICIAL x ADMINISTRATIVA/CRPS")
    linhas.append(f"- Classificação automática: {classificacao}")
    if "FALHAS RELEVANTES" in classificacao:
        linhas.append("- Estratégia sugerida: preparar impugnação administrativa robusta e, em caso de indeferimento, ação judicial com pedido de perícia técnica ou perícia indireta.")
    elif "RISCO" in classificacao:
        linhas.append("- Estratégia sugerida: complementar PPP/LTCAT antes do protocolo ou formular pedido administrativo já com ressalva técnica.")
    else:
        linhas.append("- Estratégia sugerida: seguir com pedido administrativo, mantendo documentação complementar para eventual recurso.")
    if trf == "TRF4":
        linhas.append("- Observação TRF4: aplicar IRDR 15 quanto ao EPI e ônus da prova; aplicar IRDR 8 se houver benefício por incapacidade no período.")
    linhas.append("")

    linhas.append("## 9. CONCLUSÃO")
    linhas.append(f"- Resultado: {classificacao}")
    linhas.append("- Este parecer é uma análise técnica preliminar automatizada e não substitui a conferência humana do PPP original.")
    linhas.append("- Próximos passos: revisar documento original, confirmar campos ausentes, solicitar LTCAT/CA/laudos e definir estratégia administrativa ou judicial.")
    linhas.append("")
    linhas.append("## BASE LEGAL UTILIZADA")
    for grupo, itens in BASE_LEGAL.items():
        linhas.append(f"### {grupo.upper()}")
        for titulo, texto_base in itens.items():
            linhas.append(f"- {titulo}: {texto_base}")
        linhas.append("")

    return "\n".join(linhas), campos, agentes, epi, ltcat, classificacao


# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("📄 Raio-X do PPP – PróBenefício")
st.caption("Análise campo a campo do PPP conforme IN 128/2022, Decreto 3.048/99, NR-15, Temas STF/STJ/TNU e IRDR/TRF4.")

with st.sidebar:
    st.header("Configuração")
    trf = st.selectbox("TRF de competência", ["TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"], index=3)
    st.info("O sistema não armazena dados. A análise ocorre durante a sessão.")

uploaded_file = st.file_uploader("Carregue o PPP em PDF", type=["pdf"])

texto_manual = st.text_area("Ou cole manualmente o texto extraído do PPP", height=180)

texto_final = ""

if uploaded_file:
    with st.spinner("Extraindo texto do PPP..."):
        texto_final = extrair_texto_pdf(uploaded_file)
    st.success("PDF carregado e texto extraído.")
elif texto_manual.strip():
    texto_final = texto_manual

if texto_final:
    with st.expander("Ver texto extraído / editável", expanded=False):
        texto_final = st.text_area("Texto base da análise", value=texto_final, height=300)

if st.button("🚀 Gerar Raio-X do PPP", use_container_width=True):
    if not texto_final.strip():
        st.error("Envie um PDF ou cole o texto do PPP.")
    else:
        relatorio, campos, agentes, epi, ltcat, classificacao = gerar_parecer(texto_final, trf)

        st.divider()
        st.header("📋 Resultado Executivo")
        if "FALHAS RELEVANTES" in classificacao:
            st.error(classificacao)
        elif "RISCO" in classificacao:
            st.warning(classificacao)
        else:
            st.success(classificacao)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Campos analisados", len(campos))
        with c2:
            st.metric("Agentes identificados", len(agentes))
        with c3:
            falhas_count = len([c for c in campos if c["criticidade"] in ["CRÍTICA", "GRAVE", "MODERADA"]]) + len(epi) + len(ltcat)
            st.metric("Alertas", falhas_count)

        st.subheader("🔎 Agentes nocivos identificados")
        if agentes:
            for a in agentes:
                st.write(f"- **{a['agente'].upper()}** ({a['grupo']}) — {a['enquadramento']}")
        else:
            st.warning("Nenhum agente nocivo identificado automaticamente.")

        st.subheader("⚠️ Checklist de campos")
        for c in campos:
            if c["status"].startswith("AUSENTE"):
                if c["criticidade"] == "CRÍTICA":
                    st.error(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")
                elif c["criticidade"] == "GRAVE":
                    st.warning(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")
                else:
                    st.info(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")

        st.subheader("📄 Parecer técnico completo")
        st.text_area("Parecer para copiar", relatorio, height=650)

        st.download_button(
            "⬇️ Baixar parecer em TXT",
            data=relatorio,
            file_name="raio_x_ppp_parecer.txt",
            mime="text/plain",
            use_container_width=True
        )
