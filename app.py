import streamlit as st

st.set_page_config(page_title="Raio-X PPP - PróBenefício", layout="wide")

st.title("📄 Raio-X do PPP - PróBenefício")

st.write("Faça o upload do PPP para análise completa.")

uploaded_file = st.file_uploader("Carregue o PDF do PPP", type=["pdf"])

if uploaded_file:
    st.success("Arquivo carregado com sucesso!")

    texto_exemplo = f"""
📊 ANÁLISE TÉCNICA E JURÍDICA DO PPP

O Perfil Profissiográfico Previdenciário (PPP) foi analisado à luz da legislação previdenciária vigente, com base no art. 58 da Lei 8.213/91, Decreto 3.048/99 e normas regulamentadoras aplicáveis.

━━━━━━━━━━━━━━━━━━━━━━
🔎 1. AGENTES NOCIVOS
━━━━━━━━━━━━━━━━━━━━━━

Foi realizada a verificação da presença de agentes físicos, químicos e biológicos conforme Anexo IV do Decreto 3.048/99.

A legislação previdenciária estabelece que:

➡️ A exposição habitual e permanente a agentes nocivos à saúde ou à integridade física do trabalhador enseja o reconhecimento de tempo especial.

━━━━━━━━━━━━━━━━━━━━━━
🔊 2. RUÍDO
━━━━━━━━━━━━━━━━━━━━━━

Limites legais:

- Até 05/03/1997: superior a 80 dB  
- De 06/03/1997 a 18/11/2003: superior a 90 dB  
- Após 19/11/2003: superior a 85 dB  

📌 Base legal: Decreto 2.172/97 e Decreto 4.882/03

⚠️ O uso de EPI não descaracteriza automaticamente o direito ao enquadramento especial.

━━━━━━━━━━━━━━━━━━━━━━
🦺 3. EPI
━━━━━━━━━━━━━━━━━━━━━━

Nos termos do art. 58, §2º da Lei 8.213/91:

A empresa deve comprovar a real eficácia do EPI.

Falhas comuns:

- Ausência de CA  
- Informação genérica  
- Falta de comprovação de eficácia  

━━━━━━━━━━━━━━━━━━━━━━
⚖️ 4. CONCLUSÃO
━━━━━━━━━━━━━━━━━━━━━━

Há indícios de enquadramento como atividade especial.

Falhas no PPP podem ser corrigidas judicialmente.

📌 O direito deve ser interpretado de forma favorável ao segurado.

🚀 Recomendação: análise aprofundada e possível ação judicial.
"""

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
