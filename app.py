import streamlit as st
import pdfplumber
import pytesseract
from PIL import Image
import io

st.set_page_config(page_title="Raio-X PPP - PróBenefício", layout="wide")

st.title("📄 Raio-X do PPP - PróBenefício")
st.write("Faça o upload do PPP para análise completa.")

uploaded_file = st.file_uploader("Carregue o PDF do PPP", type=["pdf"])

# =========================
# FUNÇÃO OCR + TEXTO
# =========================
def extrair_texto_pdf(file):
    texto_total = ""

    try:
        with pdfplumber.open(file) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_total += texto + "\n"
                else:
                    imagem = pagina.to_image(resolution=300)
                    pil_img = imagem.original
                    texto_ocr = pytesseract.image_to_string(pil_img, lang="por")
                    texto_total += texto_ocr + "\n"
    except:
        texto_total = "Erro ao processar o PDF."

    return texto_total.lower()


# =========================
# ANÁLISE INTELIGENTE
# =========================
def analisar_ppp(texto):

    resultado = []

    # 🔊 RUÍDO
    if "ruído" in texto or "db" in texto:
        resultado.append("🔊 Agente físico RUÍDO identificado.")

        if "85" in texto or "86" in texto or "87" in texto:
            resultado.append("⚠️ Possível exposição acima de 85 dB → atividade especial após 2003.")

    # ☣️ QUÍMICOS
    if "hidrocarboneto" in texto or "óleo" in texto or "graxa" in texto:
        resultado.append("☣️ Agente químico identificado → potencial insalubridade.")

    # 🦠 BIOLÓGICOS
    if "vírus" in texto or "bactéria" in texto or "hospital" in texto:
        resultado.append("🦠 Agente biológico identificado → enquadramento especial provável.")

    # 🦺 EPI
    if "epi" in texto:
        if "eficaz" in texto:
            resultado.append("🦺 EPI declarado eficaz (necessita validação jurídica).")
        else:
            resultado.append("⚠️ EPI sem comprovação de eficácia.")

    else:
        resultado.append("❌ Ausência de informação sobre EPI.")

    # 📋 RESPONSÁVEL TÉCNICO
    if "engenheiro" not in texto and "médico do trabalho" not in texto:
        resultado.append("❌ Ausência de responsável técnico → PPP inválido juridicamente.")

    # 📊 LTCAT
    if "ltcat" not in texto:
        resultado.append("⚠️ LTCAT não identificado.")

    return resultado


# =========================
# GERA RELATÓRIO
# =========================
def gerar_relatorio(analise):

    relatorio = "📊 ANÁLISE TÉCNICA E JURÍDICA DO PPP\n\n"

    relatorio += "Base legal: Lei 8.213/91 (art. 57 e 58), Decreto 3.048/99 e normas regulamentadoras.\n\n"

    relatorio += "━━━━━━━━━━━━━━━━━━━━━━\n"
    relatorio += "🔎 RESULTADOS ENCONTRADOS\n"
    relatorio += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for item in analise:
        relatorio += f"- {item}\n"

    relatorio += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    relatorio += "⚖️ CONCLUSÃO JURÍDICA\n"
    relatorio += "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    if any("RUÍDO" in i for i in analise) or any("químico" in i.lower() for i in analise):
        relatorio += "👉 Há fortes indícios de atividade especial.\n"
    else:
        relatorio += "👉 Não foram identificados elementos suficientes de especialidade.\n"

    relatorio += "\n📌 O PPP pode ser contestado judicialmente em caso de inconsistências.\n"

    return relatorio


# =========================
# EXECUÇÃO
# =========================
if uploaded_file:

    st.success("Arquivo carregado com sucesso!")

    with st.spinner("Analisando PPP..."):

        texto = extrair_texto_pdf(uploaded_file)

        analise = analisar_ppp(texto)

        relatorio = gerar_relatorio(analise)

    st.subheader("📊 Resultado da Análise")

    st.text_area("Relatório", relatorio, height=400)
