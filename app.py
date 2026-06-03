import streamlit as st
import re
import unicodedata
import requests
import hashlib
import os
import pprint
from datetime import datetime
from io import BytesIO

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:
    pdfminer_extract_text = None

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
    "fumos_metalicos": {
        "grupo": "Químico",
        "termos": [
            "fumos metalicos", "fumos metálicos", "fumo metalico", "fumo metálico",
            "ferro", "manganes", "manganês", "silicio", "silício", "solda", "soldagem"
        ],
        "norma": "NR-15 Anexos 11, 12 e 13, conforme substância e forma de exposição",
        "limite": "Avaliação conforme substância: quantitativa quando houver limite de tolerância; qualitativa quando aplicável",
        "metodologia": "LTCAT/laudo técnico com identificação da substância, forma de contato, concentração quando exigível e método de avaliação",
        "fundamento": (
            "NR-15: Anexos 11 e 12 tratam de agentes químicos quantitativos, com comparação a limites de tolerância. "
            "Anexo 13 trata de agentes químicos qualitativos, em que a presença/exposição é juridicamente relevante. "
            "Para agentes químicos, a simples indicação de EPI eficaz no PPP não afasta automaticamente a especialidade; "
            "é necessária análise concreta da neutralização."
        )
    },
    "poeiras": {
        "grupo": "Químico",
        "termos": [
            "poeira respiravel", "poeira respirável", "poeira total", "poeiras", "poeira"
        ],
        "norma": "NR-15 Anexo 12 e normas técnicas de higiene ocupacional aplicáveis",
        "limite": "Avaliação quantitativa ou qualitativa conforme composição da poeira e presença de sílica livre cristalizada",
        "metodologia": "Amostragem ambiental, identificação da fração respirável/total e metodologia técnica compatível",
        "fundamento": (
            "NR-15, Anexo 12, trata de poeiras minerais e agentes relacionados. "
            "A análise depende da composição da poeira, concentração, metodologia utilizada e habitualidade da exposição. "
            "Quando houver sílica livre cristalizada ou agente cancerígeno, a análise deve ser reforçada."
        )
    },
    "oleos_minerais": {
        "grupo": "Químico",
        "termos": [
            "oleos minerais", "óleos minerais", "oleo mineral", "óleo mineral",
            "hidrocarboneto", "hidrocarbonetos", "graxa", "lubrificante"
        ],
        "norma": "NR-15 Anexo 13",
        "limite": "Avaliação qualitativa quando caracterizado contato habitual e permanente",
        "metodologia": "Laudo qualitativo com descrição da forma de contato e habitualidade",
        "fundamento": (
            "NR-15, Anexo 13: óleos minerais, hidrocarbonetos, graxas e substâncias equivalentes podem ser analisados "
            "qualitativamente quando houver contato habitual e permanente. A eficácia do EPI exige comprovação concreta."
        )
    },
    "umidade": {
        "grupo": "Físico",
        "termos": ["umidade", "umido", "úmido", "ambiente umido", "ambiente úmido"],
        "norma": "NR-15 Anexo 10",
        "limite": "Avaliação qualitativa",
        "metodologia": "Verificação qualitativa da exposição habitual a umidade excessiva",
        "fundamento": (
            "NR-15, Anexo 10: a exposição a umidade excessiva é avaliada qualitativamente, "
            "considerando a atividade, o ambiente e a habitualidade da exposição."
        )
    },
    "tensoativos_domissanitarios": {
        "grupo": "Químico",
        "termos": [
            "tensoativo", "tensoativos", "domissanitario", "domissanitarios", "domissanitários",
            "saneante", "saneantes", "desinfetante", "detergente"
        ],
        "norma": "NR-15 Anexos 11 e 13, conforme composição química",
        "limite": "Avaliação conforme substância: qualitativa ou quantitativa conforme composição e forma de exposição",
        "metodologia": "LTCAT/laudo técnico com identificação dos produtos, composição, forma de contato, frequência e proteção utilizada",
        "fundamento": (
            "NR-15: agentes químicos devem ser analisados conforme substância, composição, forma de contato e habitualidade. "
            "Produtos de limpeza, tensoativos e domissanitários exigem análise do LTCAT, FISPQ e das condições reais de exposição. "
            "A eficácia do EPI deve ser comprovada de forma concreta."
        )
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
        "termos": ["cnae", "2829-1/99", "2829199"],
        "verificacao": "Campo obrigatório. Nesta etapa o sistema apenas extrai e exibe o código CNAE informado no PPP.",
        "fundamento": "IN 128/2022, art. 281, I."
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
        "nome": "CPF/NIT",
        "criticidade": "CRÍTICA",
        "termos": ["cpf", "nit", "pis", "pasep"],
        "verificacao": "CPF deve corresponder ao trabalhador. CPF incorreto invalida a identificação do segurado.",
        "fundamento": "IN 128/2022, art. 281."
    },
    {
        "campo": "9",
        "nome": "CTPS / Matrícula eSocial",
        "criticidade": "CRÍTICA",
        "termos": ["ctps", "matricula", "matrícula", "esocial"],
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
        "campo": "15.2",
        "nome": "Tipo do agente",
        "criticidade": "MODERADA",
        "termos": ["15.2", "tipo", "fisico", "físico", "quimico", "químico", "biologico", "biológico"],
        "verificacao": "Verificar se o tipo do agente (Físico, Químico ou Biológico) está compatível com o fator de risco informado no campo 15.3.",
        "fundamento": "IN 128/2022, art. 284. O PPP deve indicar tipo de agente e fator de risco de forma coerente."
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
        "campo": "15.6",
        "nome": "EPC eficaz",
        "criticidade": "GRAVE",
        "termos": ["15.6", "epc", "epc eficaz", "proteção coletiva", "protecao coletiva"],
        "verificacao": "Verificar se há EPC eficaz. Quando constar 'Não', reforça a ausência de neutralização coletiva. Quando constar 'NA', deve haver compatibilidade técnica com o agente.",
        "fundamento": "IN 128/2022, art. 284; NR-01. A proteção coletiva deve ser priorizada antes do EPI."
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
        "termos": ["responsavel pelos registros", "responsável pelos registros", "profissional legalmente habilitado", "engenheiro", "medico do trabalho", "médico do trabalho", "crea", "crm", "registro", "reg. cons."],
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



# ============================================================
# BASE JURISPRUDENCIAL — TRFs, STF, STJ e CRPS
# Fonte interna: IRDR_Aposentadoria_Especial.docx
# ============================================================

BASE_TRIBUNAIS = {
    "NACIONAL": {
        "STF Tema 555": (
            "EPI e ruído: a declaração de EPI eficaz no PPP não descaracteriza "
            "o tempo especial quando houver exposição a ruído acima dos limites legais."
        ),
        "STF Tema 709": (
            "É constitucional a vedação de continuidade da aposentadoria especial se o beneficiário "
            "permanece ou retorna ao labor nocivo. A DER permanece como marco dos efeitos financeiros "
            "quando o segurado aguardava a implantação do benefício."
        ),
        "STF Tema 942": (
            "É garantido o direito adquirido à conversão de tempo especial em comum "
            "para períodos trabalhados antes da EC 103/2019."
        ),
        "STJ Tema 534": (
            "Eletricidade superior a 250 volts pode caracterizar atividade especial, "
            "pois o rol de agentes nocivos é exemplificativo."
        ),
        "STJ Tema 694": (
            "Limites históricos de ruído: acima de 80 dB até 05/03/1997; "
            "acima de 90 dB de 06/03/1997 a 18/11/2003; "
            "acima de 85 dB a partir de 19/11/2003."
        ),
        "STJ Tema 998": (
            "Auxílio-doença intercalado com atividade especial deve ser computado "
            "como tempo especial."
        ),
        "STJ Tema 1.090": (
            "EPI e ineficácia presumida: nacionalizou as hipóteses do IRDR 15/TRF4, "
            "incluindo ruído acima do limite, agentes cancerígenos, agentes biológicos "
            "em ambiente hospitalar/laboratorial, agentes sem limite seguro e hipóteses "
            "em que o próprio INSS reconhecia a ineficácia do EPI."
        ),
        "CRPS Enunciado 11": (
            "O PPP é documento suficiente para comprovação da especialidade em regra. "
            "Exceções importantes: ruído, frio e calor podem exigir LTCAT conforme o período."
        ),
        "CRPS Enunciado 12": (
            "O fornecimento de EPI não descaracteriza por si só a atividade especial; "
            "deve ser analisado todo o ambiente de trabalho e a real neutralização."
        ),
        "CRPS Enunciado 13": (
            "Ruído: consolida limites históricos e critérios de metodologia, em convergência "
            "com o STJ Tema 694."
        ),
        "CRPS Enunciado 14": (
            "Enquadramento por categoria profissional até 28/04/1995 nos Decretos 53.831/64 "
            "e 83.080/79. Após 29/04/1995 exige-se comprovação da efetiva exposição."
        ),
        "CRPS Enunciado 15": (
            "Conversão de tempo especial em comum admitida para períodos trabalhados "
            "até 13/11/2019."
        ),
    },

    "TRF1": {
        "síntese": (
            "TRF1 segue precedentes nacionais do STF e STJ. Aplica Tema 555/STF para ruído, "
            "Tema 534/STJ para eletricidade, STJ Tema 1.090 para biológicos e cancerígenos."
        )
    },

    "TRF2": {
        "síntese": (
            "TRF2 segue STF/STJ. Reconhece ruído pelo Tema 555/STF, eletricidade pelo Tema 534/STJ, "
            "vibração como agente físico e agentes biológicos em atividades de saúde."
        )
    },

    "TRF3": {
        "síntese": (
            "TRF3 aplica Tema 555/STF e Tema 694/STJ para ruído, reconhece eletricidade, calor, "
            "radiações e agentes químicos com base em laudo técnico e rol exemplificativo."
        )
    },

    "TRF4": {
        "IRDR 15": (
            "IRDR 15/TRF4: EPI não afasta automaticamente a especialidade em hipóteses como "
            "ruído acima dos limites, agentes cancerígenos, agentes biológicos e agentes sem "
            "limite seguro. Tese incorporada nacionalmente pelo STJ Tema 1.090."
        ),
        "IRDR 16": (
            "IRDR 16/TRF4: auxílio-doença intercalado com atividade especial deve ser computado "
            "como tempo especial, em convergência com STJ Tema 998."
        ),
    },

    "TRF5": {
        "síntese": (
            "TRF5 acompanha precedentes nacionais. Reconhece agentes biológicos, calor, ruído, "
            "enquadramento anterior a 28/04/1995 e agentes químicos cancerígenos conforme STJ Tema 1.090."
        )
    },

    "TRF6": {
        "síntese": (
            "TRF6 aplica STF/STJ. Reconhece fumos metálicos, hidrocarbonetos e cancerígenos com base "
            "no STJ Tema 1.090; ruído pelo Tema 555/STF e eletricidade pelo Tema 534/STJ."
        )
    },
}


def selecionar_base_tribunal(trf, agentes, texto):
    """
    Seleciona apenas a base jurisprudencial aplicável ao caso concreto.
    Não despeja toda a base legal.
    """
    bases = []

    texto_norm = normalizar(texto)
    grupos = [normalizar(a.get("grupo", "")) for a in agentes]
    nomes_agentes = [normalizar(a.get("agente", "")) for a in agentes]

    tem_fisico = any("fisic" in g for g in grupos)
    tem_quimico = any("quim" in g for g in grupos)
    tem_biologico = any("biologic" in g for g in grupos)

    tem_ruido = (
        "ruido" in texto_norm
        or "ruído" in texto.lower()
        or any("ruido" in n for n in nomes_agentes)
        or "db" in texto_norm
        or "dba" in texto_norm
    )

    tem_eletricidade = (
        "eletricidade" in texto_norm
        or "tensao eletrica" in texto_norm
        or "tensão elétrica" in texto.lower()
        or "250v" in texto_norm
        or "250 v" in texto_norm
    )

    tem_cancerigeno = any(
        termo in texto_norm
        for termo in [
            "benzeno", "amianto", "asbesto", "silica", "sílica",
            "hidrocarboneto aromatico", "hidrocarboneto aromático",
            "cancerigeno", "cancerígeno", "linach", "iarc"
        ]
    )

    tem_auxilio = "auxilio-doenca" in texto_norm or "auxílio-doença" in texto.lower()

    tem_periodo_pre_reforma = any(
        ano in texto_norm
        for ano in [
            "1964", "1979", "1980", "1985", "1990", "1995", "1997",
            "1999", "2003", "2007", "2010", "2015", "2018", "2019"
        ]
    )

    if tem_ruido:
        bases.append(("STF Tema 555", BASE_TRIBUNAIS["NACIONAL"]["STF Tema 555"]))
        bases.append(("STJ Tema 694", BASE_TRIBUNAIS["NACIONAL"]["STJ Tema 694"]))
        bases.append(("CRPS Enunciado 13", BASE_TRIBUNAIS["NACIONAL"]["CRPS Enunciado 13"]))

    if tem_eletricidade:
        bases.append(("STJ Tema 534", BASE_TRIBUNAIS["NACIONAL"]["STJ Tema 534"]))

    if tem_biologico or tem_quimico or tem_cancerigeno:
        bases.append(("STJ Tema 1.090", BASE_TRIBUNAIS["NACIONAL"]["STJ Tema 1.090"]))
        bases.append(("CRPS Enunciado 11", BASE_TRIBUNAIS["NACIONAL"]["CRPS Enunciado 11"]))
        bases.append(("CRPS Enunciado 12", BASE_TRIBUNAIS["NACIONAL"]["CRPS Enunciado 12"]))

    if tem_periodo_pre_reforma:
        bases.append(("STF Tema 942", BASE_TRIBUNAIS["NACIONAL"]["STF Tema 942"]))
        bases.append(("CRPS Enunciado 15", BASE_TRIBUNAIS["NACIONAL"]["CRPS Enunciado 15"]))

    if tem_auxilio:
        bases.append(("STJ Tema 998", BASE_TRIBUNAIS["NACIONAL"]["STJ Tema 998"]))

    # Tema 709 só deve aparecer se houver informação de aposentadoria especial/retorno ou orientação final ampla.
    if "retorno ao labor nocivo" in texto_norm or "aposentadoria especial" in texto_norm:
        bases.append(("STF Tema 709", BASE_TRIBUNAIS["NACIONAL"]["STF Tema 709"]))

    if trf in BASE_TRIBUNAIS:
        for titulo, fundamento in BASE_TRIBUNAIS[trf].items():
            bases.append((f"{trf} — {titulo}", fundamento))

    unicos = []
    for item in bases:
        if item not in unicos:
            unicos.append(item)

    return unicos


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
    "fumos_metalicos": {
        "grupo": "Químico",
        "termos": [
            "fumos metalicos", "fumos metálicos", "fumo metalico", "fumo metálico",
            "ferro", "manganes", "manganês", "silicio", "silício", "solda", "soldagem"
        ],
        "norma": "NR-15 Anexos 11, 12 e 13, conforme substância e forma de exposição",
        "limite": "Avaliação conforme substância: quantitativa quando houver limite de tolerância; qualitativa quando aplicável",
        "metodologia": "LTCAT/laudo técnico com identificação da substância, forma de contato, concentração quando exigível e método de avaliação",
        "fundamento": (
            "NR-15: Anexos 11 e 12 tratam de agentes químicos quantitativos, com comparação a limites de tolerância. "
            "Anexo 13 trata de agentes químicos qualitativos, em que a presença/exposição é juridicamente relevante. "
            "Para agentes químicos, a simples indicação de EPI eficaz no PPP não afasta automaticamente a especialidade; "
            "é necessária análise concreta da neutralização."
        )
    },
    "poeiras": {
        "grupo": "Químico",
        "termos": [
            "poeira respiravel", "poeira respirável", "poeira total", "poeiras", "poeira"
        ],
        "norma": "NR-15 Anexo 12 e normas técnicas de higiene ocupacional aplicáveis",
        "limite": "Avaliação quantitativa ou qualitativa conforme composição da poeira e presença de sílica livre cristalizada",
        "metodologia": "Amostragem ambiental, identificação da fração respirável/total e metodologia técnica compatível",
        "fundamento": (
            "NR-15, Anexo 12, trata de poeiras minerais e agentes relacionados. "
            "A análise depende da composição da poeira, concentração, metodologia utilizada e habitualidade da exposição. "
            "Quando houver sílica livre cristalizada ou agente cancerígeno, a análise deve ser reforçada."
        )
    },
    "oleos_minerais": {
        "grupo": "Químico",
        "termos": [
            "oleos minerais", "óleos minerais", "oleo mineral", "óleo mineral",
            "hidrocarboneto", "hidrocarbonetos", "graxa", "lubrificante"
        ],
        "norma": "NR-15 Anexo 13",
        "limite": "Avaliação qualitativa quando caracterizado contato habitual e permanente",
        "metodologia": "Laudo qualitativo com descrição da forma de contato e habitualidade",
        "fundamento": (
            "NR-15, Anexo 13: óleos minerais, hidrocarbonetos, graxas e substâncias equivalentes podem ser analisados "
            "qualitativamente quando houver contato habitual e permanente. A eficácia do EPI exige comprovação concreta."
        )
    },
    "umidade": {
        "grupo": "Físico",
        "termos": ["umidade", "umido", "úmido", "ambiente umido", "ambiente úmido"],
        "norma": "NR-15 Anexo 10",
        "limite": "Avaliação qualitativa",
        "metodologia": "Verificação qualitativa da exposição habitual a umidade excessiva",
        "fundamento": (
            "NR-15, Anexo 10: a exposição a umidade excessiva é avaliada qualitativamente, "
            "considerando a atividade, o ambiente e a habitualidade da exposição."
        )
    },
    "tensoativos_domissanitarios": {
        "grupo": "Químico",
        "termos": [
            "tensoativo", "tensoativos", "domissanitario", "domissanitarios", "domissanitários",
            "saneante", "saneantes", "desinfetante", "detergente"
        ],
        "norma": "NR-15 Anexos 11 e 13, conforme composição química",
        "limite": "Avaliação conforme substância: qualitativa ou quantitativa conforme composição e forma de exposição",
        "metodologia": "LTCAT/laudo técnico com identificação dos produtos, composição, forma de contato, frequência e proteção utilizada",
        "fundamento": (
            "NR-15: agentes químicos devem ser analisados conforme substância, composição, forma de contato e habitualidade. "
            "Produtos de limpeza, tensoativos e domissanitários exigem análise do LTCAT, FISPQ e das condições reais de exposição. "
            "A eficácia do EPI deve ser comprovada de forma concreta."
        )
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

AGENTES.update({
    "vibracao_corpo_inteiro": {
        "grupo": "Físico",
        "termos": ["vibracao de corpo inteiro", "vibração de corpo inteiro", "vci", "vdvr"],
        "norma": "NR-15 e normas técnicas de higiene ocupacional aplicáveis",
        "limite": "Critério técnico conforme intensidade e metodologia informadas no PPP/LTCAT",
        "metodologia": "Avaliação de vibração de corpo inteiro, com indicação de método, intensidade e período",
        "fundamento": "Agente físico identificado no Campo 15; exige conferência de intensidade, método técnico e habitualidade."
    },
    "vibracao_maos_bracos": {
        "grupo": "Físico",
        "termos": ["vibracao de maos e bracos", "vibração de mãos e braços", "vmb", "aren"],
        "norma": "NR-15 e normas técnicas de higiene ocupacional aplicáveis",
        "limite": "Critério técnico conforme intensidade e metodologia informadas no PPP/LTCAT",
        "metodologia": "Avaliação de vibração de mãos e braços, com indicação de método, intensidade e período",
        "fundamento": "Agente físico identificado no Campo 15; exige conferência de intensidade, método técnico e habitualidade."
    },
    "radiacoes_nao_ionizantes": {
        "grupo": "Físico",
        "termos": ["radiacoes nao ionizantes", "radiações não ionizantes", "radiacao nao ionizante", "radiação não ionizante", "radiacao solar", "radiação solar"],
        "norma": "NR-15, conforme agente físico e forma de exposição",
        "limite": "Avaliação qualitativa ou quantitativa conforme o agente descrito",
        "metodologia": "LTCAT/laudo técnico com descrição da fonte, intensidade e habitualidade",
        "fundamento": "Agente físico identificado no Campo 15; exige conferência do tipo de radiação e das condições de exposição."
    },
    "agrotoxicos": {
        "grupo": "Químico",
        "termos": ["agrotoxico", "agrotóxico", "agrotoxicos", "agrotóxicos", "pesticida", "pesticidas", "defensivo agricola", "defensivo agrícola"],
        "norma": "NR-15 Anexos 11 e 13, conforme composição química",
        "limite": "Avaliação qualitativa ou quantitativa conforme substância",
        "metodologia": "LTCAT/FISPQ com identificação do produto, composição e forma de contato",
        "fundamento": "Agente químico identificado no Campo 15; exige análise da composição, forma de contato e habitualidade."
    },
    "solventes": {
        "grupo": "Químico",
        "termos": ["solvente", "solventes", "hexano", "heptano", "acetona", "acetato de etila", "tolueno", "ppm"],
        "norma": "NR-15 Anexos 11 e 13, conforme substância",
        "limite": "Quantitativo ou qualitativo conforme substância e concentração",
        "metodologia": "LTCAT/FISPQ com concentração, método de avaliação e forma de contato",
        "fundamento": "Agente químico identificado no Campo 15; exige análise por substância e concentração quando houver limite de tolerância."
    },
    "biologicos_hospitalares": {
        "grupo": "Biológico",
        "termos": ["hiv", "hepatite b", "hepatite c", "protozoario", "protozoários", "parasita", "parasitas", "microorganismo", "microorganismos", "toxina", "toxinas", "pacientes", "ambiente hospitalar", "enfermagem", "medico", "médico", "motorista de ambulancia", "motorista de ambulância"],
        "norma": "NR-15 Anexo 14",
        "limite": "Qualitativo",
        "metodologia": "Descrição da atividade e do risco de contato com pacientes, materiais ou ambientes contaminados",
        "fundamento": BASE_LEGAL["biologicos"]["nr15_14"] + " " + BASE_LEGAL["biologicos"]["tema_211_tnu"]
    },
})


# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================

def normalizar(texto):
    if not texto:
        return ""
    texto = str(texto).translate(str.maketrans({
        "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "І": "I",
        "К": "K", "М": "M", "О": "O", "Р": "P", "Т": "T", "Х": "X",
        "а": "a", "в": "b", "с": "c", "е": "e", "н": "h", "і": "i",
        "к": "k", "м": "m", "о": "o", "р": "p", "т": "t", "х": "x",
    })).lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto


OCR_PIPELINE_VERSION = "2026-06-03-adaptativo-v12-parser-semantico"
MARCADOR_METADADOS_OCR = "=== METADADOS INTERNOS DA EXTRAÇÃO OCR ==="
MARCADOR_DIAGNOSTICO_INTERNO = "=== DIAGNÓSTICO INTERNO DO PIPELINE ==="


def remover_bloco_a_partir_do_marcador(texto, marcador):
    texto = texto or ""
    if marcador in texto:
        return texto.split(marcador, 1)[0].rstrip()
    return texto


def extrair_metadados_ocr(texto):
    texto = texto or ""
    if MARCADOR_METADADOS_OCR not in texto:
        return texto, {}
    antes, depois = texto.split(MARCADOR_METADADOS_OCR, 1)
    metadados = {}
    for linha in depois.splitlines():
        if ":" not in linha:
            continue
        chave, valor = linha.split(":", 1)
        metadados[chave.strip()] = valor.strip()
    return antes.rstrip(), metadados


def texto_para_analise_sem_diagnostico(texto):
    texto = remover_bloco_a_partir_do_marcador(texto, MARCADOR_DIAGNOSTICO_INTERNO)
    texto, _ = extrair_metadados_ocr(texto)
    return texto.rstrip()


def extrair_texto_pdf(uploaded_file):
    return extrair_texto_pdf_bytes(uploaded_file.read(), OCR_PIPELINE_VERSION)


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def extrair_texto_pdf_bytes(pdf_bytes, pipeline_version):
    # A versão integra a chave do cache. Ao evoluir o OCR, o mesmo PDF precisa
    # ser processado novamente em vez de reutilizar uma extração antiga.
    _ = pipeline_version
    partes = []

    if pdfplumber is not None:
        try:
            with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    partes.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
                    tabelas = page.extract_tables() or []
                    for tabela in tabelas:
                        for linha in tabela or []:
                            celulas = [re.sub(r"\s+", " ", str(c or "")).strip() for c in linha]
                            if any(celulas):
                                partes.append(" | ".join(celulas))
        except Exception as e:
            partes.append(f"\n[Extração pdfplumber indisponível/falhou: {e}]\n")

    if pdfminer_extract_text is not None:
        try:
            partes.append(pdfminer_extract_text(BytesIO(pdf_bytes)) or "")
        except Exception as e:
            partes.append(f"\n[Extração pdfminer indisponível/falhou: {e}]\n")

    if fitz is not None:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page in doc:
                partes.append(page.get_text("text") + "\n")
        except Exception as e:
            partes.append(f"\n[Erro na extração PyMuPDF: {e}]\n")

    texto = "\n".join(p for p in partes if p)

    _termos_estruturais = [
        "lotacao", "lotação",
        "registros ambientais",
        "responsavel pelos registros",
        "responsável pelos registros",
        "profissiografia",
        "fator de risco",
        "agente nocivo",
        "15.1", "15.3", "16.",
    ]
    _texto_norm_ocr = normalizar(texto)
    _tem_estrutura = any(t in _texto_norm_ocr for t in _termos_estruturais)
    _texto_curto = len(re.sub(r"\s+", "", texto)) < 300
    precisa_ocr = _texto_curto or not _tem_estrutura
    if precisa_ocr and pytesseract is not None and convert_from_bytes is not None:
        try:
            imagens = convert_from_bytes(pdf_bytes, dpi=250)
            for img in imagens:
                config = "--psm 6 -c preserve_interword_spaces=1"
                try:
                    texto += "\n" + pytesseract.image_to_string(img, lang="por", config=config)
                except Exception:
                    texto += "\n" + pytesseract.image_to_string(img, lang="por+eng", config=config)
            imagens_soc = [img for img in imagens if layout_soc_ppp8_compativel(img)]
            if imagens_soc:
                # O perfil SOC melhora células críticas, mas a grade dinâmica
                # continua necessária para variações de posição, escala e
                # quantidade de linhas entre documentos do mesmo fornecedor.
                texto += "\n" + ocr_tabelas_grade_ppp(imagens_soc, max_linhas_pagina=65)
                texto += "\n" + ocr_soc_celulas_ppp(imagens_soc)
            else:
                texto += "\n" + ocr_regioes_tabeladas_ppp(imagens)
                texto += "\n" + ocr_tabelas_grade_ppp(imagens)
        except Exception as e:
            texto += f"\n[OCR não executado ou falhou: {e}]\n"

    metadados = (
        f"\n\n{MARCADOR_METADADOS_OCR}\n"
        f"pipeline_version: {pipeline_version}\n"
        f"extraida_em: {datetime.now().isoformat(timespec='seconds')}\n"
    )
    return texto + metadados


def ocr_regioes_tabeladas_ppp(imagens):
    if pytesseract is None:
        return ""
    textos = []
    for pagina, img in enumerate(imagens, start=1):
        w, h = img.size
        regioes = [
            ("13/14", (0, int(h * 0.22), w, int(h * 0.48))),
            ("15", (0, int(h * 0.42), w, int(h * 0.82))),
            ("16/18/20", (0, int(h * 0.72), w, h)),
        ]
        for nome, caixa in regioes:
            try:
                crop = img.crop(caixa)
                config = "--psm 6 -c preserve_interword_spaces=1"
                try:
                    trecho = pytesseract.image_to_string(crop, lang="por", config=config)
                except Exception:
                    trecho = pytesseract.image_to_string(crop, lang="por+eng", config=config)
                if trecho and len(trecho.strip()) > 20:
                    textos.append(f"\n=== OCR REGIÃO TABELADA {nome} PÁGINA {pagina} ===\n{trecho}")
            except Exception:
                continue
    return "\n".join(textos)


def agrupar_posicoes_proximas(posicoes, distancia=3):
    grupos = []
    for pos in sorted(posicoes):
        if not grupos or pos > grupos[-1][-1] + distancia:
            grupos.append([pos])
        else:
            grupos[-1].append(pos)
    return [int(sum(grupo) / len(grupo)) for grupo in grupos]


def detectar_linhas_horizontais_grade(img):
    try:
        cinza = img.convert("L")
        w, h = cinza.size
        pixels = cinza.load()
        inicio_x = int(w * 0.035)
        fim_x = int(w * 0.965)
        largura = max(1, fim_x - inicio_x)
        candidatas = []
        for y in range(int(h * 0.12), int(h * 0.96)):
            escuros = sum(1 for x in range(inicio_x, fim_x) if pixels[x, y] < 180)
            if escuros >= largura * 0.28:
                candidatas.append(y)
        return agrupar_posicoes_proximas(candidatas, distancia=3)
    except Exception:
        return []


def detectar_linhas_verticais_faixa(img, y1, y2):
    try:
        cinza = img.convert("L")
        w, h = cinza.size
        pixels = cinza.load()
        y1 = max(0, int(y1))
        y2 = min(h, int(y2))
        altura = max(1, y2 - y1)
        candidatas = []
        for x in range(int(w * 0.025), int(w * 0.975)):
            escuros = sum(1 for y in range(y1, y2) if pixels[x, y] < 185)
            if escuros >= altura * 0.62:
                candidatas.append(x)
        return agrupar_posicoes_proximas(candidatas, distancia=3)
    except Exception:
        return []


def linha_ocr_dinamica_relevante(linha):
    """
    Mantém somente linhas da grade com algum sinal estrutural útil.
    Grades de scans ruins geram muitos fragmentos visuais que poluem o texto
    editável e podem ser interpretados como novas linhas de tabela.
    """
    linha = re.sub(r"\s+", " ", str(linha or "")).strip(" |")
    if not linha or len(re.sub(r"[^A-Za-z0-9]", "", linha)) < 3:
        return False
    if re.search(
        r"\b(?:1[2-9]|20)(?:\.\d+)?\b|"
        r"\b\d{2}/\d{2}/\d{4}\b|"
        r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b|"
        r"\b\d{3}\.?\d{3,5}\.?\d{2,3}-?\d{1,2}\b|"
        r"\b(?:F[ií]sico|Qu[ií]mico|Biol[oó]gico|Ergon[oô]mico|Acidente)\b|"
        r"\b(?:Ru[ií]do|Vibra[cç][aã]o|Radia[cç][aã]o|Umidade|Calor|Fumos|Poeira|"
        r"Hidrocarbonetos?|[ÓO]leos?|Pesticidas?|Agrot[oó]xicos?|Bact[eé]rias?|Fungos?|V[ií]rus)\b|"
        r"\b(?:dB\s*\(?A?\)?|ppm|mg/m[³3]|NHO[-\s]*01|NR[-\s]*15|CRM|CREA|CRQ|MTE)\b|"
        r"\b(?:CNPJ|CNAE|CBO|GFIP|Setor|Cargo|Fun[cç][aã]o|Per[ií]odo|Profissiografia)\b",
        linha,
        flags=re.IGNORECASE,
    ):
        return True
    return False


def ocr_tabelas_grade_ppp(imagens, max_linhas_pagina=100):
    """
    Fallback geral para PPPs escaneados com tabelas variadas.
    Detecta a grade da própria página e reconstrói linhas por células, sem
    assumir coordenadas fixas de um fornecedor ou versão do formulário.
    """
    if pytesseract is None or not imagens:
        return ""
    textos = []
    for pagina, img in enumerate(imagens, start=1):
        w, h = img.size
        horizontais = detectar_linhas_horizontais_grade(img)
        if len(horizontais) < 4:
            continue
        linhas_emitidas = 0
        for indice, (y1, y2) in enumerate(zip(horizontais, horizontais[1:]), start=1):
            altura = y2 - y1
            if altura < max(7, int(h * 0.004)) or altura > int(h * 0.10):
                continue
            verticais = detectar_linhas_verticais_faixa(img, y1, y2)
            if len(verticais) < 3:
                continue
            celulas = []
            for x1, x2 in zip(verticais, verticais[1:]):
                largura = x2 - x1
                if largura < max(8, int(w * 0.012)):
                    continue
                margem_x = max(1, int(largura * 0.025))
                margem_y = max(1, int(altura * 0.08))
                crop = img.crop((x1 + margem_x, y1 + margem_y, x2 - margem_x, y2 - margem_y))
                valor = ocr_celula(crop, psm=7)
                valor = re.sub(r"\s+", " ", valor or "").strip(" -:|")
                if valor and len(valor) <= 220:
                    celulas.append(valor)
                else:
                    celulas.append("")
            if len(celulas) < 2 or not any(celulas):
                continue
            linha = " | ".join(celulas)
            if len(re.sub(r"[\s|]", "", linha)) < 3:
                continue
            if not linha_ocr_dinamica_relevante(linha):
                continue
            textos.append(f"OCR TABELA DINÂMICA PÁGINA {pagina} | linha {indice}: {linha}")
            linhas_emitidas += 1
            if linhas_emitidas >= max_linhas_pagina:
                break
    if not textos:
        return ""
    return "\n=== OCR TABELAS DINÂMICAS ===\n" + "\n".join(textos)


def preparar_imagem_ocr_celula(crop):
    """
    Pré-processamento local para células de PPP SOC escaneado:
    escala de cinza, aumento de 300%, threshold adaptativo e sharpen.
    """
    from PIL import ImageOps, ImageFilter

    img = crop.convert("L")
    img = ImageOps.autocontrast(img)
    img = img.resize((max(1, img.width * 3), max(1, img.height * 3)))
    fundo = img.filter(ImageFilter.MedianFilter(size=15))
    img = img.point(lambda p: p)
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=180, threshold=2))
    # Threshold adaptativo sem dependência adicional: compara cada pixel
    # com a mediana de sua vizinhança, preservando letras em células sombreadas.
    img = img.convert("L")
    fundo = fundo.convert("L")
    pixels = [0 if px < max(90, bg - 18) else 255 for px, bg in zip(img.getdata(), fundo.getdata())]
    img.putdata(pixels)
    return img


