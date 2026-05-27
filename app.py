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
    campos = analisar_campos(texto)
    for campo in campos:
        if campo.get("linhas"):
            for linha in campo["linhas"]:
                for numero in linha.get("campos_incompletos", []):
                    dados = linha["subcampos"].get(numero, {})
                    faltantes.append(placeholder_manual(numero, dados.get("nome", campo["nome"]), linha["linha"]))
        elif campo["status"] == "INCOMPLETO":
            faltantes.append(placeholder_manual(campo["numero"], campo["nome"]))

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
            if c.get("linhas"):
                if c["status"] == "INCOMPLETO":
                    st.warning(f"Campo {c['campo']} — {c['nome']}: {c['criticidade']} — há linha/subcampo incompleto")
                else:
                    st.success(f"Campo {c['campo']} — {c['nome']}: localizado")
                with st.expander(f"Detalhes estruturados do Campo {c['campo']}", expanded=False):
                    for linha in c["linhas"]:
                        st.write(f"**Linha {linha['linha']} — {linha['status']}**")
                        for numero, dados in linha["subcampos"].items():
                            valor = dados.get("valor") or "não extraído"
                            st.write(f"- {numero} — {dados['nome']}: {valor}")
            elif c.get("valor"):
                st.success(f"Campo {c['campo']} — {c['nome']}: localizado — {c['valor']}")
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

        st.download_button(
            "⬇️ Baixar parecer em TXT",
            data=relatorio,
            file_name="raio_x_ppp_parecer.txt",
            mime="text/plain",
            use_container_width=True
        )
