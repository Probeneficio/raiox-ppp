import streamlit as st
import re
import unicodedata
import requests
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
    "fumos_metalicos": {
        "grupo": "Químico",
        "termos": [
            "fumos metalicos", "fumos metálicos", "fumo metalico", "fumo metálico",
            "ferro", "manganes", "manganês", "silicio", "silício", "solda", "soldagem"
        ],
        "norma": "NR-15 Anexos 11, 12 e 13, conforme substância",
        "limite": "Avaliação conforme substância: quantitativa quando houver limite de tolerância; qualitativa quando aplicável",
        "metodologia": "LTCAT/laudo técnico com identificação da substância, forma de contato e metodologia de avaliação",
        "fundamento": (
            "NR-15: Anexos 11 e 12 tratam de agentes químicos quantitativos; Anexo 13 trata de agentes qualitativos. "
            "Para agentes químicos, a simples indicação de EPI eficaz no PPP não encerra a análise previdenciária."
        )
    },
    "poeiras": {
        "grupo": "Químico",
        "termos": ["poeira respiravel", "poeira respirável", "poeira total", "poeiras", "poeira"],
        "norma": "NR-15 Anexo 12 e normas técnicas aplicáveis",
        "limite": "Avaliação conforme composição da poeira e eventual presença de sílica",
        "metodologia": "Amostragem ambiental, fração respirável/total e metodologia compatível",
        "fundamento": "NR-15, Anexo 12: poeiras minerais exigem avaliação conforme composição, concentração e metodologia."
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
        "fundamento": "NR-15, Anexo 13: óleos minerais e hidrocarbonetos podem exigir análise qualitativa da exposição habitual."
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
    "fumos_metalicos": {
        "grupo": "Químico",
        "termos": [
            "fumos metalicos", "fumos metálicos", "fumo metalico", "fumo metálico",
            "ferro", "manganes", "manganês", "silicio", "silício", "solda", "soldagem"
        ],
        "norma": "NR-15 Anexos 11, 12 e 13, conforme substância",
        "limite": "Avaliação conforme substância: quantitativa quando houver limite de tolerância; qualitativa quando aplicável",
        "metodologia": "LTCAT/laudo técnico com identificação da substância, forma de contato e metodologia de avaliação",
        "fundamento": (
            "NR-15: Anexos 11 e 12 tratam de agentes químicos quantitativos; Anexo 13 trata de agentes qualitativos. "
            "Para agentes químicos, a simples indicação de EPI eficaz no PPP não encerra a análise previdenciária."
        )
    },
    "poeiras": {
        "grupo": "Químico",
        "termos": ["poeira respiravel", "poeira respirável", "poeira total", "poeiras", "poeira"],
        "norma": "NR-15 Anexo 12 e normas técnicas aplicáveis",
        "limite": "Avaliação conforme composição da poeira e eventual presença de sílica",
        "metodologia": "Amostragem ambiental, fração respirável/total e metodologia compatível",
        "fundamento": "NR-15, Anexo 12: poeiras minerais exigem avaliação conforme composição, concentração e metodologia."
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
        "fundamento": "NR-15, Anexo 13: óleos minerais e hidrocarbonetos podem exigir análise qualitativa da exposição habitual."
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
    manual = re.search(r"(?im)^\s*3\s*[-:]\s*CNAE\s*:\s*([0-9\-\s/\.]{5,20})\s*$", texto)
    if manual:
        return normalizar_codigo_cnae(manual.group(1))

    padroes = [
        r"(?:3\s*[-:]?\s*)?CNAE\s*[:\-]?\s*([0-9]{4}\s*[-]?\s*[0-9]\s*/\s*[0-9]{2})",
        r"CNAE[^0-9]{0,80}([0-9]{4}\s*[-]?\s*[0-9]\s*/\s*[0-9]{2})",
        r"\b([0-9]{4}\s*-\s*[0-9]\s*/\s*[0-9]{2})\b",
        r"\b([0-9]{5}\s*/\s*[0-9]{2})\b",
        r"\b([0-9]{4}\s+[0-9]\s+[0-9]{2})\b",
    ]
    for p in padroes:
        m = re.search(p, texto, flags=re.IGNORECASE)
        if m:
            return normalizar_codigo_cnae(m.group(1))

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

    cpfs = re.findall(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", texto)
    if cpfs:
        # normalmente o CPF do responsável vem depois do CPF do segurado
        dados["cpf"] = cpfs[-1]

    registros = re.findall(r"\b\d{3,6}/[A-Z]{2}\b", texto)
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
        m = re.search(p, texto, flags=re.IGNORECASE | re.DOTALL)
        if m:
            nome = re.sub(r"\s+", " ", m.group(1)).strip()
            nome = re.sub(r"^(Nome|do|profissional|legalmente|habilitado)\s+", "", nome, flags=re.IGNORECASE)
            dados["nome"] = nome
            break

    texto_norm = normalizar(texto)

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

    if (
        dados["cpf"]
        or dados["registro"]
        or dados["nome"]
        or dados["profissao"] != "não identificada claramente"
        or "crea" in texto_norm
        or "crm" in texto_norm
        or "engenheiro" in texto_norm
        or "medico do trabalho" in texto_norm
    ):
        dados["localizado"] = True

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
            "termos": ["prazo de validade", "certificado de aprovacao", "certificado de aprovação", "ca do mte", "ca"],
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

        if localizado:
            status = "LOCALIZADO"
            # Janela aproximada ao redor do primeiro termo encontrado
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

    # Acrescenta análise específica de campos compostos/tabelados.
    try:
        resultados.extend(analisar_campos_compostos_159_16(texto))
    except Exception as e:
        resultados.append({
            "campo": "15.9/16",
            "nome": "Campos compostos/tabelados",
            "status": "ERRO NA ANÁLISE COMPLEMENTAR",
            "criticidade": "MODERADA",
            "valor": "",
            "falha": f"Não foi possível analisar campos compostos automaticamente: {e}",
            "verificacao": "Conferir manualmente campos 15.9 e 16.",
            "fundamento": "IN 128/2022, arts. 284 e 285.",
            "estrategia": "Preencher manualmente as linhas ausentes no texto editável."
        })

    return resultados


def extrair_responsaveis_ambientais_linhas(texto):
    """
    Tenta estruturar as linhas do Campo 16:
    16.1 Período | 16.2 CPF/NIT | 16.3 Registro | 16.4 Nome.

    Aceita linhas incompletas, por exemplo:
    06/2008 | CPF vazio | CRM 4732 | Nome
    """
    texto = texto or ""
    linhas = [re.sub(r"\s+", " ", l).strip() for l in texto.splitlines() if l.strip()]
    responsaveis = []

    # Padrão principal: período, opcional CPF, registro CRM/CREA, nome
    padroes = [
        r"(?P<periodo>\d{2}/\d{4})\s+(?:(?P<cpf>\d{10,11})\s+)?(?P<registro>(?:CRM|CREA)\s*\.?\s*\d{2,6})\s+\|?\s*(?P<nome>[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s\.]{5,80})",
        r"(?P<periodo>\d{2}/\d{2}/\d{4}\s*a\s*\d{2}/\d{2}/\d{4})\s+(?:(?P<cpf>\d{10,11})\s+)?(?P<registro>(?:CRM|CREA)\s*\.?\s*\d{2,6})\s+\|?\s*(?P<nome>[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s\.]{5,80})",
        r"(?P<periodo>\d{2}/\d{2}/\d{4}\s+a\s+\d{2}/\d{2}/\d{4})\s+\|?(?P<cpf>\d{10,11})\s+(?P<registro>(?:CRM|CREA)\s*\.?\s*\d{2,6})\s+\|?\s*(?P<nome>[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç][A-Za-zÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç\s\.]{5,80})",
    ]

    texto_compacto = "\n".join(linhas)

    for p in padroes:
        for m in re.finditer(p, texto_compacto, flags=re.IGNORECASE):
            periodo = re.sub(r"\s+", " ", m.group("periodo")).strip()
            cpf = (m.groupdict().get("cpf") or "").strip()
            registro = re.sub(r"\s+", " ", m.group("registro")).strip()
            nome = re.sub(r"\s+", " ", m.group("nome")).strip()

            # Evita capturar cabeçalhos
            if "nome do profissional" in normalizar(nome):
                continue

            habilitacao = "não identificada claramente"
            reg_norm = normalizar(registro)
            if "crm" in reg_norm:
                habilitacao = "médico do trabalho"
            elif "crea" in reg_norm:
                habilitacao = "engenheiro de segurança do trabalho / engenheiro do trabalho"

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
        registros = re.findall(r"\b(?:CRM|CREA)\s*\.?\s*\d{2,6}\b", texto, flags=re.IGNORECASE)
        nomes = re.findall(r"(Dirceu\s+Francisco\s+de\s+Ara[uú]jo\s+Rodrigues|J[oô]natan\s+Ribeiro\s+Duarte|Jonatan\s+Ribeiro\s+Duarte)", texto, flags=re.IGNORECASE)
        periodos = re.findall(r"\b\d{2}/\d{4}\b|\b\d{2}/\d{2}/\d{4}\s*a\s*\d{2}/\d{2}/\d{4}\b", texto, flags=re.IGNORECASE)
        cpfs = re.findall(r"\b\d{10,11}\b", texto)

        max_len = max(len(registros), len(nomes), len(periodos), 1)
        for i in range(max_len):
            registro = registros[i] if i < len(registros) else ""
            nome = nomes[i] if i < len(nomes) else ""
            periodo = periodos[i] if i < len(periodos) else ""
            cpf = cpfs[i] if i < len(cpfs) else ""

            if registro or nome or periodo:
                habilitacao = "médico do trabalho" if "crm" in normalizar(registro) else (
                    "engenheiro de segurança do trabalho / engenheiro do trabalho" if "crea" in normalizar(registro) else "não identificada claramente"
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

    responsaveis = extrair_responsaveis_ambientais_linhas(texto)
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


def analisar_campos(texto):
    texto_norm = normalizar(texto)

    cnae = extrair_cnae(texto)
    data_admissao = extrair_data_admissao(texto) or valor_manual_campo(texto, "10")
    tipos_15_2 = extrair_tipo_15_2(texto)
    epc_15_6 = extrair_epc_15_6(texto)
    responsavel = extrair_responsavel_tecnico(texto)
    cpf_ou_nit = extrair_cpf_ou_nit(texto) or valor_manual_campo(texto, "6")
    campo9_valor = extrair_campo9_ctps_ou_esocial(texto) or valor_manual_campo(texto, "9")

    resultados = []

    for campo in CAMPOS_PPP:
        encontrado = possui(texto_norm, campo["termos"])
        valor_extraido = ""

        # Regras específicas para reduzir falsos ausentes
        if campo["campo"] == "3":
            if cnae:
                encontrado = True
                valor_extraido = cnae
        elif campo["campo"] == "6":
            if cpf_ou_nit:
                encontrado = True
                valor_extraido = cpf_ou_nit
        elif campo["campo"] == "9":
            if campo9_valor:
                encontrado = True
                valor_extraido = campo9_valor
        elif campo["campo"] == "10":
            if data_admissao:
                encontrado = True
                valor_extraido = data_admissao
        elif campo["campo"] == "15.2":
            if tipos_15_2:
                encontrado = True
                valor_extraido = ", ".join(tipos_15_2)
        elif campo["campo"] == "15.6":
            if epc_15_6:
                encontrado = True
                valor_extraido = ", ".join(epc_15_6)
        elif campo["campo"] == "16":
            if responsavel["localizado"]:
                encontrado = True
                partes = []
                if responsavel["nome"]:
                    partes.append(f"Nome: {responsavel['nome']}")
                if responsavel["cpf"]:
                    partes.append(f"CPF: {responsavel['cpf']}")
                if responsavel["registro"]:
                    partes.append(f"Registro: {responsavel['registro']}")
                if responsavel.get("profissao"):
                    partes.append(f"Habilitação: {responsavel['profissao']}")
                valor_extraido = " | ".join(partes) if partes else "Responsável técnico localizado"

        status = "CONFORME/LOCALIZADO" if encontrado else "AUSENTE OU NÃO LOCALIZADO AUTOMATICAMENTE"

        if not encontrado:
            resultados.append({
                "campo": campo["campo"],
                "nome": campo["nome"],
                "status": status,
                "criticidade": campo["criticidade"],
                "valor": "",
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
                "valor": valor_extraido,
                "falha": "",
                "verificacao": campo["verificacao"],
                "fundamento": campo["fundamento"],
                "estrategia": "Campo localizado. Ainda assim, recomenda-se conferência material da informação."
            })

    return resultados

def analisar_agentes(texto):
    """
    Identifica todos os agentes nocivos encontrados.
    Usa termos específicos e também fallback pelo campo 15.2 quando o PPP marca Físico/Químico/Biológico.
    """
    texto_norm = normalizar(texto)
    agentes = []

    for chave, info in AGENTES.items():
        termos_norm = [normalizar(t) for t in info.get("termos", [])]
        if any(t in texto_norm for t in termos_norm):
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
                    "Agente químico identificado no PPP. A análise deve considerar a substância/produto, composição, "
                    "forma de contato, habitualidade, FISPQ/LTCAT, metodologia e eficácia concreta do EPI."
                )
            elif "fisic" in grupo_norm:
                item["enquadramento"] = (
                    "Agente físico identificado no PPP. A análise depende do agente específico, da metodologia, "
                    "da habitualidade/permanência e, quando aplicável, da intensidade."
                )
            elif "biologic" in grupo_norm:
                item["enquadramento"] = (
                    "Agente biológico identificado no PPP. A análise é predominantemente qualitativa, considerando "
                    "risco ocupacional de contaminação e contato com pacientes, materiais ou ambientes contaminados."
                )

            agentes.append(item)

    tipos = extrair_tipo_15_2(texto)
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

    def add(titulo, texto):
        if not texto:
            return
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


def gerar_parecer(texto, trf):
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
    if cnae:
        linhas.append(f"- CNAE localizado: {cnae}")
    if data_admissao:
        linhas.append(f"- Data de admissão localizada: {data_admissao}")
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

    linhas.append("## 2. CHECKLIST DE CAMPOS OBRIGATÓRIOS")
    for c in campos:
        valor = f" | Valor: {c.get('valor')}" if c.get("valor") else ""
        linhas.append(f"- Campo {c['campo']} — {c['nome']}: {c['status']}{valor}")
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
    if bases_utilizadas:
        for titulo, fundamento in bases_utilizadas:
            linhas.append(f"### {titulo}")
            linhas.append(f"- {fundamento}")
            linhas.append("")

        for titulo, fundamento in bases_tribunal:
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
        return m.group(1).strip()
    return ""


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


def preparar_texto_editavel(texto):
    """
    Acrescenta ao fim do texto extraído um bloco com qualquer campo analisado
    que não tenha sido lido com valor suficiente. O usuário pode preencher
    manualmente e clicar de novo em Gerar Raio-X do PPP.
    """
    texto = texto or ""

    # Evita duplicar o bloco se o usuário reabrir ou reanalisar.
    if MARCADOR_CAMPOS_MANUAIS in texto:
        return texto

    faltantes = []
    for numero, descricao in CAMPOS_EDITAVEIS_ANALISE:
        if not campo_tem_valor(texto, numero, descricao):
            faltantes.append(f"{numero} - {descricao}: ")

    if not faltantes:
        return texto

    bloco = (
        "\n\n"
        f"{MARCADOR_CAMPOS_MANUAIS}\n"
        "Preencha somente os campos que conseguir confirmar no PPP original. Depois clique novamente em GERAR RAIO-X DO PPP.\n\n"
        + "\n".join(faltantes)
        + "\n"
    )

    return texto.rstrip() + bloco


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
        texto_final = preparar_texto_editavel(texto_final)
    st.success("PDF carregado e texto extraído. Revise e complete manualmente os campos faltantes, se necessário.")
elif texto_manual.strip():
    texto_final = preparar_texto_editavel(texto_manual)

if texto_final:
    with st.expander("Ver texto extraído / editável", expanded=True):
        st.info("Se algum campo não foi lido, preencha no bloco 'CAMPOS NÃO LIDOS PELO OCR' e clique novamente em Gerar Raio-X do PPP.")
        texto_final = st.text_area("Texto base da análise", value=texto_final, height=420)

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
            if c.get("valor"):
                st.success(f"Campo {c['campo']} — {c['nome']}: localizado — {c['valor']}")
            elif c["status"].startswith("AUSENTE"):
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