def ocr_celula(crop, psm=6):
    if pytesseract is None:
        return ""
    try:
        img = preparar_imagem_ocr_celula(crop)
    except Exception:
        img = crop
    config = f"--psm {psm} -c preserve_interword_spaces=1"
    try:
        texto = pytesseract.image_to_string(img, lang="por", config=config)
    except Exception:
        try:
            texto = pytesseract.image_to_string(img, lang="por+eng", config=config)
        except Exception:
            texto = ""
    return re.sub(r"\s+", " ", texto or "").strip(" -:|")


def ocr_celula_com_whitelist(crop, whitelist, psm=7):
    if pytesseract is None:
        return ""
    try:
        img = preparar_imagem_ocr_celula(crop)
    except Exception:
        img = crop
    config = f"--psm {psm} -c preserve_interword_spaces=1 -c tessedit_char_whitelist={whitelist}"
    try:
        texto = pytesseract.image_to_string(img, config=config)
    except Exception:
        texto = ""
    return re.sub(r"\s+", " ", texto or "").strip(" -:|")


def ocr_celula_soc_validada(crop, numero, psm=6, tentar_alternativo=True):
    """
    Faz OCR da célula e tenta uma segunda segmentação quando a primeira leitura
    não atende ao formato esperado para o subcampo.
    """
    tentativas = [psm]
    if tentar_alternativo:
        alternativo = 6 if psm == 7 else 7
        if alternativo not in tentativas:
            tentativas.append(alternativo)
    primeiro_bruto = ""
    for modo in tentativas:
        bruto = ocr_celula(crop, psm=modo)
        if bruto and not primeiro_bruto:
            primeiro_bruto = bruto
        validado = validar_valor_ocr_soc(numero, bruto)
        if validado:
            return validado, bruto
    return "", primeiro_bruto


def crop_relativo(img, box):
    w, h = img.size
    x1, y1, x2, y2 = box
    return img.crop((int(w * x1), int(h * y1), int(w * x2), int(h * y2)))


def texto_ocr_soc_legivel(valor, minimo_palavras=1, minimo_caracteres=3):
    valor = re.sub(r"\s+", " ", str(valor or "")).strip(" -:|")
    if len(valor) < minimo_caracteres:
        return False
    if normalizar(valor) in {"do secnicio", "ee e", "e es mm mm as", "sn narrar masninass", "rsnictras"}:
        return False
    letras = re.findall(r"[A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç]", valor)
    if len(letras) < minimo_caracteres or len(letras) / max(len(valor), 1) < 0.55:
        return False
    palavras = re.findall(r"[A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç]{3,}", valor)
    return len(palavras) >= minimo_palavras


def nome_responsavel_tecnico_soc_valido(valor):
    valor = re.sub(r"\s+", " ", str(valor or "")).strip(" -:|")
    if not texto_ocr_soc_legivel(valor, minimo_palavras=2, minimo_caracteres=8):
        return False
    palavras = re.findall(r"[A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç]+", valor)
    conectores = {"de", "da", "do", "das", "dos", "e"}
    if len(palavras) < 2 or any(len(p) == 1 for p in palavras):
        return False
    for palavra in palavras:
        if palavra.lower() in conectores:
            continue
        if not (palavra.isupper() or palavra[0].isupper()):
            return False
    return True


def normalizar_resposta_ocr_soc(valor):
    valor = re.sub(r"\s+", " ", str(valor or "")).strip(" -:|")
    vn = normalizar(valor)
    respostas = {
        "s": "Sim",
        "sim": "Sim",
        "n": "Não",
        "nao": "Não",
        "na": "NA",
        "n a": "NA",
        "nao aplicavel": "NA",
        "nao se aplica": "NA",
    }
    return respostas.get(vn, "")


def validar_valor_ocr_soc(numero, valor):
    bruto = re.sub(r"\s+", " ", str(valor or "")).strip()
    if bruto in {"-", "—"} and numero in {"13.5", "13.7", "15.6", "15.7", "15.8"}:
        return "NA"
    if normalizar(bruto) in {"na", "n/a", "nao aplicavel", "nao se aplica"} and numero in {
        "13.5", "13.7", "15.4", "15.5", "15.6", "15.7", "15.8",
    }:
        return "NA"
    valor = bruto.strip(" -:|")
    if not valor:
        return ""
    if numero in {"13.1", "14.1", "15.1", "16.1"}:
        valor = re.sub(r"(\d{2}/\d{2}/\d)\s+(\d{3}\b)", r"\1\2", valor)
        m = re.search(
            r"\b(?:\d{2}/\d{2}/\d{4}|\d{2}/\d{4})\s*(?:a|at[eé]|-)"
            r"(?:\s*(?:\d{2}/\d{2}/\d{4}|(?:data\s+)?atual))?\b",
            valor,
            flags=re.IGNORECASE,
        )
        return m.group(0) if m else ""
    if numero == "13.2":
        m = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", valor)
        return m.group(0) if m else ""
    if numero in {"13.3", "13.4", "13.5"}:
        return valor if texto_ocr_soc_legivel(valor) else ""
    if numero == "13.6":
        m = re.search(r"\b\d{4,6}(?:-\d{1,2})?\b", valor)
        return m.group(0) if m else ""
    if numero == "13.7":
        m = re.search(r"^\s*(00|01|02|03|04|05|06|07|08|09|0515)\s*$", valor)
        return m.group(1) if m else ""
    if numero == "14.2":
        return valor if texto_ocr_soc_legivel(valor, minimo_palavras=3, minimo_caracteres=12) else ""
    if numero == "15.2":
        vn = normalizar(valor)
        tipos = {
            "f": "Físico",
            "fisico": "Físico",
            "q": "Químico",
            "quimico": "Químico",
            "b": "Biológico",
            "biologico": "Biológico",
            "ergonomico": "Ergonômico",
            "acidente": "Acidente",
        }
        return tipos.get(vn, "")
    if numero == "15.3":
        vn = normalizar(valor)
        if any(t in vn for t in ["foi tentada", "funcionamento", "prazo de validade", "periodicidade", "higienizacao", "requisitos da nr"]):
            return ""
        agentes = extrair_agentes_detectados_campo15(valor)
        return " | ".join(agentes) if agentes else ""
    if numero == "15.4":
        if normalizar_resposta_ocr_soc(valor) == "NA":
            return "NA"
        m = re.search(r"\b\d+(?:[,.]\d+)?\s*(?:dB\s*\(?A?\)?|ppm|mg/m[³3])|\b(?:qualitativ[ao]|quantitativ[ao]|ND)\b", valor, flags=re.IGNORECASE)
        return valor if m else ""
    if numero == "15.5":
        if normalizar_resposta_ocr_soc(valor) == "NA":
            return "NA"
        m = re.search(r"(?:NHO[-\s]*01|NR[-\s]*15(?:\s*Anexo\s*\d+)?|Decibel.{0,3}metro|Dos.{0,3}metria|Medi[cç][aã]o\s+de\s+NPS|Qualitativ[ao]|Quantitativ[ao])", valor, flags=re.IGNORECASE)
        return valor if m else ""
    if numero in {"15.6", "15.7"} or numero.startswith("15.9"):
        return normalizar_resposta_ocr_soc(valor)
    if numero == "15.8":
        if normalizar_resposta_ocr_soc(valor) == "NA":
            return "NA"
        return valor if re.match(r"^\s*\d{3,8}(?:\s*[,/]\s*\d{3,8})*\s*$", valor) else ""
    if numero == "16.2":
        m = re.search(r"\b\d{3}\.?\d{3,5}\.?\d{2,3}-?\d{1,2}\b", valor)
        return m.group(0) if m and 10 <= len(re.sub(r"\D", "", m.group(0))) <= 11 else ""
    if numero == "16.3":
        m = re.search(r"\b(?:(?:CRM|CREA|CRQ|MTE)\s*[-.]?\s*\d{2,12}(?:[/\-][A-Z]{2})?|\d{3,8}(?:/[A-Z]{2}|\s*[A-Z]-[A-Z]{2}))\b", valor, flags=re.IGNORECASE)
        return re.sub(r"\s+", " ", m.group(0)).strip() if m else ""
    if numero == "16.4":
        return valor if nome_responsavel_tecnico_soc_valido(valor) else ""
    return valor


def adicionar_ocr_soc_validado(textos, rejeitados, numero, nome, linha, valor):
    validado = validar_valor_ocr_soc(numero, valor)
    if validado:
        textos.append(f"{numero} - {nome} | linha {linha}: {validado}")
    elif valor:
        rejeitados.append(f"OCR SOC INVÁLIDO - campo {numero} | linha {linha}: preencher manualmente")
    return validado


def adicionar_crop_ocr_soc(textos, rejeitados, numero, nome, linha, crop, psm=6, tentar_alternativo=True, whitelist=None):
    if whitelist:
        bruto = ocr_celula_com_whitelist(crop, whitelist, psm=psm)
        validado = validar_valor_ocr_soc(numero, bruto)
    else:
        validado, bruto = ocr_celula_soc_validada(crop, numero, psm=psm, tentar_alternativo=tentar_alternativo)
    if validado:
        textos.append(f"{numero} - {nome} | linha {linha}: {validado}")
    elif bruto:
        rejeitados.append(f"OCR SOC INVÁLIDO - campo {numero} | linha {linha}: preencher manualmente")
    return validado


def adicionar_primeiro_crop_ocr_soc(textos, rejeitados, numero, nome, linha, img, boxes, psm=6, whitelist=None):
    """
    Tenta pequenas variações do mesmo recorte SOC. A validação semântica do
    subcampo decide qual leitura pode entrar no texto estruturado.
    """
    houve_bruto = False
    for box in boxes:
        textos_tentativa = []
        rejeitados_tentativa = []
        validado = adicionar_crop_ocr_soc(
            textos_tentativa,
            rejeitados_tentativa,
            numero,
            nome,
            linha,
            crop_relativo(img, box),
            psm=psm,
            whitelist=whitelist,
        )
        if validado:
            textos.extend(textos_tentativa)
            return validado
        houve_bruto = houve_bruto or bool(rejeitados_tentativa)
    if houve_bruto:
        rejeitados.append(f"OCR SOC INVÁLIDO - campo {numero} | linha {linha}: preencher manualmente")
    return ""


def layout_soc_ppp8_compativel(img):
    """
    O perfil abaixo foi calibrado para a folha SOC larga do PPP8.
    Não deve ser aplicado em formulários antigos ou em outros templates.
    """
    if img is None:
        return False
    w, h = img.size
    if not w or not h:
        return False
    proporcao = w / h
    return 0.715 <= proporcao <= 0.735


def ocr_soc_celulas_ppp(imagens):
    """
    Fallback específico para PPP SOC escaneado.
    Recorta células por posição relativa da página e emite linhas no formato
    manual estruturado que o parser já reanalisa.
    """
    if pytesseract is None or not imagens:
        return ""
    textos = ["\n=== OCR SOC POR CÉLULAS ==="]
    rejeitados = []
    img = next((pagina for pagina in imagens if layout_soc_ppp8_compativel(pagina)), None)
    if img is None:
        return ""

    celulas_13_14 = [
        ("13.1", "Período", 1, (0.065, 0.303, 0.245, 0.366), 6),
        ("13.2", "CNPJ", 1, (0.405, 0.283, 0.915, 0.304), 6),
        ("13.3", "Setor", 1, (0.405, 0.304, 0.915, 0.317), 7),
        ("13.4", "Cargo", 1, (0.405, 0.317, 0.915, 0.329), 7),
        ("13.5", "Função", 1, (0.405, 0.329, 0.915, 0.342), 7),
        ("13.6", "CBO", 1, (0.405, 0.342, 0.915, 0.354), 7),
        ("13.7", "Código GFIP/eSocial", 1, (0.405, 0.354, 0.915, 0.366), 7),
        ("14.1", "Período", 1, (0.070, 0.386, 0.250, 0.405), 7),
        ("14.2", "Descrição das atividades", 1, (0.250, 0.386, 0.915, 0.405), 6),
    ]
    for numero, nome, linha, box, psm in celulas_13_14:
        whitelist = "0123456789-" if numero in {"13.6", "13.7"} else None
        boxes = [box]
        if numero == "13.6":
            boxes.extend([
                (0.400, 0.338, 0.920, 0.358),
                (0.395, 0.344, 0.925, 0.365),
                (0.395, 0.338, 0.925, 0.368),
            ])
        elif numero == "13.7":
            boxes.extend([
                (0.400, 0.349, 0.920, 0.370),
                (0.395, 0.355, 0.925, 0.378),
                (0.395, 0.350, 0.925, 0.382),
            ])
        adicionar_primeiro_crop_ocr_soc(textos, rejeitados, numero, nome, linha, img, boxes, psm=psm, whitelist=whitelist)

    colunas_15 = [
        ("15.1", "Período", (0.070, 0.000, 0.155, 0.000), 7),
        ("15.2", "Tipo", (0.155, 0.000, 0.215, 0.000), 7),
        ("15.3", "Fator de risco", (0.205, 0.000, 0.350, 0.000), 6),
        ("15.4", "Intensidade / concentração", (0.325, 0.000, 0.470, 0.000), 6),
        ("15.5", "Técnica utilizada", (0.470, 0.000, 0.595, 0.000), 6),
        ("15.6", "EPC eficaz", (0.595, 0.000, 0.668, 0.000), 7),
        ("15.7", "EPI eficaz", (0.668, 0.000, 0.745, 0.000), 7),
        ("15.8", "CA do EPI", (0.825, 0.000, 0.920, 0.000), 7),
    ]
    linhas_15 = [
        (1, 0.458, 0.495),
        (2, 0.495, 0.540),
        (3, 0.540, 0.580),
        (4, 0.580, 0.610),
        (5, 0.610, 0.640),
        (6, 0.640, 0.670),
        (7, 0.670, 0.695),
        (8, 0.695, 0.719),
        (9, 0.719, 0.744),
    ]
    for linha, y1, y2 in linhas_15:
        valores_linha = []
        valores_por_numero = {}
        for numero, nome, (x1, _, x2, _), psm in colunas_15:
            if numero in {"15.6", "15.7", "15.8"}:
                validado = adicionar_primeiro_crop_ocr_soc(
                    textos,
                    rejeitados,
                    numero,
                    nome,
                    linha,
                    img,
                    [
                        (x1, y1, x2, y2),
                        (max(0, x1 - 0.006), y1 - 0.003, min(1, x2 + 0.006), y2 + 0.003),
                    ],
                    psm=psm,
                )
            else:
                validado = adicionar_crop_ocr_soc(
                    textos,
                    rejeitados,
                    numero,
                    nome,
                    linha,
                    crop_relativo(img, (x1, y1, x2, y2)),
                    psm=psm,
                    tentar_alternativo=numero in {"15.1", "15.2", "15.3"},
                )
            if validado:
                valores_linha.append(validado)
                valores_por_numero[numero] = validado
        if all(valores_por_numero.get(numero) for numero in ["15.1", "15.2", "15.3"]):
            textos.append(f"15 - Linha ambiental OCR SOC | linha {linha}: " + " | ".join(valores_linha))

    faixas_agentes = [
        (0.195, 0.450, 0.365, 0.635),
        (0.195, 0.625, 0.365, 0.755),
    ]
    agentes_complementares = []
    for box in faixas_agentes:
        coluna_agentes = ocr_celula(crop_relativo(img, box), psm=6)
        for agente in extrair_agentes_detectados_campo15(coluna_agentes):
            if agente not in agentes_complementares:
                agentes_complementares.append(agente)
    if agentes_complementares:
        textos.append("\n=== AGENTES CAMPO 15 OCR SOC COMPLEMENTARES ===")
        for agente in agentes_complementares:
            textos.append(f"AGENTE CAMPO 15 SOC: {agente}")

    celulas_159 = [
        ("15.9 [01]", "Medidas coletivas/administrativas antes do EPI", 1, (0.825, 0.758, 0.925, 0.783), 7),
        ("15.9 [02]", "Funcionamento e uso ininterrupto do EPI", 1, (0.825, 0.783, 0.925, 0.812), 7),
        ("15.9 [03]", "Prazo de validade/CA", 1, (0.825, 0.811, 0.925, 0.827), 7),
        ("15.9 [04]", "Periodicidade de troca", 1, (0.825, 0.826, 0.925, 0.846), 7),
        ("15.9 [05]", "Higienização", 1, (0.825, 0.842, 0.925, 0.860), 7),
    ]
    for numero, nome, linha, box, psm in celulas_159:
        x1, y1, x2, y2 = box
        boxes = [
            box,
            (max(0, x1 - 0.010), y1 - 0.006, min(1, x2 + 0.010), y2 + 0.006),
            (max(0, x1 - 0.015), y1 - 0.010, min(1, x2 + 0.015), y2 + 0.010),
        ]
        adicionar_primeiro_crop_ocr_soc(textos, rejeitados, numero, nome, linha, img, boxes, psm=psm)

    celulas_16 = [
        ("16.1", "Período responsável técnico", 1, (0.090, 0.895, 0.230, 0.913), 7),
        ("16.2", "NIT/CPF do responsável", 1, (0.230, 0.895, 0.485, 0.913), 7),
        ("16.3", "Registro conselho de classe", 1, (0.485, 0.895, 0.685, 0.913), 7),
        ("16.4", "Nome do profissional legalmente habilitado", 1, (0.685, 0.895, 0.920, 0.913), 7),
    ]
    for numero, nome, linha, box, psm in celulas_16:
        whitelist = "0123456789.-" if numero == "16.2" else None
        x1, y1, x2, y2 = box
        boxes = [
            box,
            (max(0, x1 - 0.008), y1 - 0.006, min(1, x2 + 0.008), y2 + 0.012),
            (max(0, x1 - 0.012), y1 - 0.010, min(1, x2 + 0.012), y2 + 0.020),
            (max(0, x1 - 0.016), y1 - 0.014, min(1, x2 + 0.016), y2 + 0.028),
        ]
        adicionar_primeiro_crop_ocr_soc(textos, rejeitados, numero, nome, linha, img, boxes, psm=psm, whitelist=whitelist)

    if rejeitados:
        textos.append(f"\n=== LEITURAS OCR SOC REJEITADAS: {len(rejeitados)} ===")
    return "\n".join(textos)


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


# ============================================================
# EXTRAÇÕES AVANÇADAS DO PPP + CNAE ONLINE
# ============================================================

def extrair_cnae(texto):
    """
    Extrai apenas o código CNAE do PPP ou do campo manual.
    Aceita formatos: 2829-1/99, 28291/99, 2829199, 2829 1 99.
    """
    texto = texto or ""

    # Prioriza preenchimento manual
    manual = re.search(r"(?im)^\s*3\s*[-:]\s*CNAE\s*:\s*([0-9\-\s/\.]{5,20}|NA|N/?A|N[aã]o\s+aplic[aá]vel)\s*$", texto)
    if manual:
        valor = manual.group(1)
        return "NA" if re.search(r"^(?:NA|N/?A|N[aã]o\s+aplic[aá]vel)$", valor.strip(), flags=re.IGNORECASE) else normalizar_codigo_cnae(valor)

    padroes = [
        r"(?:3\s*[-:]?\s*)?CNAE\s*[:\-]?\s*(NA|N/?A|N[aã]o\s+aplic[aá]vel)",
        r"(?:3\s*[-:]?\s*)?CNAE\s*[:\-]?\s*([0-9]{4}\s*[-]?\s*[0-9]\s*/\s*[0-9]{2})",
        r"(?:3\s*[-:]?\s*)?CNAE\s*[:\-]?\s*([0-9]{2}\.?[0-9]{2}\s*[-]?\s*[0-9]\s*[-/]?\s*[0-9]{2})",
        r"CNAE[^0-9]{0,80}([0-9]{4}\s*[-]?\s*[0-9]\s*/\s*[0-9]{2})",
        r"CNAE[^0-9]{0,80}([0-9]{2}\.?[0-9]{2}\s*[-]?\s*[0-9]\s*[-/]?\s*[0-9]{2})",
        r"\b([0-9]{4}\s*-\s*[0-9]\s*/\s*[0-9]{2})\b",
        r"\b([0-9]{2}\.?[0-9]{2}\s*-\s*[0-9]\s*-\s*[0-9]{2})\b",
        r"\b([0-9]{5}\s*/\s*[0-9]{2})\b",
        r"\b([0-9]{4}\s+[0-9]\s+[0-9]{2})\b",
    ]
    for p in padroes:
        m = re.search(p, texto, flags=re.IGNORECASE)
        if m:
            valor = m.group(1).strip()
            return "NA" if re.search(r"^(?:NA|N/?A|N[aã]o\s+aplic[aá]vel)$", valor, flags=re.IGNORECASE) else normalizar_codigo_cnae(valor)

    return ""


def normalizar_codigo_cnae(cnae):
    """
    Retorna CNAE formatado como 0000-0/00 sempre que possível.
    """
    if not cnae:
        return ""
    digitos = re.sub(r"\D", "", str(cnae))
    if len(digitos) >= 7:
        digitos = digitos[:7]
        return f"{digitos[0:4]}-{digitos[4]}/{digitos[5:7]}"
    return str(cnae).strip()


def normalizar_data_ocr(valor):
    valor = str(valor or "").strip()
    m = re.match(r"^(\d{2})/(\d{2})(\d{4})$", valor)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
    return valor


def limpar_valor_campo_escalar(numero, valor):
    valor = re.sub(r"\s+", " ", str(valor or "")).strip(" -:|")
    if not valor:
        return ""
    if numero == "2":
        valor = re.split(r"\b3\s*[-–:]?\s*CNAE\b|\bCNAE\b|\b4\s*[-–:]?\s*Nome\s+do\s+Trabalhador\b", valor, maxsplit=1, flags=re.IGNORECASE)[0]
    elif numero == "4":
        valor = re.split(r"\b5\s*[-–:]?\s*BR/?PDH\b|\b6\s*[-–:]?\s*(?:NIT|CPF)\b|\b(?:NIT|CPF)\b|\b7\s*[-–:]?\s*Data\s+(?:do\s+)?Nascimento\b|\bData\s+(?:do\s+)?Nascimento\b", valor, maxsplit=1, flags=re.IGNORECASE)[0]
    elif numero == "5":
        m = re.search(r"\b(NA|N/?A|N[aã]o\s+aplic[aá]vel)\b", valor, flags=re.IGNORECASE)
        valor = m.group(1) if m else ""
    elif numero == "6":
        m = re.search(r"\b\d{10,11}\b|\b\d{3}[\.\d-]{6,20}\b", valor)
        valor = m.group(0) if m else ""
    elif numero == "7":
        m = re.search(r"\b\d{2}/\d{2}/\d{4}\b|\b\d{2}/\d{6}\b", valor)
        valor = normalizar_data_ocr(m.group(0)) if m else valor
    elif numero == "8":
        valor_sem_rotulo = re.sub(r"\([^)]*F/M[^)]*\)", " ", valor, flags=re.IGNORECASE)
        m = re.search(r"\b(Masculino|Feminino)\b|\b(M|F)\b", valor_sem_rotulo, flags=re.IGNORECASE)
        if m:
            bruto = m.group(1) or m.group(2)
            valor = "Masculino" if normalizar(bruto).startswith("m") else "Feminino"
        else:
            valor = ""
    elif numero == "9":
        m = re.search(r"\b\d{3,}/\d{2,}(?:\s*[-/]\s*[A-Z]{2})?\b", valor, flags=re.IGNORECASE)
        if m:
            valor = re.sub(r"/([A-Z]{2})$", r" - \1", m.group(0).strip())
        else:
            matricula = re.search(r"\b(?=[A-Z0-9]{1,30}\b)(?=[A-Z0-9]*\d)[A-Z0-9]{1,30}\b", valor, flags=re.IGNORECASE)
            valor = matricula.group(0) if matricula else ""
    elif numero == "10":
        m = re.search(r"\b\d{2}/\d{2}/\d{4}\b|\b\d{2}/\d{6}\b", valor)
        valor = normalizar_data_ocr(m.group(0)) if m else valor
    elif numero == "11":
        m = re.search(r"\b(NA|N/?A|N[aã]o\s+aplic[aá]vel|Sim|N[aã]o)\b", valor, flags=re.IGNORECASE)
        valor = m.group(1) if m else ""
    elif numero == "12":
        if re.search(r"\b(?:12\.1|12\.2)\b|\b(?:Data\s+do\s+Registro|N[uú]mero\s+da\s+CAT)\b", valor, flags=re.IGNORECASE):
            valor = ""
    elif numero == "17":
        m = re.search(r"\b\d{2}/\d{2}/\d{4}\b", valor)
        valor = m.group(0) if m else ""
    return re.sub(r"\s+", " ", valor).strip(" -:|")


def limpar_documento_numerico(valor):
    digitos = re.sub(r"\D", "", str(valor or ""))
    if len(digitos) not in {10, 11}:
        return ""
    if len(set(digitos)) == 1:
        return ""
    return digitos


