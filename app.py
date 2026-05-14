import streamlit as st
import re
import unicodedata
from datetime import datetime

st.set_page_config(page_title="Raio-X do PPP - PróBenefício", layout="wide")

# =========================
# BASE LEGAL COMPLETA
# =========================

BASE_LEGAL = {
    "ruido": {
        "tema_555_stf": """
TEMA 555 STF: O uso de EPI não descaracteriza automaticamente a especialidade em caso de ruído acima do limite legal.
        """,
        "tema_694_stj": """
TEMA 694 STJ:
- Até 05/03/1997: acima de 80 dB
- 06/03/1997 a 18/11/2003: acima de 90 dB
- Após 19/11/2003: acima de 85 dB
        """,
    },
    "geral": {
        "tema_534_stj": """
TEMA 534 STJ: A habitualidade não exige exposição contínua durante toda jornada.
        """
    }
}

# =========================
# FUNÇÕES BÁSICAS
# =========================

def normalizar_texto(texto):
    texto = texto.lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")

def limite_ruido(data):
    if not data:
        return 85
    if data <= datetime(1997, 3, 5):
        return 80
    elif data <= datetime(2003, 11, 18):
        return 90
    return 85

# =========================
# EXTRAÇÃO SIMPLES
# =========================

def extrair_dados(texto):
    texto_norm = normalizar_texto(texto)

    ruido = None
    match = re.search(r'(\d{2,3})\s*dB', texto)
    if match:
        ruido = int(match.group(1))

    tem_ruido = "ruido" in texto_norm

    return {
        "ruido": ruido,
        "tem_ruido": tem_ruido
    }

# =========================
# ANÁLISE
# =========================

def analisar(dados):
    resultado = []

    if dados["tem_ruido"]:
        limite = 85

        if dados["ruido"]:
            if dados["ruido"] > limite:
                resultado.append("Ruído acima do limite legal → Favorável")
            else:
                resultado.append("Ruído abaixo do limite → Risco de indeferimento")
        else:
            resultado.append("Ruído sem medição → Necessita prova")

    return resultado

# =========================
# FUNDAMENTAÇÃO
# =========================

def gerar_fundamentacao(dados):
    textos = []

    if dados["tem_ruido"]:
        textos.append(BASE_LEGAL["ruido"]["tema_555_stf"])
        textos.append(BASE_LEGAL["ruido"]["tema_694_stj"])

    textos.append(BASE_LEGAL["geral"]["tema_534_stj"])

    return "\n\n".join(textos)

# =========================
# INTERFACE
# =========================

st.title("📄 Raio-X do PPP – PróBenefício")

texto = st.text_area("Cole o PPP ou texto extraído:")

if st.button("🚀 Gerar Análise"):

    if not texto.strip():
        st.error("Cole o texto primeiro.")
    else:
        dados = extrair_dados(texto)
        resultado = analisar(dados)
        fundamentacao = gerar_fundamentacao(dados)

        st.subheader("Resultado")
        for r in resultado:
            st.write(r)

        st.subheader("Fundamentação Jurídica")
        st.write(fundamentacao)
