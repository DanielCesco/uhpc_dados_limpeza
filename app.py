import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

st.set_page_config(layout="wide", page_title="Sistema de Análise de Ensaios")

# Estilização Global
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border: 1px solid #4B515D; }
    .dataframe { font-size: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

st.title('🔬 Consolidação e Análise de Módulo de Elasticidade')

# 1. Upload de Arquivos
arquivos_carregados = st.file_uploader(
    label='Carregue os arquivos CSV dos ensaios:',
    type='csv',
    accept_multiple_files=True
)

resultados_gerais = []
dict_todos_dados = {}
nomes_amostras = {}

if arquivos_carregados:
    # --- PARÂMETROS DE ENGENHARIA ---
    st.markdown('<p class="big-font">⚙️ Parâmetros Globais</p>', unsafe_allow_html=True)
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        diam_cil = st.number_input('Diâmetro do CP (mm):', value=50.0)
        area = 3.14159265358979 * (diam_cil ** 2) / 4
    with c_p2:
        L0 = st.number_input('Comprimento Inicial L0 (mm):', value=50.0)

    # --- RENOMEAR AMOSTRAS (APELIDOS) ---
    st.divider()
    st.markdown('<p class="big-font">🏷️ Identificação das Amostras</p>', unsafe_allow_html=True)
    col_nomes = st.columns(3)
    for i, arquivo in enumerate(arquivos_carregados):
        col_idx = i % 3
        with col_nomes[col_idx]:
            nomes_amostras[arquivo.name] = st.text_input(
                f"Nome para {arquivo.name}:",
                value=f"CP-{i + 1}",
                key=f"rename_{arquivo.name}"
            )

    st.divider()

    # --- PROCESSAMENTO INDIVIDUAL ---
    for arquivo in arquivos_carregados:
        f_key = arquivo.name.replace(".", "_")
        nome_cp = nomes_amostras[arquivo.name]

        with st.expander(f"📄 Análise Detalhada: {nome_cp}", expanded=False):
            try:
                # Carregamento e Cálculos
                df_raw = pd.read_csv(arquivo, sep=';', decimal=',', thousands='.', skiprows=[1])
                df_raw.columns = df_raw.columns.str.strip()
                df_att = df_raw.copy()

                # Cálculos de Engenharia (Tensão e Deformações)
                df_att['Tensão (MPa)'] = abs((df_att['Ch3 (kgf)'] * 9.81) / area)
                df_att['def 1'] = abs(df_att['Ch1 (mm)'] / L0)
                df_att['def 2'] = abs(df_att['Ch2 (mm)'] / L0)
                df_att['def media'] = (df_att['def 1'] + df_att['def 2']) / 2

                # Seleção de Eixo X
                opcoes_x = {'Canal 1': 'def 1', 'Canal 2': 'def 2', 'Média': 'def media'}
                sel_label = st.selectbox(f'Base para cálculo do Módulo:', list(opcoes_x.keys()), index=2,
                                         key=f"sel_{f_key}")
                col_x_calc = opcoes_x[sel_label]

                t_max = df_att['Tensão (MPa)'].max()

                # SUA LÓGICA DE SLIDER (P2 e P1 baseado em y_p2 + 30% Tmax)
                idx_sug_p2 = (df_att['Tensão (MPa)'] - (t_max * 0.3)).abs().idxmin()
                idx_p2 = st.slider(f'Ponto P2:', 0, len(df_att) - 1, int(idx_sug_p2), key=f"slide_{f_key}")
                x_p2, y_p2 = df_att[col_x_calc].iloc[idx_p2], df_att['Tensão (MPa)'].iloc[idx_p2]

                idx_p1 = (df_att['Tensão (MPa)'] - (y_p2 + (t_max * 0.3))).abs().idxmin()
                t_p1, x_p1 = df_att['Tensão (MPa)'].iloc[idx_p1], df_att[col_x_calc].iloc[idx_p1]

                E = (t_p1 - y_p2) / (x_p1 - x_p2) if (x_p1 - x_p2) != 0 else 0

                # Métricas
                m1, m2 = st.columns(2)
                m1.metric("Módulo de Elasticidade", f"{E:,.2f} MPa")
                m2.metric("Tensão Máxima", f"{t_max:,.2f} MPa")

                # Gráfico Individual (Canais 1, 2 e Média)
                fig_ind = go.Figure()
                fig_ind.add_trace(go.Scatter(x=df_att['def 1'], y=df_att['Tensão (MPa)'], name='Canal 1',
                                             line=dict(color='#FF4B4B', width=1.2)))
                fig_ind.add_trace(go.Scatter(x=df_att['def 2'], y=df_att['Tensão (MPa)'], name='Canal 2',
                                             line=dict(color='#00CC96', width=1.2)))
                fig_ind.add_trace(go.Scatter(x=df_att['def media'], y=df_att['Tensão (MPa)'], name='Média',
                                             line=dict(color='white', width=2.5)))
                fig_ind.add_trace(go.Scatter(x=[x_p2, x_p1], y=[y_p2, t_p1], mode='lines+markers', name='Reta E',
                                             line=dict(color='yellow', width=4), marker=dict(size=10, symbol='circle')))

                fig_ind.update_layout(template='plotly_dark', height=400, title=f"Visualização: {nome_cp}")
                st.plotly_chart(fig_ind, use_container_width=True)

                # --- DATAFRAME INDIVIDUAL (O que estava faltando) ---
                st.write("### Dados Processados do Ensaio")
                df_att = df_att.drop(columns=['Scan','Data', 'Horário'])

                if st.button(label=f'Exibir dados de {nome_cp}', key=f"btn_{f_key}"):
                    st.dataframe(df_att, use_container_width=True)

                resultados_gerais.append({
                    "ID": nome_cp, "Original": arquivo.name, "Modulo": E, "Tmax": t_max,
                    "x1": x_p1, "y1": t_p1, "x2": x_p2, "y2": y_p2, "col_x": col_x_calc
                })
                dict_todos_dados[arquivo.name] = df_att
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

    # --- RELATÓRIOS FINAIS VERTICAIS ---
    if resultados_gerais:
        st.divider()
        st.markdown('<p class="big-font">📊 Relatórios Finais</p>', unsafe_allow_html=True)
        df_res = pd.DataFrame(resultados_gerais)

        # 1. Gráfico de Curvas Sobrepostas
        st.write("### Sobreposição de Curvas (Tensão x Deformação Média)")
        fig_global = go.Figure()
        for r in resultados_gerais:
            dg = dict_todos_dados[r['Original']]
            fig_global.add_trace(go.Scatter(x=dg['def media'], y=dg['Tensão (MPa)'], name=r['ID']))
        fig_global.update_layout(template='plotly_dark', height=500)
        st.plotly_chart(fig_global, use_container_width=True)

        st.divider()

        # 2. Ranking Módulo E (Barras Vermelhas)
        st.write("### Ranking do Módulo de Elasticidade (MPa)")
        fig_bar = px.bar(df_res, x='ID', y='Modulo', color='Modulo', text_auto='.2s', color_continuous_scale='Reds')
        fig_bar.update_layout(template='plotly_dark', height=500)
        st.plotly_chart(fig_bar, use_container_width=True)

        # --- EXCEL MESTRE (FOTO DA DIREITA) ---
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_res[['ID', 'Modulo', 'Tmax', 'Original']].to_excel(writer, sheet_name='Resumo', index=False)

            for r in resultados_gerais:
                sheet = r['ID'][:31]
                df_ex = dict_todos_dados[r['Original']]
                df_ex.to_excel(writer, sheet_name=sheet, index=False)
                ws = writer.sheets[sheet]

                # Dados auxiliares da reta
                ws.write('L1', 'X_Reta');
                ws.write('M1', 'Y_Reta')
                ws.write('L2', r['x2']);
                ws.write('L3', r['x1'])
                ws.write('M2', r['y2']);
                ws.write('M3', r['y1'])

                chart = writer.book.add_chart({'type': 'scatter', 'subtype': 'straight'})
                idx_x = df_ex.columns.get_loc(r['col_x'])
                idx_y = df_ex.columns.get_loc('Tensão (MPa)')

                chart.add_series({
                    'name': 'Curva',
                    'categories': [sheet, 1, idx_x, len(df_ex), idx_x],
                    'values': [sheet, 1, idx_y, len(df_ex), idx_y],
                    'line': {'color': '#D9D9D9', 'width': 1.5}
                })
                chart.add_series({
                    'name': f'Módulo E ({r["Modulo"]:.2f})',
                    'categories': [sheet, 1, 11, 2, 11],
                    'values': [sheet, 1, 12, 2, 12],
                    'line': {'color': 'red', 'width': 2},
                    'marker': {'type': 'circle', 'size': 6, 'fill': {'color': 'red'}, 'border': {'color': 'red'}}
                })
                chart.set_title({'name': f'Análise: {r["ID"]}'})
                chart.set_x_axis({'name': 'Deformação', 'major_gridlines': {'visible': True}})
                chart.set_y_axis({'name': 'Tensão (MPa)', 'major_gridlines': {'visible': True}})
                chart.set_chartarea({'border': {'none': True}})
                ws.insert_chart('O2', chart)

        st.download_button("📊 Baixar Excel Completo", buffer.getvalue(), "Relatorio_Final.xlsx")
