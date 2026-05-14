import streamlit as st

st.set_page_config(page_title="Raio-X PPP - PróBenefício", layout="wide")

st.title("📄 Raio-X do PPP - PróBenefício")

st.write("Faça o upload do PPP para análise completa.")

uploaded_file = st.file_uploader("Carregue o PDF do PPP", type=["pdf"])

if uploaded_file:
    st.success("Arquivo carregado com sucesso!")

    texto_exemplo = """
    PPP analisado conforme legislação previdenciária vigente.

    - Verificação de agentes nocivos
    - Análise de ruído conforme NR-15 e Decreto 3.048/99
    - Verificação de EPI
    - Identificação de falhas técnicas

    POSSÍVEIS FALHAS:
    - Ausência de responsável técnico
    - Falta de metodologia de medição
    - PPP incompleto quanto ao EPI

    FUNDAMENTAÇÃO LEGAL:

    Decreto 3.048/99:
    Art. 68: A comprovação da efetiva exposição do segurado aos agentes nocivos será feita mediante formulário PPP emitido pela empresa com base em laudo técnico.

    Lei 8.213/91:
    Art. 57: A aposentadoria especial será devida ao segurado que tiver trabalhado sujeito a condições especiais que prejudiquem a saúde ou integridade física.

    CONCLUSÃO:
    Há indícios de irregularidades que podem ensejar reconhecimento de tempo especial.
    """

    st.subheader("📊 Resultado da Análise")
    st.text_area("Relatório", texto_exemplo, height=400)

    st.download_button(
        label="📥 Baixar relatório",
        data=texto_exemplo,
        file_name="relatorio_ppp.txt",
        mime="text/plain"
    )