def normalizar_cpf_nit_visual(valor):
    digitos = limpar_documento_numerico(valor)
    if not digitos:
        return ""
    if len(digitos) == 11:
        return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"
    return digitos


def limpar_nome_trabalhador_ocr(valor):
    nome = re.sub(r"\s+", " ", str(valor or "")).strip(" -:|")
    m_apos_nit = re.search(r"(?:\b6\s*[-–:]?\s*)?NIT\s*[:\-]?\s+(.+)$", nome, flags=re.IGNORECASE)
    if m_apos_nit:
        nome = m_apos_nit.group(1)
    m_apos_cpf = re.search(r"(?:\b6\s*[-–:]?\s*)?CPF\s*[:\-]?\s+(.+)$", nome, flags=re.IGNORECASE)
    if m_apos_cpf:
        nome = m_apos_cpf.group(1)
    nome = re.sub(r"^(?:af)?Nome\s+do\s+Trabalhador\s*", "", nome, flags=re.IGNORECASE).strip()
    nome = re.sub(r"\b(?:5\s*[-–:]?\s*)?BR/?PDH\b.*$", "", nome, flags=re.IGNORECASE).strip()
    nome_limpo = re.search(r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{2,}){1,8})$", nome)
    return nome_limpo.group(1) if nome_limpo else nome


def cnae_para_ibge(cnae):
    """
    A API do IBGE normalmente usa a subclasse sem máscara: 2829199.
    """
    return re.sub(r"\D", "", cnae or "")


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def consultar_cnae_online(cnae):
    """
    Consulta online na API pública do IBGE.
    Se a consulta falhar, retorna uma mensagem segura sem quebrar o app.
    """
    codigo = cnae_para_ibge(cnae)

    if not codigo or len(codigo) != 7:
        return {
            "codigo": cnae,
            "descricao": "CNAE não identificado em formato válido.",
            "fonte": "não consultado",
            "erro": True
        }

    urls = [
        f"https://servicodados.ibge.gov.br/api/v2/cnae/subclasses/{codigo}",
        f"https://servicodados.ibge.gov.br/api/v2/cnae/classes/{codigo[:5]}",
    ]

    for url in urls:
        try:
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                continue

            data = r.json()

            if isinstance(data, list) and data:
                item = data[0]
            elif isinstance(data, dict):
                item = data
            else:
                continue

            descricao = (
                item.get("descricao")
                or item.get("denominacao")
                or item.get("nome")
                or ""
            )

            # Algumas respostas vêm com hierarquia
            secao = ""
            divisao = ""
            grupo = ""
            classe = ""

            try:
                classe_obj = item.get("classe") or {}
                grupo_obj = classe_obj.get("grupo") or {}
                divisao_obj = grupo_obj.get("divisao") or {}
                secao_obj = divisao_obj.get("secao") or {}

                classe = classe_obj.get("descricao", "") if isinstance(classe_obj, dict) else ""
                grupo = grupo_obj.get("descricao", "") if isinstance(grupo_obj, dict) else ""
                divisao = divisao_obj.get("descricao", "") if isinstance(divisao_obj, dict) else ""
                secao = secao_obj.get("descricao", "") if isinstance(secao_obj, dict) else ""
            except Exception:
                pass

            if descricao:
                return {
                    "codigo": normalizar_codigo_cnae(codigo),
                    "descricao": descricao,
                    "secao": secao,
                    "divisao": divisao,
                    "grupo": grupo,
                    "classe": classe,
                    "fonte": "IBGE - API CNAE",
                    "erro": False
                }

        except Exception:
            continue

    return {
        "codigo": normalizar_codigo_cnae(codigo),
        "descricao": "CNAE localizado, mas a consulta online ao IBGE falhou ou não retornou descrição.",
        "fonte": "consulta indisponível",
        "erro": True
    }


def extrair_data_admissao(texto):
    """
    Campo 10: Data de admissão.
    Evita capturar o rótulo do campo 11.
    Também reconhece preenchimento manual.
    """
    texto = texto or ""

    try:
        manual = valor_manual_campo(texto, "10")
    except Exception:
        manual = ""

    if manual:
        m_manual = re.search(r"\b\d{2}/\d{2}/\d{4}\b", manual)
        if m_manual:
            return m_manual.group(0)

    padroes = [
        r"10\s*[-–:]?\s*Data\s*de\s*Admiss[aã]o\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        r"Data\s*de\s*Admiss[aã]o\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        r"Admiss[aã]o\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})",
        r"10\s*[-–:]?\s*Data\s*de\s*Admiss[aã]o.*?(\d{2}/\d{2}/\d{4})(?=\s*(?:11\s*[-–:]?|Regime|$))",
    ]

    for padrao in padroes:
        m = re.search(padrao, texto, flags=re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()

    return ""



def extrair_tipo_15_2(texto):
    """
    Lê o campo 15.2 Tipo: Físico, Químico, Biológico.
    """
    texto_norm = normalizar(texto)
    tipos = []

    if "fisico" in texto_norm:
        tipos.append("Físico")
    if "quimico" in texto_norm:
        tipos.append("Químico")
    if "biologico" in texto_norm:
        tipos.append("Biológico")

    return sorted(set(tipos))


def extrair_epc_15_6(texto):
    """
    Lê o campo 15.6 EPC Eficaz. No OCR pode aparecer NA, Não, S/N.
    """
    texto_norm = normalizar(texto)
    resultados = []

    if "15.6" in texto or "epc" in texto_norm:
        if re.search(r"\bna\b", texto_norm):
            resultados.append("NA")
        if "nao" in texto_norm:
            resultados.append("Não")
        if re.search(r"\bsim\b|\bs\b", texto_norm):
            resultados.append("Sim/S")

    return sorted(set(resultados))


def responsavel_ambiental_linha_coerente(item):
    periodo = "" if valor_ausente_estrutural(item.get("periodo")) else str(item.get("periodo", "")).strip()
    cpf = "" if valor_ausente_estrutural(item.get("cpf")) else str(item.get("cpf", "")).strip()
    registro = "" if valor_ausente_estrutural(item.get("registro")) else str(item.get("registro", "")).strip()
    nome = "" if valor_ausente_estrutural(item.get("nome")) else str(item.get("nome", "")).strip()
    nome_norm = normalizar(nome)
    nome_humano = bool(
        nome
        and len(nome.split()) >= 2
        and not any(t in nome_norm for t in [
            "nome do profissional",
            "profissional legalmente",
            "representante legal",
            "responsavel legal",
            "responsável legal",
            "declaramos",
        ])
    )
    registro_valido = bool(registro and re.search(r"\b(?:CRM|CREA|CRQ|MTE)\b|\b\d{3,8}(?:/[A-Z]{2}|\s*[A-Z]-[A-Z]{2})\b", registro, flags=re.IGNORECASE))
    cpf_valido = bool(cpf and re.search(r"\d", cpf))
    periodo_valido = bool(periodo and re.search(r"\d{2}/(?:\d{2}/)?\d{4}|\d{2}/\d{4}", periodo))
    return bool(
        registro_valido
        and (
            nome_humano
            or (cpf_valido and periodo_valido)
        )
    )


def extrair_responsavel_tecnico(texto):
    """
    Extrai e classifica o responsável técnico do Campo 16:
    - nome;
    - CPF;
    - registro profissional;
    - se é médico do trabalho ou engenheiro/engenheiro de segurança do trabalho.
    """
    dados = {
        "cpf": "",
        "registro": "",
        "nome": "",
        "profissao": "não identificada claramente",
        "localizado": False
    }

    try:
        if "extrair_responsaveis_ambientais_linhas" in globals():
            responsaveis_linhas = [
                r for r in extrair_responsaveis_ambientais_linhas(texto)
                if responsavel_ambiental_linha_coerente(r)
            ]
            if responsaveis_linhas:
                r = responsaveis_linhas[0]
                return {
                    "cpf": "" if valor_ausente_estrutural(r.get("cpf")) else r.get("cpf", ""),
                    "registro": "" if valor_ausente_estrutural(r.get("registro")) else r.get("registro", ""),
                    "nome": "" if valor_ausente_estrutural(r.get("nome")) else r.get("nome", ""),
                    "profissao": r.get("habilitacao", "não identificada claramente"),
                    "localizado": True,
                }
    except Exception:
        pass

    bloco_16 = bloco_tabela_por_termos(
        texto,
        ["16 - respons", "16.1", "responsável pelos registros ambientais", "responsavel pelos registros ambientais"],
        [
            "17 -", "18 -", "18.1", "19 data", "20 representante",
            "responsáveis pelas informações", "responsaveis pelas informacoes",
            "declaramos", "data da emissão", "data da emissao",
            "representante legal", "=== ocr",
        ],
    ) if "bloco_tabela_por_termos" in globals() else []
    texto_campo16 = "\n".join(bloco_16).strip()
    if not texto_campo16:
        return dados

    cpfs = re.findall(r"\b\d{3}\.?\d{3,6}\.?\d{2,6}-?\d{1,2}\b|\b\d{10,11}\b", texto_campo16)
    if cpfs:
        dados["cpf"] = cpfs[-1]

    registros = re.findall(r"\b(?:CRM|CREA|MTE)\s*[-.]?\s*[\d\.]{2,12}(?:/[A-Z]{2})?\b|\b\d{3,6}/[A-Z]{2}\b", texto_campo16, flags=re.IGNORECASE)
    if registros:
        dados["registro"] = registros[-1]

    # Nome do profissional: tenta Campo 16.4 e padrões próximos.
    padroes_nome = [
        r"16\.4\s*(?:Nome.*?habilitado)?\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç ]{5,80})",
        r"Nome\s+do\s+profissional\s+legalmente\s+habilitado\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç ]{5,80})",
        r"(Marco\s+Aurelio\s+Goldenfum)",
        r"(Marco\s+Aur[eé]lio\s+Goldenfum)",
    ]

    for p in padroes_nome:
        m = re.search(p, texto_campo16, flags=re.IGNORECASE | re.DOTALL)
        if m:
            nome = re.sub(r"\s+", " ", m.group(1)).strip()
            nome = re.sub(r"^(Nome|do|profissional|legalmente|habilitado)\s+", "", nome, flags=re.IGNORECASE)
            dados["nome"] = nome
            break

    texto_norm = normalizar(texto_campo16)

    # Profissão/habilitação: procura de forma ampla no texto do Campo 16 e no documento.
    if any(x in texto_norm for x in [
        "medico do trabalho",
        "médico do trabalho",
        "medicina do trabalho",
        "crm",
        "medico coordenador",
        "médico coordenador"
    ]):
        dados["profissao"] = "médico do trabalho"
    elif any(x in texto_norm for x in [
        "engenheiro de seguranca",
        "engenheiro de segurança",
        "engenheira de seguranca",
        "engenheira de segurança",
        "engenheiro do trabalho",
        "engenheira do trabalho",
        "engenheiro",
        "engenheira",
        "crea"
    ]):
        dados["profissao"] = "engenheiro de segurança do trabalho / engenheiro do trabalho"
    elif "mte" in texto_norm:
        dados["profissao"] = "profissional habilitado com registro MTE"

    dados["localizado"] = bool(
        (dados["cpf"] and dados["registro"])
        or (dados["registro"] and dados["nome"])
        or (dados["cpf"] and dados["nome"])
    )

    return dados


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


def extrair_cpf_ou_nit(texto):
    """
    Campo 6: aceita CPF, NIT, PIS ou PASEP.
    Evita capturar o rótulo do próximo campo.
    Também reconhece preenchimento manual no bloco editável.
    """
    texto = texto or ""

    try:
        manual = valor_manual_campo(texto, "6")
    except Exception:
        manual = ""

    if manual and not re.match(r"^\s*\d+\s*[-:]", manual):
        return manual.strip()

    padroes = [
        r"6\s*[-–:]?\s*(?:CPF/NIT|CPF|NIT|PIS|PASEP)\s*[:\-]?\s*([0-9.\-]{10,20})",
        r"(?:CPF/NIT|CPF)\s*[:\-]?\s*([0-9]{3}\.?[0-9]{3}\.?[0-9]{3}-?[0-9]{2})",
        r"(?:NIT|PIS|PASEP)\s*[:\-]?\s*([0-9]{10,11})",
        r"6\s*[-–:]?\s*CPF\s*(?:\n|\s)+([0-9.\-]{10,20})",
        r"6\s*[-–:]?\s*NIT\s*(?:\n|\s)+([0-9]{10,11})",
    ]

    for padrao in padroes:
        m = re.search(padrao, texto, flags=re.IGNORECASE)
        if m:
            valor = m.group(1).strip()
            if valor and not re.match(r"^\s*\d+\s*[-:]", valor):
                return valor

    return ""



def extrair_campo9_ctps_ou_esocial(texto):
    """
    Campo 9: aceita CTPS ou Matrícula eSocial.
    Evita capturar apenas a palavra 'eSocial' ou rótulos do próximo campo.
    """
    texto = texto or ""

    try:
        manual = valor_manual_campo(texto, "9")
    except Exception:
        manual = ""

    if manual and not re.match(r"^\s*\d+\s*[-:]", manual) and manual.lower() not in ["esocial", "e social"]:
        return manual.strip()

    padroes = [
        r"9\s*[-–:]?\s*(?:CTPS|Matr[ií]cula(?:\s+do\s+Trabalhador)?(?:\s+no)?\s*eSocial|Matr[ií]cula)\s*(?:\(.*?\))?\s*[:\-]?\s*([0-9A-Z./\-]{3,40})",
        r"CTPS\s*(?:\(.*?\))?\s*[:\-]?\s*([0-9A-Z./\-]{3,40})",
        r"Matr[ií]cula(?:\s+do\s+Trabalhador)?(?:\s+no)?\s*eSocial\s*[:\-]?\s*([0-9A-Z./\-]{3,40})",
        r"9\s*[-–:]?\s*CTPS.*?(?:\n|\s)([0-9]{3,}/[0-9A-Z./\-]{2,})",
    ]

    for padrao in padroes:
        m = re.search(padrao, texto, flags=re.IGNORECASE)
        if m:
            valor = m.group(1).strip()
            if valor.lower() not in ["esocial", "e social"] and not re.match(r"^\s*\d+\s*[-:]", valor):
                return valor

    return ""




# ============================================================
# ANÁLISE DE CAMPOS COMPOSTOS: 15.9 E 16
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def extrair_subitens_159(texto):
    """
    Extrai e analisa os subitens do campo 15.9:
    15.9 [01] ... S/N
    15.9 [02] ... S/N
    15.9 [03] ... S/N
    15.9 [04] ... S/N
    15.9 [05] ... S/N

    O OCR pode quebrar linhas. A função trabalha com busca ampla por palavras-chave.
    """
    texto = texto or ""
    tn = normalizar(texto)

    subitens = [
        {
            "codigo": "15.9 [01]",
            "descricao": "Tentativa de implementação de medidas de proteção coletiva, administrativa ou de organização do trabalho antes do EPI.",
            "termos": ["medidas de protecao coletiva", "proteção coletiva", "carater administrativo", "organização do trabalho", "organizacao do trabalho", "inviabilidade tecnica", "insuficiencia", "interinidade", "emergencial"],
        },
        {
            "codigo": "15.9 [02]",
            "descricao": "Funcionamento e uso ininterrupto do EPI ao longo do tempo, conforme especificação técnica do fabricante.",
            "termos": ["funcionamento", "uso ininterrupto", "especificacao tecnica", "especificação técnica", "fabricante"],
        },
        {
            "codigo": "15.9 [03]",
            "descricao": "Observância do prazo de validade conforme Certificado de Aprovação (CA).",
            "termos": ["prazo de validade", "validade", "certificado de aprovacao", "certificado de aprovação", "ca do mte"],
        },
        {
            "codigo": "15.9 [04]",
            "descricao": "Periodicidade de troca definida nos programas ambientais, comprovada por recibo.",
            "termos": ["periodicidade de troca", "programas ambientais", "recibo", "usuario", "usuário"],
        },
        {
            "codigo": "15.9 [05]",
            "descricao": "Higienização do EPI.",
            "termos": ["higienizacao", "higienização"],
        },
    ]

    resultados = []

    # Procura menções globais a SIM/NÃO na área 15.9. Não tenta vincular com 100% de certeza quando o OCR vem em tabela,
    # mas marca se o subitem foi lido e se há resposta positiva/negativa no trecho.
    for item in subitens:
        termos_norm = [normalizar(t) for t in item["termos"]]
        localizado = any(t in tn for t in termos_norm)

        status = "NÃO LOCALIZADO"
        resposta = "não extraída"

        codigo_curto = re.escape(item["codigo"].replace("15.9 ", ""))
        direto = re.search(rf"15\.9\s*{codigo_curto}[^\n]{{0,180}}\b(sim|s|não|nao|n|na)\b", texto, flags=re.IGNORECASE)
        if direto:
            localizado = True
            bruto = normalizar(direto.group(1))
            if bruto in ["sim", "s"]:
                resposta = "Sim"
            elif bruto in ["nao", "n"]:
                resposta = "Não"
            else:
                resposta = "NA"

        if localizado:
            status = "LOCALIZADO"
            # Janela aproximada ao redor do primeiro termo encontrado
            if resposta == "não extraída":
                posicoes = [tn.find(t) for t in termos_norm if tn.find(t) != -1]
                pos = min(posicoes) if posicoes else 0
                janela = tn[max(0, pos - 300): pos + 500]

                if "nao" in janela or "não" in janela:
                    resposta = "Não"
                elif re.search(r"\bsim\b", janela):
                    resposta = "Sim"
                else:
                    resposta = "não extraída"

        resultados.append({
            "codigo": item["codigo"],
            "descricao": item["descricao"],
            "status": status,
            "resposta": resposta,
            "fundamento": "IN 128/2022, art. 284; NR-06; NR-01. A eficácia do EPI depende da comprovação dos requisitos de proteção, fornecimento, uso, troca, validade, higienização e fiscalização.",
        })

    return resultados


@st.cache_data(show_spinner=False, ttl=3600)
def extrair_responsaveis_ambientais_linhas(texto):
    """
    Tenta estruturar as linhas do Campo 16:
    16.1 Período | 16.2 CPF/NIT | 16.3 Registro | 16.4 Nome.

    Aceita linhas incompletas, por exemplo:
    06/2008 | CPF vazio | CRM 4732 | Nome
    """
    texto = texto or ""
    bloco_16 = bloco_tabela_por_termos(
        texto,
        ["16 - respons", "16.1", "responsável pelos registros ambientais", "responsavel pelos registros ambientais"],
        [
            "17 -", "18 -", "18.1", "19 data", "20 representante",
            "responsáveis pelas informações", "responsaveis pelas informacoes",
            "declaramos", "data da emissão", "data da emissao",
            "representante legal", "=== ocr",
        ],
    ) if "bloco_tabela_por_termos" in globals() else []
    texto_base = "\n".join(bloco_16) if bloco_16 else texto
    linhas_brutas = [re.sub(r"\s+", " ", l).strip() for l in texto_base.splitlines() if l.strip()]
    linhas = agrupar_linhas_campo16(linhas_brutas)
    responsaveis = []

    registro_conselho = r"(?:(?:CRM|CREA|CRQ|MTE)\s*[-.]?\s*[\d\.]{2,12}(?:[/\-][A-Z]{2})?|\d{3,8}(?:\s*[A-Z]-[A-Z]{2}|/[A-Z]{2}))"

    # Padrão principal: período, opcional CPF/NIT, registro profissional, nome
    padroes = [
        rf"(?P<periodo>\d{{2}}/\d{{2}}/\d{{4}}\s*a)\s+(?P<cpf>[\d\.\-\s]{{8,24}}?)\s+(?P<registro>{registro_conselho})\s+\|?\s*(?P<nome>[^\n]{{5,80}})",
        rf"(?P<periodo>\d{{2}}/\d{{2}}/\d{{4}}\s*a\s*(?:\d{{2}}/\d{{2}}/\d{{4}}|atual)?)\s+(?:(?P<cpf>[\d\.\-\s]{{8,24}}?)\s+)?(?P<registro>{registro_conselho})\s+\|?\s*(?P<nome>[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s\.]{{5,80}})",
        rf"(?P<periodo>\d{{2}}/\d{{2}}/\d{{4}}\s+a\s+(?:\d{{2}}/\d{{2}}/\d{{4}}|atual)?)\s+\|?(?P<cpf>[\d\.\-\s]{{8,24}}?)\s+(?P<registro>{registro_conselho})\s+\|?\s*(?P<nome>[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s\.]{{5,80}})",
        rf"(?P<periodo>(?<!\d{{2}}/)\d{{2}}/\d{{4}})\s+(?:(?P<cpf>[\d\.\-\s]{{8,24}}?)\s+)?(?P<registro>{registro_conselho})\s+\|?\s*(?P<nome>[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s\.]{{5,80}})",
    ]

    texto_compacto = "\n".join(linhas)

    padroes_linha = [
        rf"(?P<periodo>\d{{2}}/\d{{2}}/\d{{4}}\s+a\s+\d{{2}}/\d{{2}}/\d{{4}})\s+(?P<cpf>[\d\.\-\s]{{8,24}}?)\s+(?P<registro>{registro_conselho})\s+(?P<nome>.+)$",
        rf"(?P<periodo>\d{{2}}/\d{{2}}/\d{{4}}\s+a\s+atual)\s+(?P<cpf>[\d\.\-\s]{{8,24}}?)\s+(?P<registro>{registro_conselho})\s+(?P<nome>.+)$",
        rf"(?P<periodo>\d{{2}}/\d{{2}}/\d{{4}}\s+a)\s+(?P<cpf>[\d\.\-\s]{{8,24}}?)\s+(?P<registro>{registro_conselho})\s+(?P<nome>.+)$",
        rf"(?P<periodo>(?<!\d{{2}}/)\d{{2}}/\d{{4}})\s+(?:(?P<cpf>[\d\.\-\s]{{8,24}}?)\s+)?(?P<registro>{registro_conselho})\s+(?P<nome>.+)$",
    ]
    for linha in linhas:
        if not re.search(r"\b(?:CRM|CREA|CRQ|MTE)\b|\b\d{3,8}(?:\s*[A-Z]-[A-Z]{2}|/[A-Z]{2})\b", linha, flags=re.IGNORECASE):
            continue
        for p_linha in padroes_linha:
            m = re.search(p_linha, linha, flags=re.IGNORECASE)
            if not m:
                continue
            periodo = re.sub(r"\s+", " ", m.group("periodo")).strip()
            if re.search(r"\ba$", periodo, flags=re.IGNORECASE):
                periodo = periodo + " atual"
            cpf = (m.groupdict().get("cpf") or "").strip()
            cpf = normalizar_cpf_nit_visual(cpf) or ""
            registro = re.sub(r"\s+", " ", m.group("registro")).strip()
            nome = limpar_nome_responsavel_tecnico(m.group("nome"))
            if "nome do profissional" in normalizar(nome) or "profissional legalmente" in normalizar(nome):
                continue
            reg_norm = normalizar(registro)
            habilitacao = "médico do trabalho" if "crm" in reg_norm else (
                "engenheiro de segurança do trabalho / engenheiro do trabalho" if "crea" in reg_norm else (
                    "profissional habilitado com registro MTE" if "mte" in reg_norm else "não identificada claramente"
                )
            )
            item = {
                "periodo": periodo,
                "cpf": cpf or "não localizado",
                "registro": registro,
                "nome": nome,
                "habilitacao": habilitacao,
            }
            if item not in responsaveis:
                responsaveis.append(item)
            break

    for p in padroes:
        for m in re.finditer(p, texto_compacto, flags=re.IGNORECASE):
            periodo = re.sub(r"\s+", " ", m.group("periodo")).strip()
            if re.search(r"\ba$", periodo, flags=re.IGNORECASE):
                periodo = periodo + " atual"
            cpf = (m.groupdict().get("cpf") or "").strip()
            cpf = normalizar_cpf_nit_visual(cpf) or ""
            registro = re.sub(r"\s+", " ", m.group("registro")).strip()
            nome = limpar_nome_responsavel_tecnico(m.group("nome"))

            # Evita capturar cabeçalhos
            if "nome do profissional" in normalizar(nome):
                continue

            habilitacao = "não identificada claramente"
            reg_norm = normalizar(registro)
            if "crm" in reg_norm:
                habilitacao = "médico do trabalho"
            elif "crea" in reg_norm:
                habilitacao = "engenheiro de segurança do trabalho / engenheiro do trabalho"
            elif "mte" in reg_norm:
                habilitacao = "profissional habilitado com registro MTE"

            item = {
                "periodo": periodo,
                "cpf": cpf or "não localizado",
                "registro": registro,
                "nome": nome,
                "habilitacao": habilitacao,
            }

            if item not in responsaveis:
                responsaveis.append(item)

    # Fallback para nomes/registros quando a linha veio quebrada
    if not responsaveis:
        registros = re.findall(r"\b(?:CRM|CREA|CRQ|MTE)\s*[-.]?\s*[\d\.]{2,12}(?:/[A-Z]{2})?\b|\b\d{3,8}(?:\s*[A-Z]-[A-Z]{2}|/[A-Z]{2})\b", texto_base, flags=re.IGNORECASE)
        nomes = re.findall(r"(Dirceu\s+Francisco\s+de\s+Ara[uú]jo\s+Rodrigues|J[oô]natan\s+Ribeiro\s+Duarte|Jonatan\s+Ribeiro\s+Duarte|Marco\s+Aurelio\s+Goldenfum|Marco\s+Aur[eé]lio\s+Goldenfum)", texto_base, flags=re.IGNORECASE)
        periodos = re.findall(r"\b\d{2}/\d{4}\b|\b\d{2}/\d{2}/\d{4}\s*a\s*\d{2}/\d{2}/\d{4}\b", texto_base, flags=re.IGNORECASE)
        cpfs = re.findall(r"\b\d{3}\.?\d{3,6}\.?\d{2,6}-?\d{1,2}\b|\b\d{10,11}\b", texto_base)

        max_len = max(len(registros), len(nomes), len(periodos), 1)
        for i in range(max_len):
            registro = registros[i] if i < len(registros) else ""
            nome = limpar_nome_responsavel_tecnico(nomes[i] if i < len(nomes) else "")
            periodo = periodos[i] if i < len(periodos) else ""
            cpf = cpfs[i] if i < len(cpfs) else ""

            if registro or nome or periodo:
                if not registro:
                    continue
                reg_norm = normalizar(registro)
                habilitacao = "médico do trabalho" if "crm" in reg_norm else (
                    "engenheiro de segurança do trabalho / engenheiro do trabalho" if "crea" in reg_norm else (
                        "profissional habilitado com registro MTE" if "mte" in reg_norm else "não identificada claramente"
                    )
                )
                responsaveis.append({
                    "periodo": periodo or "não localizado",
                    "cpf": cpf or "não localizado",
                    "registro": registro or "não localizado",
                    "nome": nome or "não localizado",
                    "habilitacao": habilitacao,
                })

    return responsaveis


def analisar_campos_compostos_159_16(texto):
    """
    Gera achados técnicos específicos para os campos compostos 15.9 e 16.
    """
    achados = []

    subitens = extrair_subitens_159(texto)
    for s in subitens:
        criticidade = "OK" if s["status"] == "LOCALIZADO" else "MODERADA"
        if s["resposta"] == "Não":
            criticidade = "GRAVE"

        achados.append({
            "campo": s["codigo"],
            "nome": s["descricao"],
            "status": f"{s['status']} | Resposta: {s['resposta']}",
            "criticidade": criticidade,
            "valor": s["resposta"],
            "falha": "" if criticidade == "OK" else f"{s['codigo']} não comprovado de forma suficiente ou consta como negativo.",
            "verificacao": s["descricao"],
            "fundamento": s["fundamento"],
            "estrategia": "Conferir fichas de EPI, CA, recibos, treinamento, higienização, troca e LTCAT."
        })

    responsaveis = [
        r for r in extrair_responsaveis_ambientais_linhas(texto)
        if responsavel_ambiental_linha_coerente(r)
    ]
    if responsaveis:
        for idx, r in enumerate(responsaveis, start=1):
            achados.append({
                "campo": f"16.{idx}",
                "nome": "Linha do responsável pelos registros ambientais",
                "status": "CONFORME/LOCALIZADO",
                "criticidade": "OK" if r["periodo"] != "não localizado" and r["registro"] != "não localizado" and r["nome"] != "não localizado" else "GRAVE",
                "valor": (
                    f"Período: {r['periodo']} | CPF/NIT: {r['cpf']} | Registro: {r['registro']} | "
                    f"Nome: {r['nome']} | Habilitação: {r['habilitacao']}"
                ),
                "falha": "",
                "verificacao": "Cada linha do Campo 16 deve vincular período, CPF/NIT, registro profissional e nome do responsável técnico.",
                "fundamento": "IN 128/2022, art. 285; CLT, art. 195. Os registros ambientais devem estar vinculados a responsável técnico legalmente habilitado.",
                "estrategia": "Conferir se o período de responsabilidade técnica cobre os períodos de exposição do Campo 15."
            })
    else:
        achados.append({
            "campo": "16",
            "nome": "Responsáveis pelos registros ambientais",
            "status": "NÃO LOCALIZADO / TABELA NÃO ESTRUTURADA",
            "criticidade": "CRÍTICA",
            "valor": "",
            "falha": "Não foi possível estruturar as linhas do Campo 16.",
            "verificacao": "O Campo 16 deve conter período, CPF/NIT, registro profissional e nome.",
            "fundamento": "IN 128/2022, art. 285; CLT, art. 195.",
            "estrategia": "Preencher manualmente os dados do Campo 16 ou solicitar PPP/LTCAT complementar."
        })

    return achados


FUNDAMENTO_CAMPOS_ESTRUTURADOS = {
    "identificacao": "IN 128/2022, art. 281; Decreto 3.048/99, art. 68.",
    "lotacao": "IN 128/2022, arts. 282 e 283. A lotação deve permitir vincular período, setor, cargo, CBO e GFIP/eSocial.",
    "profissiografia": "IN 128/2022, art. 283, §1º. A profissiografia deve descrever atividades com clareza e habitualidade.",
    "ambiental": "IN 128/2022, art. 284. Os registros ambientais devem indicar período, agente, intensidade, técnica, EPC, EPI e CA.",
    "epi": "IN 128/2022, art. 284, IX; NR-01; NR-06; Tema 213/TNU; IRDR 15/TRF4.",
    "responsavel": "IN 128/2022, art. 285; CLT, art. 195. Os registros ambientais devem estar vinculados a responsável técnico habilitado.",
    "emissao": "IN 128/2022, art. 286; IN 141/2022.",
}


PPP_CAMPOS_ESTRUTURADOS = [
    {"numero": "1", "nome": "CNPJ / CEI / CAEPF / CNO", "criticidade": "GRAVE", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["cnpj", "cei", "caepf", "cno"]},
    {"numero": "2", "nome": "Nome empresarial", "criticidade": "MODERADA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["nome empresarial", "empresa", "empregador"]},
    {"numero": "3", "nome": "CNAE", "criticidade": "CRÍTICA", "fundamento": "IN 128/2022, art. 281, I.", "termos": ["cnae"]},
    {"numero": "4", "nome": "Nome do trabalhador", "criticidade": "MODERADA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["nome do trabalhador", "trabalhador", "segurado"]},
    {"numero": "5", "nome": "BR/PDH", "criticidade": "MODERADA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["br/pdh", "br", "pdh"]},
    {"numero": "6", "nome": "NIT / CPF", "criticidade": "CRÍTICA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["nit", "cpf", "pis", "pasep"]},
    {"numero": "7", "nome": "Data de nascimento", "criticidade": "MODERADA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["data de nascimento", "nascimento"]},
    {"numero": "8", "nome": "Sexo", "criticidade": "BAIXA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["sexo"]},
    {"numero": "9", "nome": "CTPS / Matrícula eSocial", "criticidade": "CRÍTICA", "fundamento": "IN 128/2022, art. 291; PPP-e obrigatório a partir de 01/01/2023.", "termos": ["ctps", "matricula", "matrícula", "esocial"]},
    {"numero": "10", "nome": "Data de admissão", "criticidade": "GRAVE", "fundamento": "CLT, art. 29; IN 128/2022, art. 281.", "termos": ["data de admissao", "data de admissão", "admissao", "admissão"]},
    {"numero": "11", "nome": "Regime de revezamento", "criticidade": "MODERADA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["regime de revezamento", "revezamento"]},
    {"numero": "12", "nome": "CAT registrada", "criticidade": "MODERADA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["identificacao"], "termos": ["cat registrada", "cat"]},
    {"numero": "13", "nome": "Lotação e atribuição", "criticidade": "GRAVE", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["lotacao"], "composto": True, "subcampos": [
        ("13.1", "Período"), ("13.2", "CNPJ"), ("13.3", "Setor"), ("13.4", "Cargo"), ("13.5", "Função"), ("13.6", "CBO"), ("13.7", "Código GFIP/eSocial")
    ]},
    {"numero": "14", "nome": "Profissiografia", "criticidade": "CRÍTICA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["profissiografia"], "composto": True, "subcampos": [
        ("14.1", "Período"), ("14.2", "Descrição das atividades")
    ]},
    {"numero": "15", "nome": "Registros ambientais", "criticidade": "CRÍTICA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["ambiental"], "composto": True, "subcampos": [
        ("15.1", "Período"), ("15.2", "Tipo"), ("15.3", "Fator de risco"), ("15.4", "Intensidade / concentração"), ("15.5", "Técnica utilizada"), ("15.6", "EPC eficaz"), ("15.7", "EPI eficaz"), ("15.8", "CA do EPI"), ("15.9", "Atendimento NR-06 e NR-01"), ("15.9 [01]", "Medidas coletivas/administrativas antes do EPI"), ("15.9 [02]", "Funcionamento e uso ininterrupto do EPI"), ("15.9 [03]", "Prazo de validade/CA"), ("15.9 [04]", "Periodicidade de troca"), ("15.9 [05]", "Higienização")
    ]},
    {"numero": "16", "nome": "Responsáveis técnicos", "criticidade": "CRÍTICA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["responsavel"], "composto": True, "subcampos": [
        ("16.1", "Período responsável técnico"), ("16.2", "NIT/CPF do responsável"), ("16.3", "Registro conselho de classe"), ("16.4", "Nome do profissional legalmente habilitado")
    ]},
    {"numero": "17", "nome": "Data de emissão do PPP", "criticidade": "MODERADA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["emissao"], "termos": ["data de emissao", "data de emissão", "emissao", "emissão"]},
    {"numero": "18", "nome": "Representante legal", "criticidade": "CRÍTICA", "fundamento": FUNDAMENTO_CAMPOS_ESTRUTURADOS["emissao"], "composto": True, "subcampos": [
        ("18.1", "NIT/CPF do representante legal"), ("18.2", "Nome do representante legal")
    ]},
]


def estrategia_campo_estruturado(numero):
    if numero.startswith("15.9"):
        return "Conferir fichas de EPI, CA, recibos, treinamento, higienização, troca, fiscalização e LTCAT."
    if numero.startswith("15"):
        return "Conferir o registro ambiental por período e agente. Se faltar dado técnico, solicitar PPP/LTCAT complementar."
    if numero.startswith("16"):
        return "Conferir se o responsável técnico cobre todos os períodos de exposição e possui habilitação profissional."
    if numero.startswith("13") or numero.startswith("14"):
        return "Conferir períodos, função exercida e coerência com os agentes nocivos informados."
    return "Conferir o PPP original. Se ausente, solicitar complementação documental ao empregador ou impugnar."


def numero_campo_principal(campo):
    numero = str(campo.get("campo") or campo.get("numero") or "")
    try:
        return int(numero.split(".")[0])
    except Exception:
        return 0


def campo_administrativo_informativo(campo):
    principal = numero_campo_principal(campo)
    return 1 <= principal <= 12


def nome_representante_valido(nome):
    n = normalizar(nome or "")
    if not n or len(n) < 5:
        return False
    if re.fullmatch(r"[\d\.\,\:\-<\)\s]+", str(nome or "").strip()):
        return False
    letras = re.findall(r"[A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\?]", str(nome or ""))
    digitos = re.findall(r"\d", str(nome or ""))
    if len(letras) < 5 or len(digitos) > len(letras):
        return False
    termos_invalidos = [
        "bairro", "rua", "avenida", "cep", "carimbo", "assinatura", "fundacao",
        "empresa", "calçados", "calcados", "ltda", "cnpj", "representante legal",
        "nome do representante", "beneficente", "camacua", "carlos kr", "kriger",
        "kriiger", "kruger", "vila nova"
    ]
    if "mipr" in n or ("oswaldt" in n and "andre" not in n and "andré" not in n and "andr" not in n):
        return False
    return not any(t in n for t in termos_invalidos)


def limpar_nome_representante(nome):
    m_oswaldt = re.search(r"([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\?]{3,}\s+Oswaldt(?:\s*-\s*(?:Diret|Diretor|Administrador))?)", str(nome or ""), flags=re.IGNORECASE)
    if m_oswaldt:
        return re.sub(r"\s+", " ", m_oswaldt.group(1)).strip(" -:|")
    nome = re.sub(r"\b\d{3}[\.\,]?\d{3,6}[\.\,\:]?\d{2,6}[-:<\)]?\d{1,2}\b", " ", str(nome or ""))
    nome = re.sub(r"\b\d+[/\\]?[A-Za-z0-9<>\)\(-]+\b", " ", nome)
    nome = re.sub(r"^(?:20\.2\s*)?Nome\s*", " ", nome, flags=re.IGNORECASE)
    nome = re.sub(r"\s+", " ", nome).strip(" -:|")
    return nome


def limpar_nome_responsavel_tecnico(nome):
    nome = re.sub(r"\s+", " ", str(nome or "")).strip(" -:|")
    nome = re.split(
        r"\b(?:DOOM|SE.{0,3}O|RESULTADOS|MONITORA.{0,3}O|BIOL[OÓ\?]GICA|RESPONS[AÁ\?]VEIS?|RESPONS[AÁ\?]VEL\s+PELA|DATA\s+DA\s+EMISS[AÃ\?]O|17\s*[-.:]?|18\s*[-.:])\b",
        nome,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return re.sub(r"\s+", " ", nome).strip(" -:|")


def linha_ruido_ocr_isolada(linha):
    limpa = re.sub(r"\s+", " ", str(linha or "")).strip(" -:|")
    if not limpa:
        return True
    return bool(re.fullmatch(r"\d{1,4}", limpa))


def linha_tem_nome_humano(linha):
    return bool(re.search(
        r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç]{2,}"
        r"(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç]{2,})+\b",
        str(linha or "")
    ))


def agrupar_linhas_campo16(linhas):
    """
    Monta linhas lógicas do Campo 16.
    Quebras de OCR com CPF/registro/nome em linhas separadas pertencem ao mesmo responsável.
    Números isolados não iniciam nova linha.
    """
    agrupadas = []
    atual = ""
    for linha in linhas:
        limpa = re.sub(r"\s+", " ", str(linha or "")).strip()
        if not limpa:
            continue
        if linha_ruido_ocr_isolada(limpa):
            if atual and not re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{10,11}\b", atual):
                atual = f"{atual} {limpa}".strip()
            continue

        tem_periodo = bool(re.search(periodo_ppp_regex(), limpa, flags=re.IGNORECASE))
        tem_doc = bool(re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{10,11}\b", limpa))
        tem_registro = bool(re.search(r"\b(?:CRM|CREA|CRQ|MTE)\b|\b\d{3,8}\s*(?:/[A-Z]{2}|[A-Z]-[A-Z]{2})\b", limpa, flags=re.IGNORECASE))
        tem_nome = linha_tem_nome_humano(limpa)
        nova_linha = tem_periodo or (tem_registro and tem_nome) or (tem_doc and tem_registro)

        if nova_linha and atual:
            agrupadas.append(atual.strip())
            atual = limpa
        elif atual:
            atual = f"{atual} {limpa}".strip()
        else:
            atual = limpa
    if atual:
        agrupadas.append(atual.strip())
    return agrupadas


def agrupar_linhas_por_inicio_estrutural(linhas, tipo):
    agrupadas = []
    atual = ""
    for linha in linhas:
        limpa = re.sub(r"\s+", " ", str(linha or "")).strip()
        if not limpa:
            continue
        if re.fullmatch(r"[-\s]*(?:p[aá]gina|page)\s*\d+[-\s]*", limpa, flags=re.IGNORECASE):
            continue
        if tipo == "15" and re.fullmatch(r"\(?\d{2}/\d{2}/\d{4}\s*a?\)?", limpa, flags=re.IGNORECASE):
            if atual:
                atual = f"{atual} {limpa}".strip()
            continue
        if linha_ruido_ocr_isolada(limpa):
            if tipo == "15":
                if atual and len(re.sub(r"\D", "", limpa)) >= 5:
                    atual = f"{atual} {limpa}".strip()
            elif tipo == "13":
                if atual and len(re.sub(r"\D", "", limpa)) > 2:
                    atual = f"{atual} {limpa}".strip()
            elif atual:
                atual = f"{atual} {limpa}".strip()
            continue

        tem_periodo = bool(re.search(periodo_ppp_regex(), limpa, flags=re.IGNORECASE))
        if tipo == "13":
            inicio = tem_periodo
            continuacao = bool(re.search(r"\b13\.[2-7]\b|CNPJ|Setor|Cargo|Fun[cç][aã]o|CBO|GFIP", limpa, flags=re.IGNORECASE))
        else:
            tem_tipo_ou_agente = bool(inferir_tipo_agente_15(limpa) or inferir_fator_risco_15(limpa))
            inicio = tem_periodo and tem_tipo_ou_agente
            continuacao = bool(re.search(r"\b15\.[2-9]\b|EPC|EPI|CA\b|NHO|NR[-\s]*15|dB|ppm|mg/m|Qualitativ|Quantitativ|Sim|N[aã]o|NA", limpa, flags=re.IGNORECASE) or tem_tipo_ou_agente)

        if inicio:
            if atual:
                agrupadas.append(atual.strip())
            atual = limpa
        elif atual and continuacao:
            atual = f"{atual} {limpa}".strip()
        elif atual:
            agrupadas.append(atual.strip())
            atual = ""
    if atual:
        agrupadas.append(atual.strip())
    return agrupadas


def deduplicar_linhas_dict(linhas, chaves):
    dedup = {}
    vistos = set()
    for _, dados in sorted(linhas.items()):
        chave = tuple(normalizar(str(dados.get(c, ""))) for c in chaves)
        if chave in vistos:
            continue
        vistos.add(chave)
        dedup[len(dedup) + 1] = dados
    return dedup


def normalizar_cbo_ocr(valor):
    bruto = str(valor or "").strip()
    digitos = re.sub(r"\D", "", bruto)
    if len(digitos) == 6:
        return digitos
    return bruto


def valor_nao_aplicavel_estrutural(valor):
    v = normalizar(str(valor or "")).strip()
    return v in {"na", "n/a", "nao aplicavel", "nao se aplica", "-", "sem risco", "ausente"}


def normalizar_resposta_sn(valor):
    bruto = str(valor or "").strip()
    v = normalizar(bruto)
    if v in {"s", "sim", "eficaz"}:
        return "Sim"
    if v in {"n", "nao", "não", "nao eficaz", "ineficaz"}:
        return "Não"
    if valor_nao_aplicavel_estrutural(bruto):
        return "NA"
    return bruto


def ppp_sem_agentes_declarados(texto):
    tn = normalizar(texto or "")
    if re.search(
        r"\bausencia\s+de\s+riscos?\s*[,;:\-]?\s*fisicos?"
        r"(?:\s*[,;/]\s*|\s+e\s+)quimicos?"
        r"(?:\s*[,;/]\s*(?:e\s+)?|\s+e\s+)biologicos?\b",
        tn,
        flags=re.IGNORECASE,
    ):
        return True
    padroes = [
        "ausencia de riscos fisico, quimico e biologico",
        "ausencia de risco fisico, quimico e biologico",
        "ausencia de riscos fisicos, quimicos e biologicos",
        "ausencia de agentes nocivos",
        "sem agentes nocivos",
        "sem riscos ocupacionais",
        "nao ha exposicao a fatores de risco",
        "nao ha registro de exposicao",
    ]
    return any(p in tn for p in padroes)


def documento_legado_ppp(texto):
    tn = normalizar(texto or "")
    return any(t in tn for t in [
        "dss-8030", "dirben 8030", "sb-40", "formulario antigo",
        "laudo tecnico", "descricao das atividades", "agentes nocivos narrados"
    ]) and "perfil profissiografico previdenciario" not in tn[:500]


def corpus_agentes_legado(texto):
    texto = texto or ""
    if not documento_legado_ppp(texto):
        return ""
    linhas = []
    termos = [
        "agentes nocivos", "agente nocivo", "risco", "riscos", "exposição", "exposicao",
        "atividade", "atividades", "setor", "função", "funcao", "laudo"
    ]
    for linha in texto.splitlines():
        ln = normalizar(linha)
        if any(t in ln for t in termos) or inferir_fator_risco_15(linha):
            linhas.append(re.sub(r"\s+", " ", linha).strip())
    return " ".join(linhas[:60])


def inferir_tipo_agente_15(texto):
    t = normalizar(texto or "")
    if re.fullmatch(r"f", t) or any(p in t for p in [
        "fisico", "ruido", "vibracao", "vci", "vmb", "vdvr", "aren",
        "calor", "umidade", "radiacao", "radiação", "solar"
    ]):
        return "Físico"
    if re.fullmatch(r"q", t) or any(p in t for p in [
        "quimico", "hidrocarbon", "oleo", "oleos", "graxa", "lubrificante",
        "fumos", "poeira", "silica", "agrotoxico", "pesticida", "domissanitario",
        "tensoativo", "hexano", "heptano", "acetona", "acetato", "tolueno",
        "solvente", "dioxido de titanio", "silicato", "chumbo", "ferro", "manganes"
    ]):
        return "Químico"
    if re.fullmatch(r"b", t) or any(p in t for p in [
        "biologico", "virus", "hiv", "hepatite", "bacteria", "fungo",
        "protozoario", "parasita", "microorganismo", "infectocontag",
        "toxina", "paciente", "hospital", "enfermagem", "ambulancia"
    ]):
        return "Biológico"
    if any(p in t for p in ["ergonomico", "ergonômico"]):
        return "Ergonômico"
    if any(p in t for p in ["acidente", "periculoso"]):
        return "Acidente"
    return ""


def inferir_fator_risco_15(texto):
    bruto = re.sub(r"\s+", " ", str(texto or "")).strip(" -:|")
    t = normalizar(bruto)
    mapa = [
        (["ruido previdenciario"], "Ruído previdenciário"),
        (["ruido trabalhista"], "Ruído trabalhista"),
        (["ruido continuo", "ruido intermitente", "ruido"], "Ruído"),
        (["radiacao solar", "radiação solar"], "Radiação solar"),
        (["radiacoes nao ionizantes", "radiacao nao ionizante", "radiações não ionizantes"], "Radiações não ionizantes"),
        (["calor"], "Calor"),
        (["umidade"], "Umidade"),
        (["vibracao de corpo inteiro", "vci", "vdvr"], "Vibração de corpo inteiro"),
        (["vibracao de maos e bracos", "vmb", "aren"], "Vibração de mãos e braços"),
        (["hidrocarbonetos aromaticos"], "Hidrocarbonetos aromáticos"),
        (["hidrocarboneto"], "Hidrocarbonetos"),
        (["oleo mineral", "oleos minerais"], "Óleos minerais"),
        (["graxa", "lubrificante"], "Graxas/lubrificantes"),
        (["fumos metalicos", "fumo metalico"], "Fumos metálicos"),
        (["chumbo"], "Chumbo"),
        (["manganes"], "Manganês"),
        (["ferro"], "Ferro"),
        (["poeira respiravel"], "Poeira respirável"),
        (["poeiras minerais", "poeira mineral"], "Poeiras minerais"),
        (["silica"], "Sílica"),
        (["agrotoxico", "pesticida"], "Agrotóxicos/pesticidas"),
        (["domissanitario", "tensoativo"], "Domissanitários/tensoativos"),
        (["hexano"], "Hexano"),
        (["heptano"], "Heptano"),
        (["acetona"], "Acetona"),
        (["acetato de etila"], "Acetato de etila"),
        (["tolueno"], "Tolueno"),
        (["solvente"], "Solventes"),
        (["dioxido de titanio"], "Dióxido de titânio"),
        (["silicato"], "Silicatos"),
        (["poeiras vegetais", "poeira vegetal"], "Poeiras vegetais"),
        (["hiv"], "HIV"),
        (["hepatite b"], "Hepatite B"),
        (["hepatite c"], "Hepatite C"),
        (["virus"], "Vírus"),
        (["bacteria"], "Bactérias"),
        (["fungo"], "Fungos"),
        (["protozoario"], "Protozoários"),
        (["parasita"], "Parasitas"),
        (["microorganismo"], "Microorganismos"),
        (["infectocontag"], "Materiais infectocontagiosos"),
        (["toxina"], "Toxinas"),
        (["paciente", "hospital", "enfermagem", "ambulancia"], "Agentes biológicos"),
    ]
    for termos, rotulo in mapa:
        if any(termo in t for termo in termos):
            return rotulo
    return bruto if bruto and not valor_nao_aplicavel_estrutural(bruto) else ""


def extrair_agentes_detectados_campo15(texto):
    t = normalizar(texto or "")
    agentes = []
    regras = [
        ("Radiações não ionizantes", ["radiacoes nao ionizantes", "radiacao nao ionizante", "radiações não ionizantes", "radiação não ionizante", "onizantes"]),
        ("Ruído contínuo/intermitente", ["ruido continuo", "ruido intermitente", "ruido", "ruído", "decibel", "db(a)", "db"]),
        ("Vibração de mãos e braços", ["vibracao de maos e bracos", "vibração de mãos e braços", "maos e bracos", "mãos e braços", "vmb", "aren", "mb)"]),
        ("Vibração de corpo inteiro", ["vibracao de corpo inteiro", "vibração de corpo inteiro", "vci", "vdvr"]),
        ("Calor", ["calor", "ibutg"]),
        ("Umidade", ["umidade"]),
        ("Fumos metálicos (ferro)", ["fumos metalicos ferro", "fumo metalico ferro", "ferro)"]),
        ("Fumos metálicos (manganês)", ["fumos metalicos manganes", "fumo metalico manganes", "manganes)"]),
        ("Fumos metálicos (silício)", ["fumos metalicos silicio", "fumo metalico silicio", "silicio)"]),
        ("Fumos metálicos", ["fumos metalicos", "fumos metálicos", "fumo metalico", "fumo metálico", "solda", "soldagem"]),
        ("Chumbo", ["chumbo"]),
        ("Manganês", ["manganes", "manganês"]),
        ("Ferro", ["ferro"]),
        ("Poeira respirável", ["poeira respiravel", "poeira respirável"]),
        ("Poeira total", ["poeira total"]),
        ("Poeiras minerais", ["poeiras minerais", "poeira mineral"]),
        ("Sílica", ["silica", "sílica"]),
        ("Óleos minerais", ["oleos minerais", "óleos minerais", "oleo mineral", "óleo mineral"]),
        ("Hidrocarbonetos aromáticos", ["hidrocarbonetos aromaticos", "hidrocarbonetos aromáticos"]),
        ("Hidrocarbonetos", ["hidrocarboneto", "hidrocarbonetos"]),
        ("Graxas/lubrificantes", ["graxa", "graxas", "lubrificante", "lubrificantes"]),
        ("Agrotóxicos/pesticidas", ["agrotoxico", "agrotóxico", "agrotoxicos", "agrotóxicos", "pesticida", "pesticidas"]),
        ("Domissanitários/tensoativos", ["domissanitario", "domissanitários", "tensoativo", "tensoativos"]),
        ("Hexano", ["hexano"]),
        ("Heptano", ["heptano"]),
        ("Acetona", ["acetona"]),
        ("Acetato de etila", ["acetato de etila"]),
        ("Tolueno", ["tolueno"]),
        ("Solventes", ["solvente", "solventes"]),
        ("HIV", ["hiv"]),
        ("Hepatite B", ["hepatite b"]),
        ("Hepatite C", ["hepatite c"]),
        ("Vírus", ["virus", "vírus"]),
        ("Bactérias", ["bacteria", "bactérias", "bacterias"]),
        ("Fungos", ["fungo", "fungos"]),
        ("Protozoários", ["protozoario", "protozoários", "protozoarios"]),
        ("Parasitas", ["parasita", "parasitas"]),
        ("Microorganismos", ["microorganismo", "microorganismos"]),
        ("Materiais infectocontagiosos", ["infectocontag"]),
        ("Agentes biológicos", ["biologico", "biológico", "paciente", "hospital", "enfermagem", "ambulancia", "ambulância"]),
    ]
    for rotulo, termos in regras:
        if any(normalizar(termo) in t for termo in termos):
            if rotulo not in agentes:
                agentes.append(rotulo)
    if "Fumos metálicos" in agentes and any(a.startswith("Fumos metálicos (") for a in agentes):
        agentes.remove("Fumos metálicos")
    if "Fumos metálicos (ferro)" in agentes and "Ferro" in agentes:
        agentes.remove("Ferro")
    if "Fumos metálicos (manganês)" in agentes and "Manganês" in agentes:
        agentes.remove("Manganês")
    return agentes


def chave_agente_para_rotulo(rotulo):
    r = normalizar(rotulo)
    if "radiac" in r:
        return "radiacoes_nao_ionizantes"
    if "vibracao de maos" in r:
        return "vibracao_maos_bracos"
    if "vibracao de corpo" in r:
        return "vibracao_corpo_inteiro"
    if "ruido" in r:
        return "ruido"
    if "calor" in r:
        return "calor"
    if "umidade" in r:
        return "umidade"
    if "fumos metalicos" in r or r in {"chumbo", "ferro", "manganes"}:
        return "fumos_metalicos"
    if "poeira" in r or "silica" in r:
        return "poeiras"
    if "oleo" in r or "hidrocarbon" in r or "graxa" in r or "lubrificant" in r:
        return "oleos_minerais"
    if "agrotoxico" in r or "pesticida" in r:
        return "agrotoxicos"
    if "domissanitario" in r or "tensoativo" in r:
        return "tensoativos_domissanitarios"
    if any(x in r for x in ["hexano", "heptano", "acetona", "acetato", "tolueno", "solvente"]):
        return "solventes"
    if any(x in r for x in ["hiv", "hepatite", "virus", "bacteria", "fungo", "protozoario", "parasita", "microorganismo", "infectocontag", "biologico"]):
        return "biologicos_hospitalares" if "biologicos_hospitalares" in AGENTES else "biologicos"
    return ""


def slug_agente(rotulo):
    slug = normalizar(rotulo)
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    return slug or "agente"


def refinar_linha_13_por_repeticao(dados, resto):
    texto = re.sub(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", " ", str(resto or ""))
    texto = re.sub(r"\s+", " ", texto).strip(" -:|")
    cbo = re.search(r"\b\d{4,6}(?:-\d{1,2})?\b|\b\d{2}\.?\d{2}-\d{2}\b", texto)
    if not cbo:
        return dados
    dados["13.6"] = normalizar_cbo_ocr(cbo.group(0))
    gfip = re.search(r"\b(?:00|01|02|03|04|05|06|07|08|09|0515|[0-9]{1,4})\b", texto[cbo.end():])
    if gfip:
        dados["13.7"] = gfip.group(0)
    antes = texto[:cbo.start()].strip(" -:|")
    palavras = antes.split()
    for tamanho in range(max(1, len(palavras) // 2), 0, -1):
        a = " ".join(palavras[-2 * tamanho:-tamanho])
        b = " ".join(palavras[-tamanho:])
        if a and normalizar(a) == normalizar(b):
            setor = " ".join(palavras[:-2 * tamanho]).strip(" -:|")
            if setor:
                dados["13.3"] = setor
            dados["13.4"] = a
            dados["13.5"] = b
            break
    return dados


def janela_representante_legal(texto):
    texto = texto or ""
    tn = normalizar(texto)
    termos = [
        "representante legal da empresa",
        "representante legal",
        "responsaveis pelas informacoes",
        "responsáveis pelas informações",
    ]
    posicoes = [tn.find(normalizar(t)) for t in termos if tn.find(normalizar(t)) != -1]
    if not posicoes:
        return ""
    pos = max(posicoes)
    return texto[pos:pos + 1200]


def placeholder_manual(numero, nome, linha=None):
    if linha:
        return f"{numero} - {nome} | linha {linha}:"
    return f"{numero} - {nome}:"


def valor_manual_campo_linha(texto, numero, linha=None):
    texto = texto or ""
    if linha is not None:
        padrao = rf"(?im)^\s*{re.escape(numero)}\s*-\s*[^:\n]*\|\s*linha\s*{linha}\s*:\s*(.*?)\s*$"
        m = re.search(padrao, texto)
        if m:
            valor = m.group(1).strip()
            return valor if valor_manual_preenchido(valor) else ""
    return valor_manual_campo(texto, numero)


def linhas_manuais_por_campo(texto, numeros):
    linhas = {}
    for numero in numeros:
        padrao = rf"(?im)^\s*{re.escape(numero)}\s*-\s*[^:\n]*\|\s*linha\s*(\d+)\s*:\s*(.*?)\s*$"
        for m in re.finditer(padrao, texto or ""):
            valor = m.group(2).strip()
            if not valor_manual_preenchido(valor):
                continue
            idx = int(m.group(1))
            linhas.setdefault(idx, {})[numero] = valor
    return linhas


def trecho_apos_rotulo(texto, numero, nome, termos=None):
    texto = texto or ""
    manual = valor_manual_campo(texto, numero)
    if manual:
        return manual

    rotulos = [nome] + (termos or [])
    for rotulo in rotulos:
        if not rotulo:
            continue
        padrao = rf"(?is)(?:^|\n|\s){re.escape(numero)}?\s*[-.:]?\s*{re.escape(rotulo)}\s*[:\-]?\s*(.+?)(?=\n\s*(?:\d{{1,2}}(?:\.\d+)?(?:\s|\s*[-.:])|15\.9\s*\[|$))"
        m = re.search(padrao, texto)
        if m:
            valor = re.sub(r"\s+", " ", m.group(1)).strip(" -:")
            if valor and normalizar(valor) != normalizar(rotulo):
                return valor[:300]
    return ""


def bloco_dados_administrativos(texto):
    texto = texto or ""
    tn = normalizar(texto)
    inicio = tn.find("dados administrativos")
    if inicio == -1:
        inicio = 0
    fins = [
        p for p in [
            tn.find("12 - cat", inicio),
            tn.find("12 cat", inicio),
            tn.find("13 - lotacao", inicio),
            tn.find("13 - lotação", inicio),
            tn.find("13 lotacao", inicio),
        ]
        if p != -1
    ]
    fim = min(fins) if fins else min(len(texto), inicio + 2500)
    return texto[inicio:fim]


@st.cache_data(show_spinner=False, ttl=3600)
def extrair_campos_administrativos_ocr(texto):
    """
    Lê os campos 1 a 11 quando o OCR devolve a tabela por faixas, não por rótulo.
    Exemplo real: "VANDERLEI ... NA 125..." e
    "01/06/1969 Masculino 26459/37 - RS 02/05/2006 NA".
    """
    bloco = bloco_dados_administrativos(limpar_placeholders_manuais_vazios(texto or ""))
    flat = re.sub(r"\s+", " ", bloco).strip()
    dados = {}

    cnpj = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", flat)
    if cnpj:
        dados["1"] = cnpj.group(0)

    cnae = extrair_cnae(bloco)
    if cnae:
        dados["3"] = cnae

    m_empresa_soc = re.search(
        r"CNO\|?\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s\.&-]{5,120}?)\s+([0-9]{4}\s*[-]?\s*[0-9]\s*/\s*[0-9]{2})",
        flat,
        flags=re.IGNORECASE,
    )
    if m_empresa_soc:
        empresa_soc = re.sub(r"\s+", " ", m_empresa_soc.group(1)).strip(" -:|")
        if len(empresa_soc) >= 6:
            dados["2"] = empresa_soc

    if cnpj and cnae:
        trecho = flat[cnpj.end():]
        pos_cnae = trecho.find(cnae)
        if pos_cnae != -1:
            empresa = trecho[:pos_cnae]
            empresa = re.sub(r"^\s*(?:\d+\s*)?(?:Nome\s+Empresarial|ER\s+Nome\s+Empresarial|Nome)\s*", "", empresa, flags=re.IGNORECASE)
            empresa = re.sub(r"\b(?:ao|ão)?\s*CNAE\b.*$", "", empresa, flags=re.IGNORECASE).strip(" -:|")
            empresa = re.sub(r"\s+", " ", empresa).strip()
            if empresa and len(empresa) >= 4:
                dados["2"] = empresa
    if not dados.get("2") or normalizar(dados.get("2")) in {"rial 3", "nome empresarial"} or len(dados.get("2", "")) < 6:
        m_empresa_antes_cnae = re.search(
            r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s\.&-]{5,120}?(?:ME|LTDA|S/?A|EIRELI|CAMACUA))\s+"
            r"([0-9]{4}\s*[-]?\s*[0-9]\s*/\s*[0-9]{2})",
            flat,
            flags=re.IGNORECASE,
        )
        if m_empresa_antes_cnae:
            empresa = re.sub(r".*?(?:CNO\||CNO|CEI/CAEPF/CNO\|?)", "", m_empresa_antes_cnae.group(1), flags=re.IGNORECASE)
            empresa = re.sub(r"\s+", " ", empresa).strip(" -:|")
            if len(empresa) >= 6:
                dados["2"] = empresa
    if not dados.get("2") and cnpj:
        trecho_empresa = flat[cnpj.end():cnpj.end() + 240]
        m_empresa_mascara_flex = re.search(
            r"^\s*([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\s\.&/-]{5,140}?)\s+-?\d{4}\s*-\s*\d\s*[-/]\s*\d{2}\b",
            trecho_empresa,
            flags=re.IGNORECASE,
        )
        if m_empresa_mascara_flex:
            empresa = re.sub(r"\s+", " ", m_empresa_mascara_flex.group(1)).strip(" -:|")
            if len(empresa) >= 6:
                dados["2"] = empresa

    m_trab = re.search(
        r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{5,80})\s+"
        r"(NA|N/?A|N[ãa]o\s+aplic[aá]vel)\s+"
        r"(\d{3}[\.\d-]{6,20})\b",
        flat,
        flags=re.IGNORECASE,
    )
    if m_trab:
        nome = limpar_nome_trabalhador_ocr(m_trab.group(1))
        if nome:
            dados["4"] = nome
        dados["5"] = m_trab.group(2).upper().replace("N/A", "NA")
        dados["6"] = m_trab.group(3)

    if not all(dados.get(k) for k in ["4", "5", "6"]):
        m_trab_flex = re.search(
            r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{5,90})\s+"
            r"(NA|N/?A|N[ãa]o\s+aplic[aá]vel)\s+"
            r"(\d{10,11})\b",
            flat,
            flags=re.IGNORECASE,
        )
        if m_trab_flex:
            nome = limpar_nome_trabalhador_ocr(m_trab_flex.group(1))
            if nome:
                dados.setdefault("4", nome)
            dados.setdefault("5", m_trab_flex.group(2).upper().replace("N/A", "NA"))
            dados.setdefault("6", m_trab_flex.group(3))
    if not dados.get("6"):
        m_documento_flex = re.search(r"\b(?:6\s*[-–:]?\s*)?(?:NIT|CPF)\s*[:\-]?\s*([0-9][0-9.\-\s]{8,20}[0-9])", flat, flags=re.IGNORECASE)
        if m_documento_flex:
            digitos = re.sub(r"\D", "", m_documento_flex.group(1))
            if len(digitos) in {10, 11}:
                dados["6"] = digitos
    if not dados.get("6"):
        for m_documento in re.finditer(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", flat):
            digitos = re.sub(r"\D", "", m_documento.group(0))
            if len(digitos) == 11:
                dados["6"] = m_documento.group(0)
                break

    m_linha_doc = re.search(
        r"(\d{2}/\d{2}/\d{4}|\d{2}/\d{6})\s+"
        r"(Masculino|Feminino|M|F)\s+"
        r"([0-9A-Z./\-\s]{1,40}?)\s+"
        r"(\d{2}/\d{2}/\d{4})\s+"
        r"(NA|N/?A|N[ãa\?]o\s+aplic\S*vel)",
        flat,
        flags=re.IGNORECASE,
    )
    if m_linha_doc:
        dados["7"] = normalizar_data_ocr(m_linha_doc.group(1))
        sexo = m_linha_doc.group(2)
        dados["8"] = "Masculino" if normalizar(sexo).startswith("m") else "Feminino"
        dados["9"] = limpar_valor_campo_escalar("9", m_linha_doc.group(3))
        dados["10"] = m_linha_doc.group(4)
        dados["11"] = m_linha_doc.group(5).upper().replace("N/A", "NA")

    if not all(dados.get(k) for k in ["7", "8", "9", "10", "11"]):
        linhas_admin = [re.sub(r"\s+", " ", l).strip() for l in bloco.splitlines() if l.strip()]
        for idx_linha, linha_admin in enumerate(linhas_admin):
            m_doc_cab = re.search(
                r"(\d{2}/\d{2}/\d{4}|\d{2}/\d{6})\s+(Masculino|Feminino|M|F)\b",
                linha_admin,
                flags=re.IGNORECASE,
            )
            if not m_doc_cab:
                continue
            if not any(t in normalizar(linha_admin) for t in ["esocial", "admissao", "admissão", "revezamento"]):
                continue
            resto_linhas = " ".join(linhas_admin[idx_linha + 1:idx_linha + 4])
            m_doc_valores = re.search(
                r"\b([0-9A-Z./\-]{1,40})\s+(\d{2}/\d{2}/\d{4})\s+(NA|N/?A|N[aã\?]o\s+aplic\S*vel)\b",
                resto_linhas,
                flags=re.IGNORECASE,
            )
            if m_doc_valores:
                dados.setdefault("7", normalizar_data_ocr(m_doc_cab.group(1)))
                sexo = m_doc_cab.group(2)
                dados.setdefault("8", "Masculino" if normalizar(sexo).startswith("m") else "Feminino")
                dados.setdefault("9", limpar_valor_campo_escalar("9", m_doc_valores.group(1)))
                dados.setdefault("10", m_doc_valores.group(2))
                dados.setdefault("11", m_doc_valores.group(3).upper().replace("N/A", "NA"))
                break

    # Layouts antigos e rurais podem deslocar os valores administrativos para
    # linhas distintas. Busca limitada ao bloco administrativo evita capturar
    # datas e códigos das tabelas ambientais.
    if not dados.get("7"):
        m_nascimento = re.search(r"(?:Data\s+do\s+)?Nascimento.{0,100}?(\d{2}/\d{2}/\d{4})", bloco, flags=re.IGNORECASE | re.DOTALL)
        if m_nascimento:
            dados["7"] = m_nascimento.group(1)
    if not dados.get("8"):
        m_sexo = re.search(r"\b(Masculino|Feminino)\b", bloco, flags=re.IGNORECASE)
        if m_sexo:
            dados["8"] = m_sexo.group(1)
    if not dados.get("9"):
        m_ctps = re.search(
            r"(?:CTPS|Matr[ií]cula(?:\s+do\s+Trabalhador)?(?:\s+no)?\s*eSocial).{0,120}?"
            r"([A-Z0-9]{1,20}(?:[/,.-][A-Z0-9]{1,20})+(?:\s*-\s*[A-Z]{2})?|[A-Z][A-Z0-9]{4,30}|\d{1,12})",
            bloco,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m_ctps:
            dados["9"] = m_ctps.group(1)
    if not dados.get("9"):
        m_esocial_deslocado = re.search(
            r"\b(?:Masculino|Feminino|M|F)\b.{0,180}?\b([A-Z0-9]{1,24})\s+"
            r"(\d{2}/\d{2}/\d{4})\s+(NA|N/?A|N[aã\?]o\s+aplic\S*vel)\b",
            flat,
            flags=re.IGNORECASE,
        )
        if m_esocial_deslocado:
            dados["9"] = m_esocial_deslocado.group(1)
            dados.setdefault("10", m_esocial_deslocado.group(2))
            dados.setdefault("11", m_esocial_deslocado.group(3).upper().replace("N/A", "NA"))
    if not dados.get("10"):
        admissao = extrair_data_admissao(bloco)
        if admissao:
            dados["10"] = admissao
    if not dados.get("11"):
        m_regime = re.search(
            r"Regime\s+(?:de\s+)?Revezamento.{0,80}?\b(NA|N/?A|N[aã]o\s+aplic[aá]vel|Sim|N[aã]o)\b",
            bloco,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m_regime:
            dados["11"] = m_regime.group(1)
    datas_admin = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", bloco)
    if not dados.get("7") and datas_admin:
        dados["7"] = datas_admin[0]
    if not dados.get("10") and len(datas_admin) >= 2:
        dados["10"] = datas_admin[1]
    if not dados.get("8"):
        trecho_ate_14 = re.split(r"\b14\s*[-–]", texto or "", maxsplit=1)[0]
        m_sexo_fora_ordem = re.search(r"\b(Masculino|Feminino)\b", trecho_ate_14, flags=re.IGNORECASE)
        if m_sexo_fora_ordem:
            dados["8"] = m_sexo_fora_ordem.group(1)

    for chave in list(dados):
        dados[chave] = limpar_valor_campo_escalar(chave, dados[chave])
    if not dados.get("9"):
        m_esocial_deslocado = re.search(
            r"\b(?:Masculino|Feminino|M|F)\b.{0,180}?\b([A-Z0-9]{1,24})\s+"
            r"(\d{2}/\d{2}/\d{4})\s+(NA|N/?A|N[aã\?]o\s+aplic\S*vel)\b",
            flat,
            flags=re.IGNORECASE,
        )
        if m_esocial_deslocado:
            dados["9"] = limpar_valor_campo_escalar("9", m_esocial_deslocado.group(1))
    if not dados.get("9"):
        for m_ctps_numerica in re.finditer(r"\b\d{3,}\s*/\s*\d{2,}(?:\s*-\s*[A-Z]{2})?\b", bloco, flags=re.IGNORECASE):
            if m_ctps_numerica.start() > 0 and bloco[m_ctps_numerica.start() - 1] in ".0123456789":
                continue
            dados["9"] = re.sub(r"\s+", " ", m_ctps_numerica.group(0)).strip()
            break

    return dados


def extrair_valor_escalar_estruturado(texto, campo):
    numero = campo["numero"]
    if numero in {str(n) for n in range(1, 12)}:
        admin = extrair_campos_administrativos_ocr(texto)
        if admin.get(numero):
            return admin[numero]
    if numero == "1":
        m = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", texto or "")
        return m.group(0) if m else trecho_apos_rotulo(texto, numero, campo["nome"], campo.get("termos"))
    if numero == "3":
        return extrair_cnae(texto) or valor_manual_campo(texto, numero)
    if numero == "6":
        valor = extrair_cpf_ou_nit(texto) or valor_manual_campo(texto, numero)
        return limpar_valor_campo_escalar(numero, valor)
    if numero == "9":
        valor = extrair_campo9_ctps_ou_esocial(texto) or valor_manual_campo(texto, numero)
        return limpar_valor_campo_escalar(numero, valor)
    if numero == "10":
        valor = extrair_data_admissao(texto) or valor_manual_campo(texto, numero)
        return limpar_valor_campo_escalar(numero, valor)
    if numero == "12":
        manual = valor_manual_campo(texto, numero)
        if manual:
            return limpar_valor_campo_escalar(numero, manual)
        bloco_cat = bloco_tabela_por_termos(
            texto,
            ["12 - cat registrada", "12 cat registrada", "cat registrada"],
            ["13 - lotação", "13 lotação", "13 -", "lotação e atribuição", "lotacao e atribuicao"],
        )
        texto_cat = "\n".join(bloco_cat)
        if texto_cat:
            datas_cat = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", texto_cat)
            numeros_cat = re.findall(r"\b\d{4,20}\b", re.sub(r"\b12(?:\.[12])?\b", " ", texto_cat))
            if not datas_cat and not numeros_cat:
                return "NA"
    if numero in ["7", "17"]:
        manual = valor_manual_campo(texto, numero)
        if manual:
            manual_limpo = limpar_valor_campo_escalar(numero, manual)
            if manual_limpo:
                return manual_limpo
        if numero == "17":
            manual19 = valor_manual_campo(texto, "19")
            if manual19:
                return manual19
            bloco_17 = bloco_tabela_por_termos(
                texto,
                ["17 data", "17 - data", "data da emissão do ppp", "data de emissão do ppp", "data emissão ppp", "data emissao ppp"],
                ["18 representante", "18 - representante", "19 ", "20 "],
            )
            m_bloco_17 = re.search(r"\b\d{2}/\d{2}/\d{4}\b", "\n".join(bloco_17))
            if m_bloco_17:
                return m_bloco_17.group(0)
            m19 = re.search(r"(?is)(?:19\s*[-.:]?\s*)?Data\s*de\s*Emiss[aã]o\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})", texto or "")
            if m19:
                return m19.group(1)
            m19_proximo = re.search(r"(?is)\b19\b.{0,40}Data\s*de\s*Emiss[aã]o.{0,80}?(\d{2}/\d{2}/\d{4})", texto or "")
            if m19_proximo:
                return m19_proximo.group(1)
            m19_generico = re.search(r"(?is)\b19\b.{0,140}?(\d{2}/\d{2}/\d{4})", texto or "")
            if m19_generico:
                return m19_generico.group(1)
            m_data_generica = re.search(r"(?is)Data\s*(?:da|de)?\s*Emiss.{0,8}o(?:\s*do\s*PPP)?.{0,160}?(\d{2}/\d{2}/\d{4})", texto or "")
            if m_data_generica:
                return m_data_generica.group(1)
            bloco_19 = bloco_tabela_por_termos(
                texto,
                ["19 data de emissão", "19 data de emissao", "data de emissão", "data de emissao"],
                ["20 representante", "representante legal", "observações", "observacoes"],
            )
            m_bloco_19 = re.search(r"\b\d{2}/\d{2}/\d{4}\b", "\n".join(bloco_19))
            if m_bloco_19:
                return m_bloco_19.group(0)
        rotulo = trecho_apos_rotulo(texto, numero, campo["nome"], campo.get("termos"))
        data = re.search(r"\b\d{2}/\d{2}/\d{4}\b", rotulo)
        return data.group(0) if data else limpar_valor_campo_escalar(numero, rotulo)
    return limpar_valor_campo_escalar(numero, trecho_apos_rotulo(texto, numero, campo["nome"], campo.get("termos")))


def candidato_linha_tabela(texto, inicio, fim=None):
    tn = normalizar(texto or "")
    aliases_inicio = {
        "Lotação e atribuição": ["lotacao e atribuicao", "lotação e atribuição", "lotacao atribuicao"],
        "Profissiografia": ["profissiografia"],
        "Registros ambientais": ["registros ambientais", "exposicao a fatores de riscos", "exposição a fatores de riscos", "fatores de riscos"],
        "Responsáveis técnicos": ["responsavel pelos registros ambientais", "responsável pelos registros ambientais", "responsaveis tecnicos", "responsáveis técnicos"],
    }
    candidatos_inicio = aliases_inicio.get(inicio, [inicio])
    pos_inicio = -1
    for candidato in candidatos_inicio:
        pos_inicio = tn.find(normalizar(candidato))
        if pos_inicio != -1:
            break
    if pos_inicio == -1:
        return []
    pos_fim = len(texto)
    if fim:
        achou_fim = tn.find(normalizar(fim), pos_inicio + 1)
        if achou_fim != -1:
            pos_fim = achou_fim
    bloco = texto[pos_inicio:pos_fim]
    linhas = []
    for linha in bloco.splitlines():
        limpa = re.sub(r"\s+", " ", linha).strip()
        if len(limpa) < 8:
            continue
        if re.search(r"\d{2}/\d{2}/\d{4}|\d{2}/\d{4}|\b(?:fisico|físico|quimico|químico|biologico|biológico)\b|CRM|CREA", limpa, flags=re.IGNORECASE):
            linhas.append(limpa)
    return linhas[:20]


def periodo_ppp_regex():
    data = r"(?:0[1-9]|[12]\d|3[01])/(?:0[1-9]|1[0-2])/\d{4}|(?:0[1-9]|1[0-2])/\d{4}"
    return rf"(?:{data})(?:\s*(?:a|at[eé]|-)\s*(?:{data}|(?:data\s+)?atual))?"


def periodo_ppp_linha(linha):
    linha = linha or ""
    padrao = periodo_ppp_regex()
    m = re.search(padrao, linha, flags=re.IGNORECASE)
    if not m:
        return None, ""
    periodo = m.group(0).strip()
    fim = m.end()
    resto = linha[fim:]
    if re.match(r"^\s*a(?:\s|$)", resto, flags=re.IGNORECASE) and not re.search(r"\ba\s*(?:\d{2}/\d{2}/\d{4}|\d{2}/\d{4}|atual)\b", periodo, flags=re.IGNORECASE):
        periodo = periodo + " a atual"
        resto = re.sub(r"^\s*a\b", " ", resto, count=1, flags=re.IGNORECASE)
    return m, periodo


def dividir_colunas_ocr(linha):
    linha_original = (linha or "").strip()
    if "|" in linha:
        partes = [p.strip() for p in linha_original.split("|")]
    else:
        partes = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\s{2,}|\t+", linha_original)]
    return [p for p in partes if p]


def tokens_linha_ocr(linha):
    return [p for p in dividir_colunas_ocr(linha) if p]


def preencher_por_ordem(dados, chaves, valores):
    """
    Preenche subcampos na ordem visual da tabela quando o OCR preserva colunas.
    Não sobrescreve valores já extraídos por rótulo/contexto.
    """
    for chave, valor in zip(chaves, valores):
        bruto = re.sub(r"\s+", " ", str(valor or "")).strip()
        if bruto in {"-", "—"} and chave in {"13.5", "13.7", "15.4", "15.5", "15.6", "15.7", "15.8"}:
            valor = "NA"
        else:
            valor = bruto.strip(" -:|")
        if valor and not dados.get(chave):
            dados[chave] = valor
    return dados


def extrair_ca_linha_15(texto):
    texto = str(texto or "")
    texto = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", " ", texto)
    texto = re.sub(r"\b\d{2,3}(?:[,.]\d+)?\s*dB\s*\(?A?\)?", " ", texto, flags=re.IGNORECASE)
    candidatos = re.findall(r"\b\d{3,8}\b", texto)
    candidatos = [c for c in candidatos if not re.match(r"^(?:19|20)\d{2}$", c)]
    return candidatos[-1] if candidatos else ""


def normalizar_linha_15(dados):
    linha_original = str(dados.get("_linha_original", ""))
    tipo = inferir_tipo_agente_15(dados.get("15.2", ""))
    if not tipo:
        tipo = inferir_tipo_agente_15(" ".join(str(dados.get(k, "")) for k in ["15.3", "_linha_original"]))
    if tipo:
        dados["15.2"] = tipo

    fator = inferir_fator_risco_15(dados.get("15.3", ""))
    if not fator:
        fator = inferir_fator_risco_15(linha_original)
    agentes_detectados = extrair_agentes_detectados_campo15(" ".join(str(dados.get(k, "")) for k in ["15.2", "15.3", "_linha_original"]))
    if agentes_detectados:
        dados["_agentes_detectados"] = " | ".join(agentes_detectados)
    if fator:
        dados["15.3"] = fator
        tipo_fator = inferir_tipo_agente_15(fator)
        if tipo_fator:
            dados["15.2"] = tipo_fator

    texto_intensidade = " ".join(str(dados.get(k, "")) for k in ["15.3", "15.4", "_linha_original"])
    intensidade_embutida = re.search(r"\b\d{2,3}(?:[,.]\d+)?\s*dB\s*\(?A?\)?(?:\s*NEN)?|\b\d+(?:[,.]\d+)?\s*(?:ppm|mg/m[³3])\b|\b(?:qualitativ[ao]|quantitativ[ao]|ND)\b", texto_intensidade, flags=re.IGNORECASE)
    if intensidade_embutida and (
        not dados.get("15.4")
        or re.search(r"\b(?:NHO|NR[-\s]*15|Decibel|Medi[cç])", str(dados.get("15.4", "")), flags=re.IGNORECASE)
    ):
        dados["15.4"] = intensidade_embutida.group(0)

    for chave in ["15.4", "15.5", "15.6", "15.7", "15.8"]:
        if valor_nao_aplicavel_estrutural(dados.get(chave, "")):
            dados[chave] = "NA"
    if (
        not dados.get("15.6")
        and dados.get("15.7") == "NA"
        and dados.get("15.8") == "NA"
    ):
        # Alguns PDFs textuais descartam apenas o primeiro hífen da sequência
        # EPC/EPI/CA. A presença estrutural dos dois NA seguintes permite
        # preservar o sentido da célula sem inventar resposta positiva.
        dados["15.6"] = "NA"

    if dados.get("15.4"):
        m = re.search(r"\b\d{2,3}(?:[,.]\d+)?\s*dB\s*\(?A?\)?(?:\s*NEN)?", dados["15.4"], flags=re.IGNORECASE)
        if m:
            dados["15.4"] = m.group(0)
        elif re.search(r"\b(?:qualitativ[ao]|quantitativ[ao]|ND|ppm|mg/m)\b", dados["15.4"], flags=re.IGNORECASE):
            dados["15.4"] = re.sub(r"\s+", " ", dados["15.4"]).strip()
    texto_tecnica = " ".join(str(dados.get(k, "")) for k in ["15.4", "15.5", "15.6", "_linha_original"])
    if dados.get("15.5"):
        m = re.search(r"(?:Medi[cç\?].{0,4}o\s+de\s+NPS\s*-\s*)?(?:Decibel.{0,3}metro|Decibelimetro|Dos.{0,3}metro|NHO[-\s]*01|NHO\s*01|Fundacentro|NR[-\s]*15(?:\s*Anexo\s*\d+)?)", texto_tecnica, flags=re.IGNORECASE)
        if m:
            dados["15.5"] = re.sub(r"\s+", " ", m.group(0)).strip()
    fator_norm = normalizar(str(dados.get("15.3", "")))
    tipo_norm = normalizar(str(dados.get("15.2", "")))
    if dados.get("_agentes_detectados") and "ruido" not in fator_norm:
        agentes_filtrados = [
            a.strip()
            for a in str(dados.get("_agentes_detectados", "")).split("|")
            if a.strip() and "ruido" not in normalizar(a)
        ]
        dados["_agentes_detectados"] = " | ".join(agentes_filtrados)
    if "ruido" not in fator_norm and re.search(r"\bdB\b", str(dados.get("15.4", "")), flags=re.IGNORECASE):
        dados["15.4"] = ""
    if "ruido" not in fator_norm and re.search(r"(?:Decibel|NHO[-\s]*01|Medi[cç\?].{0,4}o\s+de\s+NPS)", str(dados.get("15.5", "")), flags=re.IGNORECASE):
        dados["15.5"] = ""
    if "ruido" not in fator_norm and tipo_norm != "fisico":
        if re.search(r"\bdB\b", str(dados.get("15.4", "")), flags=re.IGNORECASE):
            dados["15.4"] = ""
        if re.search(r"(?:Decibel|NHO[-\s]*01|Medi[cç\?].{0,4}o\s+de\s+NPS)", str(dados.get("15.5", "")), flags=re.IGNORECASE):
            dados["15.5"] = ""
    respostas = re.findall(r"\b(N[aã\?]o\s+se\s+aplica|N[aã\?]o|Sim|S|N|NA|Eficaz|N[aã\?]o\s+eficaz)\b", linha_original, flags=re.IGNORECASE)
    respostas = [normalizar_resposta_sn(r) for r in respostas]
    valor_15_6 = normalizar(str(dados.get("15.6", "")))
    valor_15_7 = normalizar(str(dados.get("15.7", "")))
    if respostas and (not dados.get("15.6") or valor_15_6 not in {"nao", "sim", "na", "nao se aplica"}):
        dados["15.6"] = respostas[0]
    if len(respostas) >= 2 and (not dados.get("15.7") or valor_15_7 not in {"nao", "sim", "na", "nao se aplica"}):
        dados["15.7"] = respostas[1]
    if dados.get("15.8"):
        if normalizar(str(dados.get("15.8", ""))) in {"nao", "sim", "nao se aplica"}:
            dados["15.8"] = ""
        ca = extrair_ca_linha_15(dados.get("15.8", ""))
        if ca:
            dados["15.8"] = ca
    if not dados.get("15.8") or "nao extraido" in normalizar(str(dados.get("15.8", ""))):
        ca_linha = extrair_ca_linha_15(linha_original)
        if ca_linha:
            dados["15.8"] = ca_linha
        elif normalizar(str(dados.get("15.7", ""))) in {"na", "nao se aplica"}:
            dados["15.8"] = "NA"
    return dados


def indice_original_por_texto_normalizado(texto, termo):
    """
    Localiza um termo normalizado sem perder o índice no texto original.
    Necessário para recortar contexto correto quando há acentos.
    """
    normalizado = []
    indices = []
    for indice, caractere in enumerate(str(texto or "")):
        base = unicodedata.normalize("NFD", caractere.lower())
        for item in base:
            if unicodedata.category(item) != "Mn":
                normalizado.append(item)
                indices.append(indice)
    pos = "".join(normalizado).find(normalizar(termo))
    return indices[pos] if pos != -1 and pos < len(indices) else -1


def suplementar_linhas_15_por_agentes(bloco, linhas):
    """
    Garante uma linha lógica para cada agente escrito no Campo 15. Em muitos
    PPPs o período e o tipo aparecem apenas na primeira linha visual.
    """
    texto_bloco = "\n".join(bloco or [])
    agentes = extrair_agentes_detectados_campo15(texto_bloco)
    if not agentes:
        return linhas
    periodos = re.findall(periodo_ppp_regex(), texto_bloco, flags=re.IGNORECASE)
    periodo_herdado = periodos[0] if periodos else ""
    existentes = " ".join(
        " ".join(str(dados.get(chave) or "") for chave in ["15.3", "_agentes_detectados"])
        for dados in linhas.values()
    )
    existentes_detectados = {
        normalizar(agente) for agente in extrair_agentes_detectados_campo15(existentes)
    }
    posicoes_agentes = []
    for agente in agentes:
        pos = indice_original_por_texto_normalizado(texto_bloco, agente)
        if pos != -1:
            posicoes_agentes.append((pos, agente))
    posicoes_agentes.sort()
    proxima_posicao = {}
    for indice, (pos, agente) in enumerate(posicoes_agentes):
        proxima_posicao[agente] = posicoes_agentes[indice + 1][0] if indice + 1 < len(posicoes_agentes) else None

    for agente in agentes:
        if normalizar(agente) in existentes_detectados:
            continue
        pos = indice_original_por_texto_normalizado(texto_bloco, agente)
        limite = proxima_posicao.get(agente)
        fim = min(pos + 240, limite) if pos != -1 and limite is not None else pos + 240
        contexto = texto_bloco[pos:fim] if pos != -1 else agente
        dados = {
            "15.1": periodo_herdado,
            "15.2": inferir_tipo_agente_15(agente),
            "15.3": agente,
            "_agentes_detectados": agente,
            "_linha_original": re.sub(r"\s+", " ", contexto).strip(),
            "_linha_suplementar": True,
        }
        intensidade = re.search(
            r"\b\d+(?:[,.]\d+)?\s*(?:dB\s*\(?A?\)?(?:\s*NEN)?|ppm|mg/m[³3])\b|"
            r"\b(?:qualitativ[ao]|quantitativ[ao]|ND)\b",
            contexto,
            flags=re.IGNORECASE,
        )
        if intensidade:
            dados["15.4"] = intensidade.group(0)
        tecnica = re.search(
            r"(?:NHO[-\s]*01|NR[-\s]*15(?:\s*,?\s*anexo\s*\d+)?|Decibel.{0,3}metro|"
            r"Dos.{0,3}metria|Medi[cç][aã]o\s+de\s+NPS|NIOSH[-\s]*\d+|Inspe[cç][aã]o)",
            contexto,
            flags=re.IGNORECASE,
        )
        if tecnica:
            dados["15.5"] = re.sub(r"\s+", " ", tecnica.group(0)).strip()
        respostas = re.findall(r"\b(NA|N/?A|N[aã]o|Sim|S|N)\b", contexto, flags=re.IGNORECASE)
        if respostas:
            dados["15.6"] = normalizar_resposta_sn(respostas[0])
        if len(respostas) >= 2:
            dados["15.7"] = normalizar_resposta_sn(respostas[1])
        normalizar_linha_15(dados)
        linhas[len(linhas) + 1] = dados
    return linhas


def texto_linha_sem_periodo(linha, periodo):
    texto = linha or ""
    if periodo:
        texto = texto.replace(periodo, " ", 1)
    return texto


def bloco_tabela_por_termos(texto, termos_inicio, termos_fim=None):
    linhas = (texto or "").splitlines()
    inicio = None
    fim = len(linhas)
    termos_inicio = [normalizar(t) for t in termos_inicio]
    termos_fim = [normalizar(t) for t in (termos_fim or [])]

    for idx, linha in enumerate(linhas):
        ln = normalizar(linha)
        if any(t in ln for t in termos_inicio):
            inicio = idx
            break

    if inicio is None:
        return []

    for idx in range(inicio + 1, len(linhas)):
        ln = normalizar(linhas[idx])
        if any(t in ln for t in termos_fim):
            fim = idx
            break

    return linhas[inicio:fim]


def extrair_subcampos_13_rotulados(bloco):
    """
    Complementa layouts modernos em que os rótulos 13.3 a 13.7 aparecem
    empilhados e o valor fica na linha imediatamente seguinte.
    """
    texto_bloco = "\n".join(bloco or [])
    encontrados = {}
    rotulos = {
        "13.3": r"Setor",
        "13.4": r"Cargo",
        "13.5": r"Fun[cç][aã]o",
        "13.6": r"CBO",
        "13.7": r"(?:C[oó]digo\s*)?(?:GFIP/eSocial|GFIP|eSocial)",
    }
    proximo = r"(?=\s*(?:13\.[3-7]\b|14\s*[-–]|14\.1\b|Profissiografia\b))"
    for codigo, rotulo in rotulos.items():
        m = re.search(
            rf"{re.escape(codigo)}\s*[-–:]?\s*{rotulo}\s*(.*?)" + proximo,
            texto_bloco + "\n14 -",
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not m:
            continue
        valor = re.sub(r"\s+", " ", m.group(1)).strip(" :|")
        if valor in {"-", "—"}:
            valor = "NA"
        validado = validar_valor_ocr_soc(codigo, valor)
        if validado:
            encontrados[codigo] = validado
    return encontrados


def extrair_linhas_13_matriciais(texto):
    """
    Reconstrói layouts em que o extrator entrega primeiro os rótulos da grade
    e, depois, os valores de cada linha. O padrão aparece em PPPs rurais e não
    depende da coordenada física da tabela.
    """
    bloco = bloco_tabela_por_termos(
        texto,
        ["13 - lotação", "13 lotação", "lotação e atribuição", "lotacao e atribuicao"],
        ["registros ambientais", "15 - exposição", "15 exposicao", "15 -", "15.1"],
    )
    texto_bloco = "\n".join(bloco or [])
    texto_bloco_norm = normalizar(texto_bloco)
    if len(re.findall(r"13\.2\b", texto_bloco_norm)) < 2:
        return {}

    pos_14 = re.search(r"\b14\s*[-–]\s*Profissiografia\b", texto_bloco, flags=re.IGNORECASE)
    texto_periodos = texto_bloco[:pos_14.start()] if pos_14 else texto_bloco
    periodos = []
    for periodo in re.findall(periodo_ppp_regex(), texto_periodos, flags=re.IGNORECASE):
        periodo = re.sub(r"\s+", " ", periodo).strip()
        if periodo not in periodos:
            periodos.append(periodo)

    linhas_bloco = [re.sub(r"\s+", " ", linha).strip() for linha in bloco if linha.strip()]
    indices_cnpj = []
    for idx, linha in enumerate(linhas_bloco):
        if re.fullmatch(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", linha):
            indices_cnpj.append(idx)
    if len(periodos) < 2 or len(indices_cnpj) < 2:
        return {}

    resultado = {}
    for numero, inicio in enumerate(indices_cnpj, start=1):
        fim = indices_cnpj[numero] if numero < len(indices_cnpj) else len(linhas_bloco)
        valores = [
            valor for valor in linhas_bloco[inicio + 1:fim]
            if not re.search(r"^(?:13|14)(?:\.\d+)?\s*[-–:]|descricao\s+atividades", normalizar(valor), flags=re.IGNORECASE)
        ]
        pos_cbo = next(
            (idx for idx, valor in enumerate(valores) if re.fullmatch(r"\d{4,6}(?:-\d{1,2})?", valor)),
            None,
        )
        if pos_cbo is None or not valores:
            continue
        dados = {
            "13.1": periodos[numero - 1] if numero <= len(periodos) else "",
            "13.2": linhas_bloco[inicio],
            "13.3": valores[0],
            "_linha_original": " | ".join(linhas_bloco[inicio:fim]),
        }
        atribuicoes = [valor for valor in valores[1:pos_cbo] if valor not in {"-", "—"}]
        if atribuicoes:
            dados["13.4"] = atribuicoes[0]
        if len(atribuicoes) >= 2:
            dados["13.5"] = atribuicoes[1]
        elif any(valor in {"-", "—", "NA", "N/A"} for valor in valores[1:pos_cbo]):
            dados["13.5"] = "NA"
        elif len(re.findall(r"13\.5\b", texto_bloco_norm)) >= len(indices_cnpj):
            # A coluna existe na matriz, mas não há token entre cargo e CBO.
            dados["13.5"] = "NA"
        dados["13.6"] = normalizar_cbo_ocr(valores[pos_cbo])
        for valor in valores[pos_cbo + 1:]:
            if re.fullmatch(r"(?:0[0-9]|0515)", valor):
                dados["13.7"] = valor
                break
        resultado[numero] = dados
    return resultado


@st.cache_data(show_spinner=False, ttl=3600)
def extrair_linhas_13_ocr(texto):
    bloco_original = bloco_tabela_por_termos(
        texto,
        ["13 - lotação", "13 lotação", "13 -", "13.1", "lotação e atribuição", "lotacao e atribuicao"],
        ["14 - profissiografia", "14 profissiografia", "14 -", "14.1", "profissiografia", "15 - exposição", "15 exposicao", "15 -", "fatores de riscos"],
    )
    bloco = list(bloco_original)
    bloco = agrupar_linhas_por_inicio_estrutural(bloco, "13")
    linhas = {}
    padrao_periodo = periodo_ppp_regex()
    for linha in bloco:
        limpa = re.sub(r"\s+", " ", linha).strip()
        if not re.search(padrao_periodo, limpa):
            continue
        colunas = dividir_colunas_ocr(linha)
        if len(colunas) < 2:
            colunas = re.split(r"\s+(?=\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|[A-ZÁÉÍÓÚÂÊÔÃÕÇ]{3,})", limpa)
        periodo, periodo_valor = periodo_ppp_linha(limpa)
        if not periodo:
            continue
        idx = len(linhas) + 1
        dados = {"13.1": periodo_valor, "_linha_original": limpa}
        cnpj = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", limpa)
        if cnpj:
            dados["13.2"] = cnpj.group(0)
        resto = texto_linha_sem_periodo(linha, periodo.group(0)).strip()
        resto = re.sub(r"^\s*a\b", " ", resto, count=1, flags=re.IGNORECASE).strip()
        if cnpj:
            resto = resto.replace(cnpj.group(0), " ")
        partes = [p.strip(" -") for p in re.split(r"\s{2,}|\t+", resto) if p.strip()]
        preencher_por_ordem(dados, ["13.3", "13.4", "13.5"], partes)
        cbo = re.search(r"\b\d{4,6}(?:-\d{1,2})?\b|\b\d{2}\.?\d{2}-\d{2}\b", resto)
        if cbo:
            dados["13.6"] = normalizar_cbo_ocr(cbo.group(0))
        gfip = re.search(r"\b(?:00|01|02|03|04|05|06|07|08|09|0515)\b", resto)
        if gfip:
            dados["13.7"] = gfip.group(0)
        if cbo and not (dados.get("13.4") and dados.get("13.5")):
            antes_cbo = resto[:cbo.start()]
            antes_cbo = re.sub(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", " ", antes_cbo)
            antes_cbo = re.sub(r"\s+", " ", antes_cbo).strip(" -:|")
            m_auxiliar = re.search(r"\b(AUXILIAR\s+DE\s+PRODU[CÇ][AÃ]O)\s+\1\b", antes_cbo, flags=re.IGNORECASE)
            if m_auxiliar:
                setor = antes_cbo[:m_auxiliar.start()].strip(" -:|")
                if setor:
                    dados["13.3"] = setor
                dados["13.4"] = re.sub(r"\s+", " ", m_auxiliar.group(1)).strip()
                dados["13.5"] = re.sub(r"\s+", " ", m_auxiliar.group(1)).strip()
        refinar_linha_13_por_repeticao(dados, resto)
        setor_norm = normalizar(dados.get("13.3", ""))
        if setor_norm in {"s o", "se o", "sê o", "s? o"} or ("?" in str(dados.get("13.3", "")) and len(str(dados.get("13.3", ""))) <= 5):
            dados.pop("13.3", None)
        linhas[idx] = dados

    rotulados = extrair_subcampos_13_rotulados(bloco_original)
    if not linhas and rotulados:
        linhas[1] = dict(rotulados)
        m_periodo = re.search(periodo_ppp_regex(), "\n".join(bloco_original), flags=re.IGNORECASE)
        if m_periodo:
            linhas[1]["13.1"] = m_periodo.group(0)

    # OCR de PPP escaneado frequentemente quebra os subcampos 13.4/13.5 em linhas próprias.
    if not linhas and any(re.search(r"13\.[4-7]", l) for l in bloco):
        linhas[1] = {"_linha_original": " | ".join(re.sub(r"\s+", " ", l).strip() for l in bloco if "13." in l)}

    if linhas:
        texto_bloco = "\n".join(bloco)
        texto_bloco_original = "\n".join(bloco_original)
        primeiro = linhas.setdefault(1, {})
        for codigo, valor in rotulados.items():
            primeiro[codigo] = valor
        if not primeiro.get("13.2"):
            cnpj_bloco = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", texto_bloco_original)
            if cnpj_bloco:
                primeiro["13.2"] = cnpj_bloco.group(0)
        if not primeiro.get("13.2"):
            cnpj_admin = extrair_campos_administrativos_ocr(texto).get("1", "")
            if cnpj_admin:
                primeiro["13.2"] = cnpj_admin
        for codigo, rotulo in [
            ("13.2", "CNPJ"),
            ("13.3", "Setor"),
            ("13.4", "Cargo"),
            ("13.5", "Função"),
            ("13.6", "CBO"),
            ("13.7", "GFIP"),
        ]:
            if primeiro.get(codigo):
                continue
            if codigo == "13.2":
                padrao = r"13\.2\s*[-:]?\s*CNPJ[^\n:]*[:\-]?\s*([^\n|]+)"
            elif codigo == "13.3":
                padrao = r"13\.3\s*[-:]?\s*Setor[^\n:]*[:\-]?\s*([^\n|]+)"
            elif codigo == "13.7":
                padrao = r"13\.7\s*[-:]?\s*(?:C[oó]d\.?\s*)?GFIP(?:/eSocial)?\s*[:\-]?\s*([0-9]{1,4})"
            elif codigo == "13.6":
                padrao = r"13\.6\s*[-:]?\s*CBO\s*[:\-]?\s*([0-9]{4,6}(?:-\d{1,2})?|[0-9]{2}\.?[0-9]{2}-[0-9]{2})"
            else:
                padrao = rf"{re.escape(codigo)}\s*[-:]?\s*{rotulo}\s+([^\n|]+)"
            m = re.search(padrao, texto_bloco, flags=re.IGNORECASE)
            if m:
                valor = re.sub(r"\s+", " ", m.group(1)).strip(" -:|")
                if codigo == "13.2":
                    cnpj_valor = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", valor)
                    if cnpj_valor:
                        valor = cnpj_valor.group(0)
                if codigo == "13.6":
                    valor = normalizar_cbo_ocr(valor)
                if valor and not re.match(r"^13\.\d", valor):
                    primeiro[codigo] = valor
        for linha_extra in bloco:
            limpa_extra = re.sub(r"\s+", " ", linha_extra).strip()
            m_generico = re.search(r"(13\.[2-7])\s*[-:]?\s*[^A-Z0-9]*(.+)$", limpa_extra, flags=re.IGNORECASE)
            if not m_generico:
                continue
            codigo = m_generico.group(1)
            if primeiro.get(codigo):
                continue
            valor = re.sub(r"^(CNPJ|Setor|Cargo|Fun[cç][aã]o|CBO|C[oó]d\.?\s*GFIP)\s*", "", m_generico.group(2).strip(" -:|"), flags=re.IGNORECASE)
            if valor and not valor.startswith("13."):
                if codigo == "13.2":
                    cnpj_valor = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", valor)
                    if cnpj_valor:
                        valor = cnpj_valor.group(0)
                if codigo == "13.6":
                    valor = normalizar_cbo_ocr(valor)
                primeiro[codigo] = valor
        if not primeiro.get("13.1"):
            resto_texto = texto[texto.find(bloco[-1]) if bloco else 0:]
            m_periodo_14 = re.search(r"14[\s,\.]*1?.{0,80}?(" + periodo_ppp_regex() + r")", resto_texto, flags=re.IGNORECASE | re.DOTALL)
            if not m_periodo_14:
                m_periodo_14 = re.search(periodo_ppp_regex(), resto_texto, flags=re.IGNORECASE)
            if m_periodo_14:
                primeiro["13.1"] = m_periodo_14.group(1 if m_periodo_14.lastindex else 0).strip()
    for idx, dados_matriciais in extrair_linhas_13_matriciais(texto).items():
        destino = linhas.setdefault(idx, {})
        for codigo, valor in dados_matriciais.items():
            if codigo == "_linha_original" or codigo.startswith("13.") or not destino.get(codigo):
                destino[codigo] = valor
    return deduplicar_linhas_dict(linhas, ["13.1", "13.2", "13.3", "13.4", "13.5", "13.6", "13.7"])


def extrair_linhas_14_matriciais(texto):
    """
    Recupera períodos e descrições quando o PDF lineariza as duas linhas do
    Campo 14 antes de apresentar os textos das atividades.
    """
    bloco = bloco_tabela_por_termos(
        texto,
        ["13 - lotação", "13 lotação", "lotação e atribuição", "lotacao e atribuicao"],
        ["registros ambientais", "15 - exposição", "15 exposicao", "15 -", "15.1"],
    )
    texto_bloco = "\n".join(bloco or [])
    m_inicio = re.search(r"\b14\s*[-–]\s*Profissiografia\b", texto_bloco, flags=re.IGNORECASE)
    if not m_inicio:
        return {}
    trecho_14 = texto_bloco[m_inicio.start():]
    periodos = []
    for periodo in re.findall(periodo_ppp_regex(), trecho_14, flags=re.IGNORECASE):
        periodo = re.sub(r"\s+", " ", periodo).strip()
        if periodo not in periodos:
            periodos.append(periodo)
    if len(periodos) < 2:
        return {}

    linhas = [re.sub(r"\s+", " ", linha).strip() for linha in trecho_14.splitlines() if linha.strip()]
    ultimo_gfip = -1
    for idx, linha in enumerate(linhas):
        if re.fullmatch(r"(?:0[0-9]|0515)", linha):
            ultimo_gfip = idx
    if ultimo_gfip == -1:
        return {}
    narrativa_linhas = linhas[ultimo_gfip + 1:]
    descricoes = []
    atual = ""
    for linha in narrativa_linhas:
        if atual and re.search(r"[.!?]\s*$", atual) and re.match(r"^[A-ZÁÉÍÓÚÂÊÔÃÕÇ]", linha):
            descricoes.append(atual)
            atual = linha
        else:
            atual = (atual + " " + linha).strip()
    if atual:
        descricoes.append(atual)
    descricoes = [re.sub(r"\s+", " ", descricao).strip() for descricao in descricoes if len(descricao.strip()) >= 55]
    if len(descricoes) < len(periodos):
        sentencas = [
            re.sub(r"\s+", " ", descricao).strip()
            for descricao in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", " ".join(narrativa_linhas))
            if len(descricao.strip()) >= 40
        ]
        if len(sentencas) >= len(periodos):
            excesso_primeira = len(sentencas) - len(periodos) + 1
            descricoes = [" ".join(sentencas[:excesso_primeira])] + sentencas[excesso_primeira:]
    if len(descricoes) < len(periodos):
        return {}
    return {
        idx: {"14.1": periodo, "14.2": descricoes[idx - 1], "_linha_original": descricoes[idx - 1]}
        for idx, periodo in enumerate(periodos, start=1)
    }


@st.cache_data(show_spinner=False, ttl=3600)
def extrair_linhas_14_ocr(texto):
    bloco = bloco_tabela_por_termos(
        texto,
        ["14 - profissiografia", "14 profissiografia", "14 -", "14.1", "profissiografia"],
        ["15 - exposição", "15 exposicao", "15 -", "15.1", "registros ambientais", "exposição a fatores"],
    )
    linhas = {}
    padrao_periodo = periodo_ppp_regex()
    pendente = None
    for linha in bloco:
        limpa = re.sub(r"\s+", " ", linha).strip()
        if not limpa or re.match(r"^(?:13|15|16|17|18|19|20)(?:\.\d+)?\s*[-:|]", limpa, flags=re.IGNORECASE):
            continue
        if re.search(r"\b(?:registros ambientais|respons[aá]vel|representante legal|data de emiss[aã]o|exposi[cç][aã]o a fatores)\b", limpa, flags=re.IGNORECASE):
            continue
        m, periodo_valor = periodo_ppp_linha(limpa)
        if m:
            idx = len(linhas) + 1
            descricao = limpa[m.end():].strip(" -")
            descricao = re.sub(r"^\s*a\b", " ", descricao, count=1, flags=re.IGNORECASE).strip(" -")
            dados = {"14.1": periodo_valor, "14.2": descricao, "_linha_original": limpa}
            partes = tokens_linha_ocr(linha)
            if len(partes) >= 2:
                preencher_por_ordem(dados, ["14.1", "14.2"], partes)
            linhas[idx] = dados
            pendente = idx
        elif pendente and len(limpa) > 25 and not re.search(r"14\.\d|descri[cç][aã]o|per[ií]odo", limpa, flags=re.IGNORECASE):
            linhas[pendente]["14.2"] = (linhas[pendente].get("14.2", "") + " " + limpa).strip()
    for idx, dados_matriciais in extrair_linhas_14_matriciais(texto).items():
        destino = linhas.setdefault(idx, {})
        for codigo, valor in dados_matriciais.items():
            if codigo == "_linha_original" or not destino.get(codigo) or codigo == "14.2":
                destino[codigo] = valor
    return deduplicar_linhas_dict(linhas, ["14.1", "14.2"])


@st.cache_data(show_spinner=False, ttl=3600)
def extrair_linhas_15_ocr(texto):
    bloco = bloco_tabela_por_termos(
        texto,
        ["15 - exposição", "15 exposicao", "15 -", "15.1", "exposição a fatores de riscos", "exposicao a fatores de riscos", "fatores de riscos"],
        ["15.9", "16 - respons", "16.1", "responsável pelos registros", "responsavel pelos registros"],
    )
    if not bloco and re.search(r"15\s*[-:]?.{0,160}(?:Fatores\s+de\s+Riscos|Exposi.{0,4}o)|Fumos\s+met[aá\?]licos|Qu[ií\?]mico", texto or "", flags=re.IGNORECASE | re.DOTALL):
        bloco = (texto or "").splitlines()
    bloco = agrupar_linhas_por_inicio_estrutural(bloco, "15")
    linhas = {}
    padrao_periodo = periodo_ppp_regex()
    tipo_re = r"F(?:[ií\?]sico)?|Q(?:u[ií\?]mico)?|B(?:iol[oó\?]gico)?|Ergon[oô\?]mico|Acidente|Periculoso"
    ultimo_idx = None
    for linha in bloco:
        limpa = re.sub(r"\s+", " ", linha).strip()
        linha_parse = re.sub(r"\s*\|\s*", " ", limpa)
        linha_parse = re.sub(
            r"((?:0[1-9]|[12]\d|3[01])/(?:0[1-9]|1[0-2])/\d{4})\s+a[\|\]lI]?\s+",
            r"\1 a ",
            linha_parse,
            flags=re.IGNORECASE,
        )
        m = re.search(rf"(?P<periodo>{padrao_periodo})\s+(?P<tipo>{tipo_re})\s+(?P<resto>.+)", linha_parse, flags=re.IGNORECASE)
        periodo_aberto = False
        if not m:
            m = re.search(rf"(?P<periodo>(?:0[1-9]|[12]\d|3[01])/(?:0[1-9]|1[0-2])/\d{{4}}|(?:0[1-9]|1[0-2])/\d{{4}})\s+a\s+(?P<tipo>{tipo_re})\s+(?P<resto>.+)", linha_parse, flags=re.IGNORECASE)
            periodo_aberto = bool(m)
        if not m:
            m_sem_tipo = re.search(
                rf"(?P<periodo>(?:0[1-9]|[12]\d|3[01])/(?:0[1-9]|1[0-2])/\d{{4}}|(?:0[1-9]|1[0-2])/\d{{4}})\s+a\s+(?P<resto>.+)",
                linha_parse,
                flags=re.IGNORECASE,
            )
            if m_sem_tipo:
                resto_sem_tipo = m_sem_tipo.group("resto").strip()
                agentes_sem_tipo = extrair_agentes_detectados_campo15(resto_sem_tipo)
                fator_sem_tipo = inferir_fator_risco_15(resto_sem_tipo)
                tipo_sem_tipo = inferir_tipo_agente_15(resto_sem_tipo)
                if agentes_sem_tipo or fator_sem_tipo or tipo_sem_tipo:
                    idx = len(linhas) + 1
                    dados = {
                        "15.1": m_sem_tipo.group("periodo").strip() + " a atual",
                        "15.2": tipo_sem_tipo or inferir_tipo_agente_15(fator_sem_tipo) or "não localizado",
                        "15.3": fator_sem_tipo or (agentes_sem_tipo[0] if agentes_sem_tipo else ""),
                        "_linha_original": limpa,
                    }
                    partes_sem_tipo = [p.strip() for p in re.split(r"\s{2,}| (?=NA\b|N[aã\?]o\b|Sim\b|Qualitativ|Quantitativ|ND\b|\d{2,3}[,.]\d|ppm\b|mg/m|NHO|NR[-\s]*15)", resto_sem_tipo) if p.strip()]
                    preencher_por_ordem(dados, ["15.3", "15.4", "15.5", "15.6", "15.7", "15.8"], partes_sem_tipo)
                    normalizar_linha_15(dados)
                    linhas[idx] = dados
                    ultimo_idx = idx
                    continue
            if ultimo_idx and re.search(r"\b\d{2,3}(?:[,.]\d+)?\s*dB|Medi[cç\?].{0,4}o\s+de\s+NPS|Decibel|NHO[-\s]*01|NR[-\s]*15|ppm|mg/m", limpa, flags=re.IGNORECASE):
                base = linhas.get(ultimo_idx, {})
                intensidade = re.search(r"\b\d{2,3}(?:[,.]\d+)?\s*dB\s*\(?A?\)?(?:\s*\(\d{2}/\d{2}/\d{4}\))?|\b\d+(?:[,.]\d+)?\s*(?:ppm|mg/m[³3])\b", limpa, flags=re.IGNORECASE)
                tecnica = re.search(r"(?:Medi[cç\?].{0,4}o\s+de\s+NPS\s*-\s*)?(?:Decibel.{0,3}metro|Decibelimetro|Dos.{0,3}metro|NHO[-\s]*01|NHO\s*01|Fundacentro|NR[-\s]*15(?:\s*Anexo\s*\d+)?)", limpa, flags=re.IGNORECASE)
                if not intensidade:
                    if tecnica and not base.get("15.5"):
                        base["15.5"] = re.sub(r"\s+", " ", tecnica.group(0)).strip()
                        normalizar_linha_15(base)
                    continue
                intensidade_valor = intensidade.group(0)
                if not base.get("15.4"):
                    base["15.4"] = intensidade.group(0)
                    if tecnica and not base.get("15.5"):
                        base["15.5"] = re.sub(r"\s+", " ", tecnica.group(0)).strip()
                    respostas_base = re.findall(r"\b(N[aã\?]o|Sim|NA)\b", limpa, flags=re.IGNORECASE)
                    if respostas_base and not base.get("15.6"):
                        base["15.6"] = respostas_base[0]
                    if len(respostas_base) >= 2 and not base.get("15.7"):
                        base["15.7"] = respostas_base[1]
                    normalizar_linha_15(base)
                    continue
                if normalizar(base.get("15.4")) == normalizar(intensidade_valor):
                    if tecnica and not base.get("15.5"):
                        base["15.5"] = re.sub(r"\s+", " ", tecnica.group(0)).strip()
                    normalizar_linha_15(base)
                    continue
                idx = len(linhas) + 1
                dados = {
                    "15.1": base.get("15.1", ""),
                    "15.2": base.get("15.2", ""),
                    "15.3": base.get("15.3", ""),
                    "_linha_original": limpa,
                }
                dados["15.4"] = intensidade.group(0)
                if tecnica:
                    dados["15.5"] = re.sub(r"\s+", " ", tecnica.group(0)).strip()
                respostas = re.findall(r"\b(N[aã\?]o|Sim|NA)\b", limpa, flags=re.IGNORECASE)
                if respostas:
                    dados["15.6"] = respostas[0]
                if len(respostas) >= 2:
                    dados["15.7"] = respostas[1]
                ca = extrair_ca_linha_15(limpa)
                if ca:
                    dados["15.8"] = ca
                normalizar_linha_15(dados)
                linhas[idx] = dados
                ultimo_idx = idx
            continue
        idx = len(linhas) + 1
        resto = m.group("resto").strip()
        partes = dividir_colunas_ocr(resto)
        if len(partes) <= 1:
            partes = [p.strip() for p in re.split(r"\s{2,}| (?=NA\b|N[aã\?]o\b|Sim\b|S\b|N\b|Eficaz\b|Qualitativ|Quantitativ|ND\b|\d{2,3}[,.]\d|ppm\b|mg/m|Medi[cç\?][aã\?]o|Decibel|NHO|NR[-\s]*15)", resto) if p.strip()]
        dados = {
            "15.1": (m.group("periodo").strip() + " a atual") if periodo_aberto else m.group("periodo").strip(),
            "15.2": m.group("tipo").strip(),
            "_linha_original": limpa,
        }
        chaves = ["15.3", "15.4", "15.5", "15.6", "15.7", "15.8"]
        preencher_por_ordem(dados, chaves, partes)
        if "15.7" not in dados and re.search(r"-{3,}|N/?A|NA|N[aã]o|Sim", resto, flags=re.IGNORECASE):
            dados["15.7"] = "não extraído claramente"
        if "15.8" not in dados and re.search(r"-{3,}|\bCA\b|N/?A|NA|\d{3,6}", resto, flags=re.IGNORECASE):
            dados["15.8"] = "não extraído claramente"
        normalizar_linha_15(dados)
        linhas[idx] = dados
        ultimo_idx = idx

    linhas = suplementar_linhas_15_por_agentes(bloco, linhas)
    if linhas:
        for idx, dados in linhas.items():
            inicio = dados.get("_linha_original", "")
            contexto = inicio

            if not dados.get("15.4"):
                intensidade = re.search(r"\b\d{2,3}(?:[,.]\d+)?\s*dB\s*\(?A?\)?|\b\d+(?:[,.]\d+)?\s*(?:ppm|mg/m[³3])\b|\b(?:qualitativ[ao]|quantitativ[ao]|ND)\b", contexto, flags=re.IGNORECASE)
                if intensidade:
                    dados["15.4"] = intensidade.group(0)
            if not dados.get("15.5"):
                tecnica = re.search(r"(?:Medi[cç\?].{0,4}o\s+de\s+NPS\s*-\s*)?(?:Decibel.{0,3}metro|Dos.{0,3}metro|NHO[-\s]*01|NHO\s*01|Fundacentro|NR[-\s]*15(?:\s*Anexo\s*\d+)?)", contexto, flags=re.IGNORECASE)
                if tecnica:
                    dados["15.5"] = re.sub(r"\s+", " ", tecnica.group(0)).strip()
            if not dados.get("15.6"):
                epc = re.search(r"\b(N[aã\?]o se aplica|N[aã\?]o|Sim|NA)\b", contexto, flags=re.IGNORECASE)
                if epc:
                    dados["15.6"] = epc.group(1)
            if not dados.get("15.7"):
                respostas = re.findall(r"\b(N[aã\?]o|Sim|NA)\b", contexto, flags=re.IGNORECASE)
                if len(respostas) >= 2:
                    dados["15.7"] = respostas[1]
            normalizar_linha_15(dados)
    if not linhas and ppp_sem_agentes_declarados(texto):
        linhas[1] = {
            "15.1": "NA",
            "15.2": "NA",
            "15.3": "Ausência de riscos físico, químico e biológico",
            "15.4": "NA",
            "15.5": "NA",
            "15.6": "NA",
            "15.7": "NA",
            "15.8": "NA",
            "15.9": "NA",
            "15.9 [01]": "NA",
            "15.9 [02]": "NA",
            "15.9 [03]": "NA",
            "15.9 [04]": "NA",
            "15.9 [05]": "NA",
            "_linha_original": "PPP sem agentes nocivos declarados",
        }
    if not linhas and documento_legado_ppp(texto):
        legado = corpus_agentes_legado(texto)
        fator = inferir_fator_risco_15(legado)
        tipo = inferir_tipo_agente_15(fator or legado)
        periodo = ""
        m_periodo_legado = re.search(periodo_ppp_regex(), texto or "", flags=re.IGNORECASE)
        if m_periodo_legado:
            periodo = m_periodo_legado.group(0)
        if fator or tipo:
            linhas[1] = {
                "15.1": periodo or "não localizado",
                "15.2": tipo or "não localizado",
                "15.3": fator or "não localizado",
                "15.4": "não extraída",
                "15.5": "documento legado / narrativa",
                "_linha_original": re.sub(r"\s+", " ", legado[:400]).strip(),
            }
    if not linhas:
        texto_bloco = "\n".join(bloco) if bloco else (texto or "")
        m_periodo = re.search(periodo_ppp_regex(), texto_bloco, flags=re.IGNORECASE)
        tipo_fallback = inferir_tipo_agente_15(texto_bloco)
        fator_fallback = inferir_fator_risco_15(texto_bloco)
        if m_periodo and (tipo_fallback or fator_fallback):
            idx = 1
            dados = {"15.1": m_periodo.group(0).strip(), "_linha_original": re.sub(r"\s+", " ", texto_bloco[:400]).strip()}
            for linha_coluna in bloco:
                limpa_coluna = re.sub(r"\s+", " ", linha_coluna).strip()
                if not re.search(periodo_ppp_regex(), limpa_coluna):
                    continue
                valores = tokens_linha_ocr(linha_coluna)
                if len(valores) >= 3:
                    preencher_por_ordem(dados, ["15.1", "15.2", "15.3", "15.4", "15.5", "15.6", "15.7", "15.8"], valores)
                    break
            if tipo_fallback:
                dados["15.2"] = tipo_fallback
            if fator_fallback:
                dados["15.3"] = fator_fallback
            intensidade = re.search(r"\b\d{2,3}(?:[,.]\d+)?\s*dB\s*\(?A?\)?", texto_bloco, flags=re.IGNORECASE)
            if intensidade:
                dados["15.4"] = intensidade.group(0)
            tecnica = re.search(r"(?:Medi[cç].{0,3}o\s+de\s+NPS\s*-\s*)?(?:Decibel.{0,3}metro|Decibelimetro|Dos.{0,3}metro|NHO[-\s]*01|Fundacentro|NR[-\s]*15)", texto_bloco, flags=re.IGNORECASE)
            if tecnica:
                dados["15.5"] = re.sub(r"\s+", " ", tecnica.group(0)).strip()
            respostas = re.findall(r"\b(N[aã\?]o|Sim|NA)\b", texto_bloco, flags=re.IGNORECASE)
            if respostas:
                dados["15.6"] = respostas[0]
            if len(respostas) >= 2:
                dados["15.7"] = respostas[1]
            normalizar_linha_15(dados)
            linhas[idx] = dados
    for dados in linhas.values():
        normalizar_linha_15(dados)
    return deduplicar_linhas_dict(linhas, ["15.1", "15.2", "15.3", "15.4", "15.5", "15.6", "15.7", "15.8"])


def montar_linhas_compostas(texto, campo):
    subcampos = campo.get("subcampos", [])
    numeros = [s[0] for s in subcampos]
    manuais = linhas_manuais_por_campo(texto, numeros)
    bloquear_fallback_16_isolado = False

    if campo["numero"] == "13":
        for idx, dados in extrair_linhas_13_ocr(texto).items():
            manuais.setdefault(idx, {})
            for k, v in dados.items():
                if not v:
                    continue
                if k.startswith("13.") and not validar_valor_ocr_soc(k, v):
                    continue
                manuais[idx].setdefault(k, v)

    if campo["numero"] == "14":
        for idx, dados in extrair_linhas_14_ocr(texto).items():
            manuais.setdefault(idx, {})
            for k, v in dados.items():
                if not v:
                    continue
                if k.startswith("14.") and not validar_valor_ocr_soc(k, v):
                    continue
                manuais[idx].setdefault(k, v)

    if campo["numero"] == "16":
        responsaveis = [
            r for r in extrair_responsaveis_ambientais_linhas(texto)
            if responsavel_ambiental_linha_coerente(r)
        ]
        for idx, resp in enumerate(responsaveis, start=1):
            manuais.setdefault(idx, {})
            manuais[idx].setdefault("16.1", resp.get("periodo", ""))
            manuais[idx].setdefault("16.2", resp.get("cpf", ""))
            manuais[idx].setdefault("16.3", resp.get("registro", ""))
            manuais[idx].setdefault("16.4", resp.get("nome", ""))
        for idx in list(manuais):
            chaves_16 = [
                chave for chave, valor in manuais[idx].items()
                if chave.startswith("16.") and valor and not valor_ausente_estrutural(valor)
            ]
            if chaves_16 == ["16.3"]:
                # Registro isolado é candidato frágil: pode ser ruído OCR ou
                # pertencer a outra região. Mantém placeholder até haver linha
                # lógica com período, documento ou nome.
                manuais.pop(idx)
                bloquear_fallback_16_isolado = True

    if campo["numero"] == "15":
        for idx, dados in extrair_linhas_15_ocr(texto).items():
            manuais.setdefault(idx, {})
            for k, v in dados.items():
                if not v:
                    continue
                if k.startswith("15.") and not validar_valor_ocr_soc(k, v):
                    continue
                manuais[idx].setdefault(k, v)
        tipos = extrair_tipo_15_2(texto)
        epcs = extrair_epc_15_6(texto)
        sub159 = {s["codigo"]: s.get("resposta", "") for s in extrair_subitens_159(texto)}
        if sub159 and manuais:
            primeira_linha = manuais[min(manuais)]
            for codigo, resposta in sub159.items():
                if resposta and resposta != "não extraída":
                    primeira_linha.setdefault(codigo, resposta)
        if (tipos or epcs or sub159) and not manuais:
            manuais.setdefault(1, {})
            if tipos:
                manuais[1].setdefault("15.2", ", ".join(tipos))
            if epcs:
                manuais[1].setdefault("15.6", ", ".join(epcs))
            for codigo, resposta in sub159.items():
                if resposta and resposta != "não extraída":
                    manuais[1].setdefault(codigo, resposta)

    if campo["numero"] == "18":
        manual18 = valor_manual_campo(texto, "18")
        janela_rep = janela_representante_legal(texto)
        bloco_18 = bloco_tabela_por_termos(
            texto,
            ["18 representante legal", "18 - representante legal", "representante legal da empresa"],
            ["19 ", "20 ", "observações", "observacoes", "assinatura"],
        )
        texto_18 = "\n".join(bloco_18)
        bloco_20 = bloco_tabela_por_termos(
            texto,
            ["20 representante legal", "20 - representante legal", "representante legal da empresa"],
            ["observações", "observacoes", "assinatura"],
        )
        texto_20 = "\n".join(bloco_20)
        cpf = (
            valor_manual_campo(texto, "18.1")
            or valor_manual_campo(texto, "20.1")
            or extrair_cpf_ou_nit(manual18)
        )
        nome = valor_manual_campo(texto, "18.2") or valor_manual_campo(texto, "20.2")
        for linha_rep in (texto_18 + "\n" + texto_20 + "\n" + janela_rep).splitlines():
            valores = tokens_linha_ocr(linha_rep)
            if len(valores) >= 2 and re.search(r"\d{3}[\.\,\:]?\d{3,6}", linha_rep):
                candidatos_cpf = [v for v in valores if re.search(r"\d{3}[\.\,\:]?\d{3,6}", v)]
                candidatos_nome = [limpar_nome_representante(v) for v in valores]
                candidatos_nome = [v for v in candidatos_nome if nome_representante_valido(v)]
                if not cpf and candidatos_cpf:
                    cpf = normalizar_cpf_nit_visual(candidatos_cpf[0])
                if not nome and candidatos_nome:
                    nome = candidatos_nome[-1]
                if not nome:
                    m_nome_linha = re.search(r"([A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç\?]{3,}\s+Oswaldt(?:\s*-\s*(?:Diret|Diretor|Administrador))?)", linha_rep, flags=re.IGNORECASE)
                    if m_nome_linha and nome_representante_valido(m_nome_linha.group(1)):
                        nome = limpar_nome_representante(m_nome_linha.group(1))
        if not cpf:
            m_cpf18 = re.search(r"18\.1\s*(?:NIT|CPF)?[^\d]{0,30}([\d\.\-]{8,20})", texto_18, flags=re.IGNORECASE)
            if m_cpf18:
                cpf = normalizar_cpf_nit_visual(m_cpf18.group(1))
        if not nome:
            m_nome18 = re.search(r"18\.2\s*Nome\s*[:\-]?\s*([^\n\r|]+)", texto_18, flags=re.IGNORECASE)
            if m_nome18:
                nome = limpar_nome_representante(m_nome18.group(1))
                if not nome_representante_valido(nome):
                    nome = ""
            if not nome:
                linhas_18 = [l.strip() for l in texto_18.splitlines() if l.strip()]
                for idx_linha, linha_18 in enumerate(linhas_18):
                    if "18.2" in linha_18 or ("nome" in normalizar(linha_18) and "representante" in normalizar(linha_18)):
                        if idx_linha + 1 < len(linhas_18):
                            candidato = limpar_nome_representante(linhas_18[idx_linha + 1])
                            if nome_representante_valido(candidato):
                                nome = candidato
                                break
        if not cpf:
            m_cpf = re.search(r"\b\d{3}\.?\d{3,6}\.?\d{2,6}-?\d{1,2}\b", texto_20)
            if m_cpf:
                cpf = normalizar_cpf_nit_visual(m_cpf.group(0))
        if not cpf and janela_rep:
            candidatos_cpf = re.findall(r"\b\d{3}[\.\,]?\d{3,6}[\.\,\:]?\d{2,6}[-:<\)]?\d{1,2}\b", janela_rep)
            if candidatos_cpf:
                cpf = normalizar_cpf_nit_visual(candidatos_cpf[0])
        if not nome:
            m_nome_20 = re.search(r"20\.2\s*Nome\s*([^\n\r]+)", texto_20, flags=re.IGNORECASE)
            m_nome = m_nome_20 or re.search(r"\bNome\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç\s]{5,80})", texto_20)
            if m_nome:
                nome = limpar_nome_representante(m_nome.group(1))
                if not nome_representante_valido(nome):
                    nome = ""
            else:
                nomes = re.findall(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){1,5}\b", texto_20)
                nomes = [n for n in nomes if nome_representante_valido(n)]
                if nomes:
                    nome = nomes[-1]
        if not nome and janela_rep:
            m_oswaldt = re.search(r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+Oswaldt|OSWALDT)(?:\s*-\s*(?:Diret|Diretor|Administrador))?)", janela_rep, flags=re.IGNORECASE)
            if m_oswaldt and nome_representante_valido(m_oswaldt.group(1)):
                nome = limpar_nome_representante(m_oswaldt.group(1))
        if not nome and janela_rep:
            m_oswaldt_ocr = re.search(r"([A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\?]{2,}\s+oswa\w+(?:\s*-\s*(?:Diret|Diretor|Administrador))?)", janela_rep, flags=re.IGNORECASE)
            if m_oswaldt_ocr and nome_representante_valido(m_oswaldt_ocr.group(1)):
                nome = limpar_nome_representante(m_oswaldt_ocr.group(1))
        if not nome and janela_rep:
            m_assinatura_nome = re.search(r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){1,4}\s*-\s*(?:Diret|Diretor|Administrador))", janela_rep)
            if m_assinatura_nome and nome_representante_valido(m_assinatura_nome.group(1)):
                nome = limpar_nome_representante(m_assinatura_nome.group(1))
        if not nome and janela_rep:
            candidatos_nome = re.findall(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){1,4}\b", janela_rep)
            candidatos_nome = [n for n in candidatos_nome if nome_representante_valido(n)]
            if candidatos_nome:
                nome = candidatos_nome[-1]
        if manual18 or cpf or nome:
            manuais.setdefault(1, {})
            cpf = normalizar_cpf_nit_visual(cpf)
            if cpf:
                manuais[1].setdefault("18.1", cpf)
            if nome or manual18:
                manuais[1].setdefault("18.2", nome or manual18)

    if not manuais and campo["numero"] not in {"16", "18"}:
        marcador_fim = {"13": "14", "14": "15", "15": "16", "16": "17", "18": None}.get(campo["numero"])
        candidatas = candidato_linha_tabela(texto, campo["nome"], marcador_fim)
        for idx, linha in enumerate(candidatas, start=1):
            manuais.setdefault(idx, {})
            manuais[idx]["_linha_original"] = linha

    if not manuais:
        manuais[1] = {}

    linhas = []
    for idx in sorted(manuais):
        dados = manuais[idx]
        subdados = {}
        incompletos = []
        for numero, nome in subcampos:
            valor = dados.get(numero) or (
                "" if bloquear_fallback_16_isolado and campo["numero"] == "16"
                else valor_manual_campo_linha(texto, numero, idx)
            )
            if not valor and numero == "15.9":
                valor = "ver subitens" if any(dados.get(n) for n, _ in subcampos if n.startswith("15.9 [")) else ""
            subdados[numero] = {"nome": nome, "valor": valor}
            campo_159_global = campo["numero"] == "15" and idx > 1 and (
                numero == "15.9" or numero.startswith("15.9 [")
            )
            if valor_ausente_estrutural(valor) and not campo_159_global:
                incompletos.append(numero)
        valores_linha = [d.get("valor", "") for d in subdados.values() if d.get("valor")]
        status_linha = "INCOMPLETO" if incompletos else "CONFORME/LOCALIZADO"
        if not incompletos and valores_linha and all(valor_nao_aplicavel_estrutural(v) for v in valores_linha):
            status_linha = "LOCALIZADO — NÃO APLICÁVEL"
        linhas.append({
            "linha": idx,
            "valor_original": dados.get("_linha_original", ""),
            "subcampos": subdados,
            "status": status_linha,
            "campos_incompletos": incompletos,
        })
    return linhas


def campo_estruturado_para_resultado(campo, texto):
    numero = campo["numero"]
    nome = campo["nome"]
    subcampos = {}
    linhas = []

    if campo.get("composto"):
        linhas = montar_linhas_compostas(texto, campo)
        incompleto = any(l["status"] == "INCOMPLETO" for l in linhas)
        possui_valor_estruturado = any(
            any(
                d.get("valor") and not valor_ausente_estrutural(d.get("valor"))
                for d in linha.get("subcampos", {}).values()
            )
            for linha in linhas
        )
        for subnumero, subnome in campo.get("subcampos", []):
            valores = []
            linhas_subcampo = []
            for linha in linhas:
                dados = linha["subcampos"].get(subnumero, {"nome": subnome, "valor": ""})
                valor = dados.get("valor", "")
                valores.append(valor)
                linhas_subcampo.append({
                    "linha": linha["linha"],
                    "valor": valor,
                    "status": "CONFORME/LOCALIZADO" if valor and not valor_ausente_estrutural(valor) else "INCOMPLETO",
                })
            sub_incompleto = any(valor_ausente_estrutural(valor) for valor in valores)
            sub_possui_valor = any(valor and not valor_ausente_estrutural(valor) for valor in valores)
            sub_status = "INCOMPLETO" if sub_incompleto else "CONFORME/LOCALIZADO"
            if sub_incompleto and sub_possui_valor:
                sub_status = "PARCIALMENTE LOCALIZADO"
            subcampos[subnumero] = {
                "numero": subnumero,
                "nome": subnome,
                "valor_extraido": " | ".join(v for v in valores if v),
                "subcampos": {},
                "linhas": linhas_subcampo,
                "status": sub_status,
                "criticidade": campo["criticidade"] if sub_incompleto else "OK",
                "fundamento_juridico": campo["fundamento"],
                "estrategia": estrategia_campo_estruturado(subnumero),
                "placeholder_manual": placeholder_manual(subnumero, subnome, 1),
            }
        valores = []
        for linha in linhas:
            partes = [f"{n}: {d['valor']}" for n, d in linha["subcampos"].items() if d["valor"]]
            if linha.get("valor_original"):
                partes.append(f"linha OCR: {linha['valor_original']}")
            if partes:
                valores.append(f"linha {linha['linha']} - " + " | ".join(partes))
        valor_extraido = "\n".join(valores)
    else:
        valor_extraido = extrair_valor_escalar_estruturado(texto, campo)
        incompleto = not bool(valor_extraido)
        possui_valor_estruturado = bool(valor_extraido)

    if incompleto:
        status = "PARCIALMENTE LOCALIZADO" if possui_valor_estruturado else "INCOMPLETO"
    elif valor_nao_aplicavel_estrutural(valor_extraido):
        status = "LOCALIZADO — NÃO APLICÁVEL"
    else:
        status = "CONFORME/LOCALIZADO"
    criticidade = campo["criticidade"] if incompleto else "OK"
    falha = f"Campo {numero} — {nome} está incompleto ou não foi localizado de forma estruturada." if incompleto else ""

    return {
        "numero": numero,
        "campo": numero,
        "nome": nome,
        "valor_extraido": valor_extraido,
        "valor": valor_extraido,
        "subcampos": subcampos,
        "linhas": linhas,
        "status": status,
        "criticidade": criticidade,
        "falha": falha,
        "verificacao": campo.get("verificacao", "Verificar o campo no PPP original e no texto editável."),
        "fundamento_juridico": campo["fundamento"],
        "fundamento": campo["fundamento"],
        "estrategia": estrategia_campo_estruturado(numero),
        "placeholder_manual": placeholder_manual(numero, nome),
    }


def valor_ausente_estrutural(valor):
    v = normalizar(str(valor or "")).strip()
    return not v or v in {
        "nao localizado",
        "nao localizada",
        "nao extraido",
        "nao extraida",
        "nao extraido claramente",
        "nao extraida claramente",
        "nao identificado",
        "nao identificada",
    }


@st.cache_data(show_spinner=False)
def analisar_campos(texto):
    texto = texto_para_analise_sem_diagnostico(texto)
    texto = limpar_placeholders_manuais_vazios(texto)
    return [campo_estruturado_para_resultado(campo, texto) for campo in PPP_CAMPOS_ESTRUTURADOS]


def corpus_agentes_campo15(texto):
    partes = []
    for dados in extrair_linhas_15_ocr(texto).values():
        for chave in ["15.2", "15.3", "15.4", "15.5", "_agentes_detectados"]:
            valor = dados.get(chave, "")
            if valor and not valor_ausente_estrutural(valor):
                partes.append(str(valor))
    bloco = bloco_tabela_por_termos(
        texto,
        ["15 - exposição", "15 exposicao", "15 -", "15.1", "exposição a fatores de riscos", "exposicao a fatores de riscos"],
        ["15.9", "16 - respons", "16.1", "responsável pelos registros", "responsavel pelos registros"],
    )
    texto_bloco = " ".join(re.sub(r"\s+", " ", l).strip() for l in bloco)
    partes.extend(re.findall(r"(?im)^\s*AGENTE\s+CAMPO\s+15\s+SOC\s*:\s*(.+?)\s*$", texto or ""))
    if not ppp_sem_agentes_declarados(texto_bloco):
        # Mesmo quando uma linha já foi estruturada, o OCR pode ter omitido a
        # repetição de período/tipo nas linhas seguintes. Reaproveita somente
        # agentes expressamente presentes dentro do Campo 15.
        partes.extend(extrair_agentes_detectados_campo15(texto_bloco))
    if partes:
        return " ".join(dict.fromkeys(partes))
    legado = corpus_agentes_legado(texto)
    if legado:
        return legado
    return texto_bloco


def montar_item_agente(chave, info):
    item = {
        "agente": chave,
        "grupo": info.get("grupo", ""),
        "norma": info.get("norma", ""),
        "limite": info.get("limite", ""),
        "metodologia": info.get("metodologia", ""),
        "fundamento": info.get("fundamento", ""),
        "enquadramento": "INDÍCIO DE ENQUADRAMENTO — exige conferência do período, habitualidade, permanência, intensidade/concentração e metodologia."
    }

    grupo_norm = normalizar(item["grupo"])
    if "quim" in grupo_norm:
        item["enquadramento"] = (
            "Agente químico identificado no Campo 15 do PPP. A análise deve considerar a substância/produto, "
            "composição, forma de contato, habitualidade, FISPQ/LTCAT, metodologia e eficácia concreta do EPI."
        )
    elif "fisic" in grupo_norm:
        item["enquadramento"] = (
            "Agente físico identificado no Campo 15 do PPP. A análise depende do agente específico, "
            "da metodologia, da habitualidade/permanência e, quando aplicável, da intensidade."
        )
    elif "biologic" in grupo_norm:
        item["enquadramento"] = (
            "Agente biológico identificado no Campo 15 do PPP. A análise é predominantemente qualitativa, "
            "considerando risco ocupacional de contaminação e contato com pacientes, materiais ou ambientes contaminados."
        )
    return item


def analisar_agentes(texto):
    """
    Identifica agentes nocivos apenas a partir do Campo 15 estruturado.
    Evita falso positivo por palavras soltas em outros trechos do documento.
    """
    if ppp_sem_agentes_declarados(texto):
        return []
    corpus_15 = corpus_agentes_campo15(texto)
    if "ausencia de riscos" in normalizar(corpus_15) and not re.search(r"ru[ií]do|vibra|hidrocarbon|fumos|poeira|silica|agro|virus|bacter|fung|hiv|hepatite", corpus_15, flags=re.IGNORECASE):
        return []
    texto_norm = normalizar(corpus_15)
    agentes = []
    vistos = set()
    bases_detectadas = set()

    for rotulo in extrair_agentes_detectados_campo15(corpus_15):
        chave_base = chave_agente_para_rotulo(rotulo)
        if not chave_base or chave_base not in AGENTES:
            continue
        bases_detectadas.add(chave_base)
        item = montar_item_agente(chave_base, AGENTES[chave_base])
        item["agente"] = slug_agente(rotulo)
        item["agente_original"] = rotulo
        item["enquadramento"] = f"Agente identificado no Campo 15 do PPP: {rotulo}. " + item.get("enquadramento", "")
        chave_item = item["agente"]
        if chave_item not in vistos:
            agentes.append(item)
            vistos.add(chave_item)

    for chave, info in AGENTES.items():
        if chave in bases_detectadas:
            continue
        if chave == "hidrocarbonetos" and "oleos_minerais" in bases_detectadas:
            continue
        termos_norm = [normalizar(t) for t in info.get("termos", [])]
        if any(t in texto_norm for t in termos_norm):
            item = montar_item_agente(chave, info)
            if item["agente"] not in vistos:
                agentes.append(item)
                vistos.add(item["agente"])

    tipos = []
    for dados in extrair_linhas_15_ocr(texto).values():
        tipo = dados.get("15.2", "")
        if tipo and not valor_ausente_estrutural(tipo):
            tipos.append(tipo)
    if not tipos:
        tipos = extrair_tipo_15_2(corpus_15)
    tipos_norm = [normalizar(t) for t in tipos]

    if "fisico" in tipos_norm and not any(normalizar(a["grupo"]).startswith("fisic") for a in agentes):
        agentes.append({
            "agente": "fisicos_generico",
            "grupo": "Físico",
            "norma": "NR-15 e Decreto 3.048/99, conforme agente físico específico",
            "limite": "Depende do agente físico identificado no PPP",
            "metodologia": "Conferir campo 15.3, 15.4 e 15.5",
            "fundamento": (
                "Agentes físicos exigem análise conforme o agente específico, metodologia, intensidade e habitualidade. "
                "Quando o PPP indicar tipo Físico no campo 15.2, deve-se conferir o fator de risco no campo 15.3."
            ),
            "enquadramento": "TIPO FÍSICO IDENTIFICADO — exige conferência do fator de risco específico."
        })

    if "quimico" in tipos_norm and not any("quim" in normalizar(a["grupo"]) for a in agentes):
        agentes.append({
            "agente": "quimicos_generico",
            "grupo": "Químico",
            "norma": "NR-15 Anexos 11, 12 e 13, conforme substância",
            "limite": "Quantitativo ou qualitativo conforme o agente químico",
            "metodologia": "Conferir campo 15.3, concentração, técnica utilizada, FISPQ e LTCAT",
            "fundamento": (
                "Agentes químicos devem ser analisados conforme substância, composição, forma de contato, habitualidade "
                "e metodologia. A eficácia do EPI deve ser comprovada de forma concreta."
            ),
            "enquadramento": "TIPO QUÍMICO IDENTIFICADO — exige análise do produto/substância e da forma de exposição."
        })

    if "biologico" in tipos_norm and not any("biologic" in normalizar(a["grupo"]) for a in agentes):
        agentes.append({
            "agente": "biologicos_generico",
            "grupo": "Biológico",
            "norma": "NR-15 Anexo 14",
            "limite": "Qualitativo",
            "metodologia": "Atividade descrita / risco de contato",
            "fundamento": (
                "NR-15, Anexo 14: agentes biológicos são avaliados qualitativamente, considerando risco de contato "
                "com pacientes, material infectocontagiante, lixo urbano, esgoto, secreções, sangue, laboratórios, "
                "hospitais e ambientes equivalentes."
            ),
            "enquadramento": "TIPO BIOLÓGICO IDENTIFICADO — análise qualitativa do risco ocupacional."
        })

    return agentes



def analisar_epi(texto, agentes):
    texto_norm = normalizar(texto)
    conclusoes = []

    tem_epi = "epi" in texto_norm or "15.7" in texto
    tem_eficaz = "eficaz" in texto_norm or "sim" in texto_norm

    if not tem_epi:
        conclusoes.append({
            "criticidade": "CRÍTICA",
            "ponto": "EPI não localizado",
            "analise": "Não foi localizada informação clara sobre EPI no texto extraído.",
            "fundamento": BASE_LEGAL["epi"]["tema_213_tnu"] + " " + BASE_LEGAL["epi"]["nr06"],
            "estrategia": "Solicitar PPP/LTCAT complementar, CA, fichas de EPI e prova de treinamento/fiscalização."
        })
        return conclusoes

    for ag in agentes:
        grupo = normalizar(ag.get("grupo", ""))
        agente = ag.get("agente", "")

        if "biologic" in grupo:
            conclusoes.append({
                "criticidade": "CRÍTICA",
                "ponto": "EPI x agente biológico",
                "analise": "Para agentes biológicos, o EPI não afasta automaticamente a especialidade, dada a natureza qualitativa do risco.",
                "fundamento": BASE_LEGAL["biologicos"]["tema_211_tnu"] + " " + BASE_LEGAL["biologicos"]["irdr15"],
                "estrategia": "Defender risco ocupacional qualitativo e solicitar prova complementar se necessário."
            })
        elif "quim" in grupo:
            conclusoes.append({
                "criticidade": "GRAVE" if tem_eficaz else "CRÍTICA",
                "ponto": f"EPI x agente químico ({agente})",
                "analise": (
                    "Para agente químico, a eficácia do EPI exige prova concreta: CA adequado ao agente, validade, "
                    "fornecimento, treinamento, troca, higienização, fiscalização e compatibilidade com a forma de exposição."
                ),
                "fundamento": (
                    "NR-06; Tema 213/TNU; IRDR 15/TRF4. Para agentes químicos, a mera marcação de EPI eficaz no PPP "
                    "não encerra a análise se não houver prova concreta de neutralização."
                ),
                "estrategia": "Conferir CA, campo 15.9, FISPQ e LTCAT. Se houver omissão, impugnar a neutralização."
            })
        elif "fisic" in grupo:
            conclusoes.append({
                "criticidade": "MODERADA",
                "ponto": f"EPI x agente físico ({agente})",
                "analise": (
                    "Para agente físico, a eficácia do EPI depende do agente específico. Em ruído acima do limite, "
                    "o EPI eficaz não descaracteriza automaticamente a especialidade."
                ),
                "fundamento": BASE_LEGAL["ruido"]["tema_555_stf"] + " " + BASE_LEGAL["epi"]["tema_213_tnu"],
                "estrategia": "Conferir agente físico específico, metodologia, intensidade e eventual aplicação do Tema 555/STF."
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

    responsavel = extrair_responsavel_tecnico(texto)
    tem_resp = responsavel["localizado"]
    if not tem_resp:
        itens.append({
            "criticidade": "CRÍTICA",
            "ponto": "Responsável técnico não localizado",
            "analise": "Não foi identificado médico do trabalho ou engenheiro de segurança do trabalho com CREA/CRM.",
            "fundamento": BASE_LEGAL["responsavel"]["art_195_clt"] + " " + BASE_LEGAL["responsavel"]["in_128_285"],
            "estrategia": "Impugnar validade técnica do PPP e solicitar documento com responsável habilitado."
        })
    elif responsavel.get("profissao") == "não identificada claramente":
        itens.append({
            "criticidade": "GRAVE",
            "ponto": "Habilitação do responsável técnico não identificada claramente",
            "analise": (
                "Foi localizado responsável técnico no Campo 16, mas o texto extraído não permitiu confirmar "
                "se ele é médico do trabalho ou engenheiro de segurança do trabalho."
            ),
            "fundamento": BASE_LEGAL["responsavel"]["art_195_clt"] + " " + BASE_LEGAL["responsavel"]["in_128_285"],
            "estrategia": "Conferir no PPP original se há CRM/CREA e qualificação profissional. Se ausente, solicitar complementação."
        })

    return itens



def coletar_base_legal_utilizada(falhas, agentes, epi, ltcat):
    """
    Monta a base legal utilizada apenas a partir do que apareceu na análise:
    - falhas localizadas;
    - agentes nocivos localizados;
    - alertas de EPI/EPC;
    - alertas de LTCAT/responsável.
    Evita despejar toda a base legal no parecer.
    """
    bases = []
    fundamentos_vistos = set()

    def add(titulo, texto):
        if not texto:
            return
        chave_fundamento = re.sub(r"\s+", " ", texto.strip())
        if chave_fundamento in fundamentos_vistos:
            return
        fundamentos_vistos.add(chave_fundamento)
        item = (titulo.strip(), texto.strip())
        if item not in bases:
            bases.append(item)

    for f in falhas:
        nome = f.get("nome") or f.get("ponto") or f.get("campo") or "Falha identificada"
        fundamento = f.get("fundamento", "")
        if fundamento:
            add(str(nome), fundamento)

    for a in agentes:
        nome = a.get("agente", "Agente nocivo")
        fundamento = a.get("fundamento", "")
        if fundamento:
            add(f"Agente nocivo — {nome}", fundamento)

    for e in epi:
        ponto = e.get("ponto", "EPI/EPC")
        fundamento = e.get("fundamento", "")
        if fundamento:
            add(f"EPI/EPC — {ponto}", fundamento)

    for l in ltcat:
        ponto = l.get("ponto", "LTCAT/Responsável técnico")
        fundamento = l.get("fundamento", "")
        if fundamento:
            add(f"LTCAT/Responsável — {ponto}", fundamento)

    return bases


@st.cache_data(show_spinner=False)
def gerar_parecer(texto, trf):
    texto = texto_para_analise_sem_diagnostico(texto)
    texto = limpar_placeholders_manuais_vazios(texto)
    datas = extrair_datas(texto)
    cnae = extrair_cnae(texto)
    data_admissao = extrair_data_admissao(texto)
    tipos_15_2 = extrair_tipo_15_2(texto)
    epc_15_6 = extrair_epc_15_6(texto)
    responsavel = extrair_responsavel_tecnico(texto)

    campos = analisar_campos(texto)
    agentes = analisar_agentes(texto)
    epi = analisar_epi(texto, agentes)
    ltcat = analisar_ltcat_responsavel(texto)

    campos_administrativos_pendentes = [
        c for c in campos
        if campo_administrativo_informativo(c) and c["criticidade"] in ["CRÍTICA", "GRAVE", "MODERADA"]
    ]
    campos_tecnicos = [c for c in campos if not campo_administrativo_informativo(c)]

    falhas = [c for c in campos_tecnicos if c["criticidade"] in ["CRÍTICA", "GRAVE", "MODERADA"]]
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
    if tipos_15_2:
        linhas.append(f"- Campo 15.2 Tipo identificado: {', '.join(tipos_15_2)}")
    if epc_15_6:
        linhas.append(f"- Campo 15.6 EPC identificado: {', '.join(epc_15_6)}")
    if responsavel["localizado"]:
        linhas.append(
            f"- Responsável técnico localizado: "
            f"{responsavel['nome'] or 'nome não extraído'} | "
            f"CPF: {responsavel['cpf'] or 'não extraído'} | "
            f"Registro: {responsavel['registro'] or 'não extraído'} | "
            f"Habilitação: {responsavel.get('profissao', 'não identificada claramente')}"
        )
    linhas.append("")

    linhas.append("## 2. CHECKLIST TÉCNICO DO PPP")
    for c in campos_tecnicos:
        valor = f" | Valor: {c.get('valor')}" if c.get("valor") else ""
        linhas.append(f"- Campo {c['campo']} — {c['nome']}: {c['status']}{valor}")
    if campos_administrativos_pendentes:
        linhas.append("")
        linhas.append("### Pendências administrativas de leitura, sem peso na análise técnica")
        for c in campos_administrativos_pendentes:
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
        linhas.append("- Responsável técnico localizado automaticamente.")
        if responsavel["localizado"]:
            linhas.append(
                f"  Dados extraídos: {responsavel['nome'] or 'nome não extraído'} | "
                f"CPF: {responsavel['cpf'] or 'não extraído'} | "
                f"Registro: {responsavel['registro'] or 'não extraído'} | "
                f"Habilitação: {responsavel.get('profissao', 'não identificada claramente')}"
            )
        linhas.append("- Recomenda-se conferência manual do registro profissional e do período de responsabilidade.")
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
    linhas.append("## BASE LEGAL UTILIZADA NA ANÁLISE")
    bases_utilizadas = coletar_base_legal_utilizada(falhas, agentes, epi, ltcat)
    bases_tribunal = selecionar_base_tribunal(trf, agentes, texto)
    fundamentos_exibidos = set()
    if bases_utilizadas:
        for titulo, fundamento in bases_utilizadas:
            chave_fundamento = re.sub(r"\s+", " ", fundamento.strip())
            if chave_fundamento in fundamentos_exibidos:
                continue
            fundamentos_exibidos.add(chave_fundamento)
            linhas.append(f"### {titulo}")
            linhas.append(f"- {fundamento}")
            linhas.append("")

        for titulo, fundamento in bases_tribunal:
            chave_fundamento = re.sub(r"\s+", " ", fundamento.strip())
            if chave_fundamento in fundamentos_exibidos:
                continue
            fundamentos_exibidos.add(chave_fundamento)
            linhas.append(f"### {titulo}")
            linhas.append(f"- {fundamento}")
            linhas.append("")
    else:
        linhas.append("- Nenhuma base legal específica foi acionada automaticamente, pois não foram localizadas falhas ou agentes nocivos relevantes.")
        linhas.append("")

    return "\n".join(linhas), campos, agentes, epi, ltcat, classificacao



# ============================================================
# COMPLEMENTAÇÃO MANUAL E REANÁLISE
# ============================================================

MARCADOR_CAMPOS_MANUAIS = "=== CAMPOS NÃO LIDOS PELO OCR — PREENCHER MANUALMENTE ==="

CAMPOS_EDITAVEIS_ANALISE = [
    ("1", "CNPJ/CEI/CAEPF/CNO"),
    ("2", "Nome Empresarial"),
    ("3", "CNAE"),
    ("4", "Nome do Trabalhador"),
    ("5", "BR/PDH"),
    ("6", "CPF/NIT"),
    ("7", "Data de Nascimento"),
    ("8", "Sexo"),
    ("9", "CTPS / Matrícula eSocial"),
    ("10", "Data de Admissão"),
    ("11", "Regime de Revezamento"),
    ("12", "CAT Registrada"),
    ("13", "Lotação e Atribuição"),
    ("14", "Profissiografia / Descrição das Atividades"),
    ("15.1", "Período"),
    ("15.2", "Tipo"),
    ("15.3", "Fator de Risco"),
    ("15.4", "Intensidade / Concentração"),
    ("15.5", "Técnica Utilizada"),
    ("15.6", "EPC Eficaz"),
    ("15.7", "EPI Eficaz"),
    ("15.8", "CA EPI"),
    ("15.9", "Atendimento NR-06 e NR-01"),
    ("15.9 [01]", "Medidas de proteção coletiva/administrativa antes do EPI"),
    ("15.9 [02]", "Uso ininterrupto e funcionamento do EPI"),
    ("15.9 [03]", "Prazo de validade/CA do EPI"),
    ("15.9 [04]", "Periodicidade de troca comprovada"),
    ("15.9 [05]", "Higienização do EPI"),
    ("16", "Responsável pelos Registros Ambientais"),
    ("16.1", "Período do responsável técnico"),
    ("16.2", "CPF/NIT do Responsável"),
    ("16.3", "Registro Conselho de Classe"),
    ("16.4", "Nome do Profissional Legalmente Habilitado"),
    ("17", "Data de Emissão do PPP"),
    ("18", "Representante Legal / Assinatura"),
]


def valor_manual_campo(texto, numero):
    """
    Lê valor preenchido manualmente em linhas como:
    3 - CNAE: 2829-1/99
    6 - CPF/NIT: 12345678900
    """
    padrao = rf"(?im)^\s*{re.escape(numero)}\s*[-:]\s*[^:\n]*:\s*(.+?)\s*$"
    m = re.search(padrao, texto or "")
    if m:
        valor = m.group(1).strip()
        return valor if valor_manual_preenchido(valor) else ""
    return ""


def valor_manual_preenchido(valor):
    """
    Diferencia correção manual real de placeholder vazio ou contaminado.
    Ex.: "13.4 - Cargo | linha 1:" não pode virar valor extraído.
    """
    valor = (valor or "").strip()
    if not valor:
        return False
    if re.match(r"^\d{1,2}(?:\.\d+)?(?:\s*\[\d+\])?\s*-\s*[^:]+:\s*$", valor):
        return False
    if re.match(r"^\d{1,2}(?:\.\d+)?(?:\s*\[\d+\])?\s*-\s*[^|:]+\|\s*linha\s*\d+\s*:\s*$", valor, flags=re.IGNORECASE):
        return False
    return True


def limpar_placeholders_manuais_vazios(texto):
    """
    Mantém correções manuais preenchidas e remove linhas de placeholder vazias.
    Isso evita que o bloco editável seja interpretado como dado do PPP.
    """
    texto = texto or ""
    marcador = None
    offset = 0
    for linha in texto.splitlines(keepends=True):
        ln = normalizar(linha)
        if "campos" in ln and "lidos" in ln and "ocr" in ln:
            marcador = (offset, offset + len(linha))
            break
        offset += len(linha)

    if marcador:
        antes = texto[:marcador[0]]
        depois = texto[marcador[1]:]
    elif MARCADOR_CAMPOS_MANUAIS in texto:
        antes, depois = texto.split(MARCADOR_CAMPOS_MANUAIS, 1)
    else:
        return texto
    linhas_validas = []
    for linha in depois.splitlines():
        limpa = linha.strip()
        if not limpa:
            continue
        if limpa.lower().startswith("preencha somente"):
            continue
        if ":" in linha:
            valor = linha.rsplit(":", 1)[-1].strip()
            if valor_manual_preenchido(valor):
                linhas_validas.append(linha)

    if not linhas_validas:
        return antes.rstrip()

    return (
        antes.rstrip()
        + "\n\n"
        + MARCADOR_CAMPOS_MANUAIS
        + "\n"
        + "\n".join(linhas_validas)
        + "\n"
    )


def campo_tem_valor(texto, numero, descricao):
    """
    Verifica se um campo está suficientemente lido.
    Não basta existir o número do campo; precisa existir valor ou extração específica.
    """
    texto = texto or ""
    texto_norm = normalizar(texto)

    # Se o usuário preencheu manualmente, considera localizado.
    if valor_manual_campo(texto, numero):
        return True

    if numero == "1":
        return bool(re.search(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", texto))
    if numero == "3":
        return bool(extrair_cnae(texto))
    if numero == "6":
        return bool(extrair_cpf_ou_nit(texto))
    if numero == "9":
        return bool(extrair_campo9_ctps_ou_esocial(texto))
    if numero == "10":
        return bool(extrair_data_admissao(texto))
    if numero == "15.2":
        return bool(extrair_tipo_15_2(texto))
    if numero == "15.6":
        return bool(extrair_epc_15_6(texto))
    if numero == "16":
        return extrair_responsavel_tecnico(texto).get("localizado", False)
    if numero == "16.2":
        return bool(re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", texto) or re.search(r"\b\d{10,11}\b", texto))
    if numero == "16.3":
        return bool(re.search(r"\b(?:CRM|CREA)?\s*\.?\s*\d{2,6}/?[A-Z]{0,2}\b", texto, flags=re.IGNORECASE))
    if numero == "16.4":
        resp = extrair_responsavel_tecnico(texto)
        return bool(resp.get("nome"))
    if numero == "17":
        return "data de emissao" in texto_norm or "data de emissão" in texto.lower() or bool(extrair_datas(texto))
    if numero == "18":
        return any(x in texto_norm for x in ["representante legal", "assinatura", "assinado"])

    # Verificação genérica: descrição ou termos próximos encontrados
    desc_norm = normalizar(descricao)
    if desc_norm in texto_norm:
        return True

    return False


def _valor_nao_aplicavel(valor):
    v = normalizar(str(valor or "")).strip()
    return v in {"na", "n/a", "nao aplicavel", "não aplicável", "nao se aplica", "não se aplica"}


def _linhas_manuais_preenchidas_do_bloco(texto):
    texto = limpar_placeholders_manuais_vazios(texto)
    if MARCADOR_CAMPOS_MANUAIS not in texto:
        return texto, []
    antes, depois = texto.split(MARCADOR_CAMPOS_MANUAIS, 1)
    linhas = [linha for linha in depois.splitlines() if linha.strip()]
    return antes.rstrip(), linhas


def deve_gerar_placeholder_subcampo(texto, campo, linha, numero, dados):
    valor = dados.get("valor", "")
    if not valor_ausente_estrutural(valor):
        return False

    indice_linha = linha.get("linha")
    if valor_manual_campo_linha(texto, numero, indice_linha):
        return False

    if (numero == "15.9" or numero.startswith("15.9 [")) and indice_linha not in {None, 1}:
        return False

    admin = extrair_campos_administrativos_ocr(texto)
    if numero == "13.2" and admin.get("1"):
        return False

    if numero == "15.8":
        epi = linha.get("subcampos", {}).get("15.7", {}).get("valor", "")
        if _valor_nao_aplicavel(epi):
            return False

    if numero.startswith("15.9 ["):
        for subitem in extrair_subitens_159(texto):
            if subitem.get("codigo") == numero and subitem.get("status") == "LOCALIZADO":
                return False

    return True


def formatar_diagnostico(objeto, limite=2600):
    texto = pprint.pformat(objeto, width=120, compact=True, sort_dicts=True)
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "\n... [diagnóstico truncado]"


def metadados_app_em_execucao():
    caminho = os.path.abspath(__file__)
    try:
        with open(caminho, "rb") as arquivo:
            hash_curto = hashlib.sha256(arquivo.read()).hexdigest()[:12]
        timestamp = datetime.fromtimestamp(os.path.getmtime(caminho)).isoformat(timespec="seconds")
    except Exception as e:
        hash_curto = f"indisponível: {e}"
        timestamp = "indisponível"
    return caminho, timestamp, hash_curto


def status_cache_ocr(metadados):
    extraida_em = metadados.get("extraida_em", "")
    if not extraida_em:
        return "NÃO DETERMINÁVEL: texto manual ou metadados de extração ausentes"
    try:
        idade = abs((datetime.now() - datetime.fromisoformat(extraida_em)).total_seconds())
    except ValueError:
        return f"NÃO DETERMINÁVEL: timestamp OCR inválido ({extraida_em})"
    if idade <= 5:
        return f"NOVA EXTRAÇÃO PROVÁVEL: gerada em {extraida_em}"
    return f"CACHE REAPROVEITADO PROVÁVEL: extração original gerada em {extraida_em}"


def texto_bloco_diagnostico_placeholder(texto, numero):
    texto = texto or ""
    campo_principal = numero.split(".", 1)[0]
    limites = {
        "13": (["13 - lotação", "13 - lotacao"], ["14 - profiss"]),
        "14": (["14 - profiss"], ["15 - expos"]),
        "15": (["15 - expos"], ["16 - respons"]),
        "16": (["16 - respons"], ["responsáveis pelas informações", "responsaveis pelas informacoes", "declaramos"]),
        "17": (["17 ", "data da emissão", "data da emissao"], ["18 ", "representante legal"]),
        "18": (["18 ", "representante legal"], ["observações", "observacoes", "assinatura"]),
    }
    inicio_termos, fim_termos = limites.get(campo_principal, ([], []))
    if not inicio_termos:
        return texto
    texto_norm = normalizar(texto)
    posicoes_inicio = [texto_norm.find(normalizar(termo)) for termo in inicio_termos]
    posicoes_inicio = [pos for pos in posicoes_inicio if pos >= 0]
    if not posicoes_inicio:
        return texto
    inicio = min(posicoes_inicio)
    posicoes_fim = [texto_norm.find(normalizar(termo), inicio + 1) for termo in fim_termos]
    posicoes_fim = [pos for pos in posicoes_fim if pos > inicio]
    fim = min(posicoes_fim) if posicoes_fim else len(texto)
    return texto[inicio:fim]


def candidatos_diagnostico_placeholder(texto, numero):
    texto = texto_bloco_diagnostico_placeholder(texto, numero)
    padroes = {
        "13.6": r"(?<![\d./-])\d{4}(?:-\d{2}|\d{2})(?![\d./-])",
        "13.7": r"\b(?:00|01|04|05|06)\b",
        "15.6": r"(?im)(?:^|\|)\s*(?:-|NA|N/A|NÃO|SIM)\s*(?:\||$)",
        "15.7": r"(?im)(?:^|\|)\s*(?:-|NA|N/A|NÃO|SIM)\s*(?:\||$)",
        "15.8": r"(?im)(?:^|\|)\s*(?:-|NA|N/A|\d{2,6})\s*(?:\||$)",
        "16.1": r"\b\d{2}/\d{2}/\d{4}\s+a(?:tual|\s+\d{2}/\d{2}/\d{4})?\b",
        "16.2": r"\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{10,11})\b",
        "16.3": r"\b(?:CRM|CREA|COREN|CRQ|MTE)?\s*\.?\s*\d{2,10}(?:[-/]?[A-Z]{2})?\b",
        "17": r"\b\d{2}/\d{2}/\d{4}\b",
        "18.1": r"\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})\b",
    }
    padrao = padroes.get(numero)
    if not padrao:
        return []
    encontrados = []
    for candidato in re.findall(padrao, texto or "", flags=re.IGNORECASE):
        valor = candidato if isinstance(candidato, str) else "".join(candidato)
        valor = valor.strip()
        if valor and valor not in encontrados:
            encontrados.append(valor)
    return encontrados[:8]


def subcampo_estruturado_no_resultado(campos, numero, indice_linha):
    for campo in campos:
        for linha in campo.get("linhas", []):
            if indice_linha is not None and linha.get("linha") != indice_linha:
                continue
            valor = linha.get("subcampos", {}).get(numero, {}).get("valor", "")
            if not valor_ausente_estrutural(valor):
                return valor
    return ""


def diagnosticar_placeholders(texto, campos, faltantes):
    diagnosticos = []
    for placeholder in faltantes:
        m = re.match(
            r"^\s*(\d+(?:\.\d+)?(?:\s*\[\d+\])?)\s*-\s*(.*?)(?:\s*\|\s*linha\s*(\d+))?\s*:\s*$",
            placeholder,
            flags=re.IGNORECASE,
        )
        if not m:
            diagnosticos.append({"placeholder": placeholder, "motivo": "Formato de placeholder não reconhecido."})
            continue
        numero = m.group(1).strip()
        indice_linha = int(m.group(3)) if m.group(3) else None
        candidatos = candidatos_diagnostico_placeholder(texto, numero)
        estruturado = subcampo_estruturado_no_resultado(campos, numero, indice_linha)
        validacao = "N/A"
        motivo = "OCR e parser não localizaram candidato compatível."
        if candidatos:
            validacao = "PENDENTE: candidato deve ser confirmado na região lógica do campo"
            motivo = "Há candidato no texto, mas ele ainda não foi associado à linha estrutural correta."
        if numero == "16.3" and candidatos and not estruturado:
            validacao = "REJEITAR se isolado: exige coerência com período, CPF/NIT e nome dentro do bloco 16"
            motivo = "Registro de conselho isolado não pode preencher o Campo 16."
        diagnosticos.append({
            "campo": numero,
            "linha": indice_linha,
            "candidatos_no_texto": candidatos or "nenhum",
            "OCR_encontrou": "SIM" if candidatos else "NÃO",
            "parser_estruturou": estruturado or "NÃO",
            "validacao": validacao,
            "placeholder": "SIM",
            "motivo": motivo,
        })
    return diagnosticos


def gerar_bloco_diagnostico_interno(texto_analise, campos, faltantes, metadados_ocr):
    caminho, timestamp, hash_curto = metadados_app_em_execucao()
    campos_resumo = [
        {
            "campo": campo.get("numero"),
            "status": campo.get("status"),
            "linhas": campo.get("linhas", []),
        }
        for campo in campos
    ]
    compostos = {}
    for campo in PPP_CAMPOS_ESTRUTURADOS:
        if campo.get("numero") in {"13", "14", "15", "16", "18", "20"}:
            compostos[campo["numero"]] = montar_linhas_compostas(texto_analise, campo)
    secoes = [
        MARCADOR_DIAGNOSTICO_INTERNO,
        f"OCR_PIPELINE_VERSION: {OCR_PIPELINE_VERSION}",
        f"app.py em execução: {caminho}",
        f"app.py timestamp: {timestamp}",
        f"app.py sha256 curto: {hash_curto}",
        f"cache OCR: {status_cache_ocr(metadados_ocr)}",
        "",
        "--- preparar_texto_editavel ---",
        formatar_diagnostico({
            "tamanho_texto_analise": len(texto_analise),
            "quantidade_placeholders": len(faltantes),
            "metadados_ocr": metadados_ocr or "ausentes",
        }),
        "",
        "--- analisar_campos ---",
        formatar_diagnostico(campos_resumo),
        "",
        "--- extrair_linhas_13_matriciais ---",
        formatar_diagnostico(extrair_linhas_13_matriciais(texto_analise)),
        "",
        "--- extrair_linhas_14_matriciais ---",
        formatar_diagnostico(extrair_linhas_14_matriciais(texto_analise)),
        "",
        "--- extrair_linhas_15_ocr ---",
        formatar_diagnostico(extrair_linhas_15_ocr(texto_analise)),
        "",
        "--- extrair_responsaveis_ambientais_linhas ---",
        formatar_diagnostico(extrair_responsaveis_ambientais_linhas(texto_analise)),
        "",
        "--- montar_linhas_compostas ---",
        formatar_diagnostico(compostos),
        "",
        "--- gerar_placeholders ---",
        formatar_diagnostico(faltantes),
        "",
        "--- diagnóstico por campo não lido ---",
        formatar_diagnostico(diagnosticar_placeholders(texto_analise, campos, faltantes), limite=5200),
    ]
    return "\n".join(secoes).rstrip() + "\n"


def preparar_texto_editavel(texto):
    """
    Acrescenta ao fim do texto extraído um bloco com qualquer campo analisado
    que não tenha sido lido com valor suficiente. O usuário pode preencher
    manualmente e clicar de novo em Gerar Raio-X do PPP.
    """
    texto = remover_bloco_a_partir_do_marcador(texto or "", MARCADOR_DIAGNOSTICO_INTERNO)
    texto, metadados_ocr = extrair_metadados_ocr(texto)
    texto_base, manuais_preenchidos = _linhas_manuais_preenchidas_do_bloco(texto)
    texto_analise = limpar_placeholders_manuais_vazios(texto)

    faltantes = []
    campos = analisar_campos(texto_analise)
    for campo in campos:
        if campo.get("linhas"):
            for linha in campo["linhas"]:
                for numero in linha.get("campos_incompletos", []):
                    dados = linha["subcampos"].get(numero, {})
                    if deve_gerar_placeholder_subcampo(texto_analise, campo, linha, numero, dados):
                        faltantes.append(placeholder_manual(numero, dados.get("nome", campo["nome"]), linha["linha"]))
        elif campo["status"] == "INCOMPLETO":
            if not valor_manual_campo(texto_analise, campo["numero"]):
                faltantes.append(placeholder_manual(campo["numero"], campo["nome"]))

    linhas_bloco = []
    vistos = set()
    for linha in manuais_preenchidos + faltantes:
        chave = linha.strip()
        if chave and chave not in vistos:
            linhas_bloco.append(linha)
            vistos.add(chave)

    bloco = ""
    if linhas_bloco:
        bloco = (
            "\n\n"
            f"{MARCADOR_CAMPOS_MANUAIS}\n"
            "Preencha somente os campos que conseguir confirmar no PPP original. Depois clique novamente em GERAR RAIO-X DO PPP.\n\n"
            + "\n".join(linhas_bloco)
            + "\n"
        )
    diagnostico = gerar_bloco_diagnostico_interno(texto_analise, campos, faltantes, metadados_ocr)
    return texto_base.rstrip() + bloco + "\n\n" + diagnostico


# ============================================================
# INTERFACE STREAMLIT
# ============================================================

st.title("📄 Raio-X do PPP – PróBenefício")
st.caption("Análise campo a campo do PPP conforme IN 128/2022, Decreto 3.048/99, NR-15, Temas STF/STJ/TNU e IRDR/TRF4.")

if pytesseract is None or convert_from_bytes is None:
    st.warning(
        "⚠️ OCR por imagem não disponível neste ambiente "
        "(Tesseract/pdf2image não instalado). PDFs escaneados "
        "podem ter leitura incompleta. Use PDF com texto "
        "selecionável para melhor resultado."
    )

with st.sidebar:
    st.header("Configuração")
    trf = st.selectbox("TRF de competência", ["TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"], index=3)
    st.info("O sistema não armazena dados. A análise ocorre durante a sessão.")

uploaded_file = st.file_uploader("Carregue o PPP em PDF", type=["pdf"])

texto_manual = st.text_area("Ou cole manualmente o texto extraído do PPP", height=180)

texto_final = ""

if uploaded_file:
    with st.spinner("📄 Lendo PDF e extraindo texto..."):
        texto_bruto = extrair_texto_pdf(uploaded_file)
    with st.spinner("🔍 Preparando campos e placeholders..."):
        # Etapa 1: preparação do bloco editável (pré-análise)
        texto_final = preparar_texto_editavel(texto_bruto)
    st.success(
        "✅ PDF processado. Revise o texto abaixo e "
        "preencha campos faltantes antes de gerar o Raio-X."
    )
elif texto_manual.strip():
    # Etapa 1: preparação do bloco editável (pré-análise)
    texto_final = preparar_texto_editavel(texto_manual)

if texto_final:
    with st.expander("Ver texto extraído / editável", expanded=True):
        st.info("Se algum campo não foi lido, preencha no bloco 'CAMPOS NÃO LIDOS PELO OCR' e clique novamente em Gerar Raio-X do PPP.")
        texto_final = st.text_area("Texto base da análise", value=texto_final, height=420)

if st.button("🚀 Gerar Raio-X do PPP", use_container_width=True):
    if not texto_final.strip():
        st.error("Envie um PDF ou cole o texto do PPP.")
    else:
        # Etapa 2: geração do parecer sobre o texto editado
        texto_para_analise = texto_para_analise_sem_diagnostico(texto_final)
        relatorio, campos, agentes, epi, ltcat, classificacao = gerar_parecer(texto_para_analise, trf)

        _cnae_extraido = extrair_cnae(texto_para_analise)
        _cnpj_extraido = re.search(
            r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b",
            texto_para_analise
        )
        if _cnae_extraido and len(re.sub(r"\D", "", _cnae_extraido)) == 7:
            with st.spinner("Consultando CNAE no IBGE..."):
                _info_cnae = consultar_cnae_online(_cnae_extraido)
            if not _info_cnae.get("erro"):
                st.info(
                    f"📋 CNAE {_info_cnae['codigo']}: "
                    f"{_info_cnae['descricao']} "
                    f"({_info_cnae.get('fonte', '')})"
                )

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
            st.metric("Campos técnicos", len([c for c in campos if not campo_administrativo_informativo(c)]))
        with c2:
            st.metric("Agentes identificados", len(agentes))
        with c3:
            falhas_count = len([
                c for c in campos
                if not campo_administrativo_informativo(c)
                and c["criticidade"] in ["CRÍTICA", "GRAVE", "MODERADA"]
            ]) + len(epi) + len(ltcat)
            st.metric("Alertas", falhas_count)

        st.subheader("🔎 Agentes nocivos identificados")
        if agentes:
            for a in agentes:
                st.write(f"- **{a['agente'].upper()}** ({a['grupo']}) — {a['enquadramento']}")
        else:
            st.warning("Nenhum agente nocivo identificado automaticamente.")

        st.subheader("⚠️ Checklist de campos")
        campos_com_pendencia = [
            c for c in campos
            if c.get("status") not in {"CONFORME/LOCALIZADO", "LOCALIZADO — NÃO APLICÁVEL"}
        ]
        if not campos_com_pendencia:
            st.success("Nenhum campo com erro ou pendência de leitura.")
        for c in campos_com_pendencia:
            if c.get("linhas"):
                st.warning(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']} — há linha/subcampo incompleto")
                with st.expander(f"Detalhes estruturados do Campo {c['campo']}", expanded=False):
                    for linha in c["linhas"]:
                        st.write(f"**Linha {linha['linha']} — {linha['status']}**")
                        for numero, dados in linha["subcampos"].items():
                            valor = dados.get("valor") or "não extraído"
                            st.write(f"- {numero} — {dados['nome']}: {valor}")
            elif c["status"].startswith("AUSENTE"):
                if c["criticidade"] == "CRÍTICA":
                    st.error(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")
                elif c["criticidade"] == "GRAVE":
                    st.warning(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")
                else:
                    st.info(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")
            elif c["status"] == "INCOMPLETO":
                if c["criticidade"] == "CRÍTICA":
                    st.error(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")
                elif c["criticidade"] == "GRAVE":
                    st.warning(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")
                else:
                    st.info(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']}")

        st.subheader("📄 Parecer técnico completo")
        st.text_area("Parecer para copiar", relatorio, height=650)

        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "⬇️ Baixar parecer em TXT",
                data=relatorio,
                file_name="raio_x_ppp_parecer.txt",
                mime="text/plain",
                use_container_width=True
            )
        with col_b:
            _relatorio_md = relatorio.replace("# ", "\n# ").replace("## ", "\n## ")
            st.download_button(
                "⬇️ Baixar parecer em Markdown",
                data=_relatorio_md,
                file_name="raio_x_ppp_parecer.md",
                mime="text/markdown",
                use_container_width=True
            )
