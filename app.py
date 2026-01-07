# --- IMPORTAÇÃO DE BIBLIOTECAS ---
import pandas as pd  # O 'pd' é o padrão para o Pandas. Ele cria a estrutura de tabelas (DataFrames).
import streamlit as st  # Transforma o script Python em um Web App interativo.
import plotly.graph_objects as go  # Usado para gráficos complexos onde controlamos cada camada (traces).
import plotly.express as px  # Usado para gráficos rápidos e automáticos (como o de barras).
from io import BytesIO  # Cria um arquivo "fantasma" na memória RAM para gerar o Excel sem precisar salvar no HD.

# --- CONFIGURAÇÃO INICIAL DO SITE ---
# layout="wide": Faz o conteúdo ocupar toda a largura da tela, ideal para dashboards com muitos gráficos.
st.set_page_config(layout="wide", page_title="Sistema de Análise de Ensaios")

# --- CUSTOMIZAÇÃO VISUAL (CSS) ---
# st.markdown com unsafe_allow_html permite injetar estilos CSS para mudar o visual padrão do Streamlit.
st.markdown("""
    <style>
    .big-font { font-size:24px !important; font-weight: bold; } /* Cria uma classe de fonte grande */
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border: 1px solid #4B515D; } /* Estiliza os quadros de métricas */
    .dataframe { font-size: 12px !important; } /* Diminui a fonte das tabelas para caber mais dados */
    </style>
    """, unsafe_allow_html=True)

# Exibe o título principal na tela
st.title('🔬 Consolidação e Análise de Módulo de Elasticidade')

# --- 1. INTERFACE DE CARREGAMENTO ---
# accept_multiple_files=True: Permite que você selecione vários arquivos CSV de uma vez.
arquivos_carregados = st.file_uploader(
    label='Carregue os arquivos CSV dos ensaios:',
    type='csv',
    accept_multiple_files=True
)

# Inicialização de variáveis globais que guardam os dados de todos os arquivos processados
resultados_gerais = []  # Lista de dicionários para o resumo final.
dict_todos_dados = {}  # Dicionário que mapeia o nome do arquivo ao seu respectivo DataFrame.
nomes_amostras = {}  # Mapeia o nome do arquivo original ao "apelido" dado pelo usuário.

# Só executa o código abaixo se houver pelo menos um arquivo carregado
if arquivos_carregados:

    # --- 2. ENTRADA DE PARÂMETROS DE ENGENHARIA ---
    st.markdown('<p class="big-font">⚙️ Parâmetros Globais</p>', unsafe_allow_html=True)
    c_p1, c_p2 = st.columns(2)  # Divide a linha em duas colunas de mesma largura.

    with c_p1:
        # number_input: Campo numérico. O 'value' é o padrão inicial.
        diam_cil = st.number_input('Diâmetro do CP (mm):', value=50.0)
        # Cálculo da área da seção transversal. O Python usa ** para potência.
        area = 3.14159265358979 * (diam_cil ** 2) / 4

    with c_p2:
        L0 = st.number_input('Comprimento Inicial L0 (mm):', value=50.0)

    # st.divider(): Desenha uma linha horizontal para separar visualmente as seções.
    st.divider()
    st.markdown('<p class="big-font">🏷️ Identificação das Amostras</p>', unsafe_allow_html=True)

    # Cria 3 colunas para os campos de renomeação ficarem lado a lado.
    col_nomes = st.columns(3)

    # Loop 'enumerate' percorre a lista de arquivos e nos dá o índice 'i' e o objeto 'arquivo'.
    for i, arquivo in enumerate(arquivos_carregados):
        col_idx = i % 3  # Operador de resto (módulo) garante que o índice fique sempre entre 0 e 2.
        with col_nomes[col_idx]:
            # text_input: Campo para digitar o nome da amostra.
            # key: O Streamlit exige uma chave única para cada widget criado dentro de um loop.
            nomes_amostras[arquivo.name] = st.text_input(
                f"Nome para {arquivo.name}:",
                value=f"CP-{i + 1}",
                key=f"rename_{arquivo.name}"
            )

    st.divider()

    # --- 3. LOOP DE PROCESSAMENTO INDIVIDUAL ---
    for arquivo in arquivos_carregados:
        # replace(".", "_"): Previne erros de ID no Streamlit removendo pontos do nome.
        f_key = arquivo.name.replace(".", "_")
        nome_cp = nomes_amostras[arquivo.name]  # Busca o apelido definido no passo anterior.

        # expander: Cria uma caixa que abre e fecha. expanded=False deixa fechado por padrão.
        with st.expander(f"📄 Análise Detalhada: {nome_cp}", expanded=False):
            try:
                # pd.read_csv: Transforma o texto do CSV em uma tabela Pandas.
                # decimal=',': Converte a vírgula do arquivo para o ponto do Python (essencial para cálculos).
                # skiprows=[1]: Pula a segunda linha do arquivo (geralmente onde estão as unidades mm, kgf).
                df_raw = pd.read_csv(arquivo, sep=';', decimal=',', thousands='.', skiprows=[1])

                # .columns.str.strip(): Remove espaços em branco "fantasmas" no nome das colunas (ex: "Ch1 " vira "Ch1").
                df_raw.columns = df_raw.columns.str.strip()
                df_att = df_raw.copy()  # Cria uma cópia para não alterar os dados originais brutos.

                # --- CÁLCULOS TÉCNICOS ---
                # abs(): Garante que os valores sejam positivos (módulo).
                df_att['Tensão (MPa)'] = abs((df_att['Ch3 (kgf)'] * 9.81) / area)  # Força(kgf) -> Newton -> MPa
                df_att['def 1'] = abs(df_att['Ch1 (mm)'] / L0)  # Deformação específica canal 1
                df_att['def 2'] = abs(df_att['Ch2 (mm)'] / L0)  # Deformação específica canal 2
                # Média aritmética das deformações dos dois canais (sensores laterais).
                df_att['def media'] = (df_att['def 1'] + df_att['def 2']) / 2

                # st.selectbox: Menu de escolha. O usuário define qual coluna de deformação quer usar no gráfico.
                opcoes_x = {'Canal 1': 'def 1', 'Canal 2': 'def 2', 'Média': 'def media'}
                sel_label = st.selectbox(f'Base para cálculo do Módulo:', list(opcoes_x.keys()), index=2,
                                         key=f"sel_{f_key}")
                col_x_calc = opcoes_x[sel_label]  # Recupera o nome técnico da coluna escolhida.

                # .max(): Pega o maior valor de tensão para definir escalas e referências.
                t_max = df_att['Tensão (MPa)'].max()

                # --- LÓGICA DE LOCALIZAÇÃO DE PONTOS ---
                # .abs().idxmin(): Técnica para achar a linha (índice) cujo valor é o mais próximo de um alvo.
                # Alvo aqui: 30% da Tensão Máxima.
                idx_sug_p2 = (df_att['Tensão (MPa)'] - (t_max * 0.3)).abs().idxmin()

                # Slider para ajuste fino do ponto P2 (onde a fase elástica acaba).
                idx_p2 = st.slider(f'Ponto P2:', 0, len(df_att) - 1, int(idx_sug_p2), key=f"slide_{f_key}")

                # .iloc[idx]: "Localização por índice". Pega os valores X e Y exatos daquela linha.
                x_p2, y_p2 = df_att[col_x_calc].iloc[idx_p2], df_att['Tensão (MPa)'].iloc[idx_p2]

                # P1 é calculado automaticamente como sendo 30% da Tmax acima da tensão de P2.
                idx_p1 = (df_att['Tensão (MPa)'] - (y_p2 + (t_max * 0.3))).abs().idxmin()
                t_p1, x_p1 = df_att['Tensão (MPa)'].iloc[idx_p1], df_att[col_x_calc].iloc[idx_p1]

                # Cálculo final do Módulo (Coeficiente Angular da Reta).
                # Evita divisão por zero se os pontos forem iguais.
                E = (t_p1 - y_p2) / (x_p1 - x_p2) if (x_p1 - x_p2) != 0 else 0

                # metric: Widget que mostra um valor grande com um título pequeno em cima.
                m1, m2 = st.columns(2)
                m1.metric("Módulo de Elasticidade", f"{E:,.2f} MPa")
                m2.metric("Tensão Máxima", f"{t_max:,.2f} MPa")

                # --- CONSTRUÇÃO DO GRÁFICO ---
                fig_ind = go.Figure()  # Cria a "tela" em branco do gráfico.

                # add_trace: Adiciona uma camada de dados (uma linha ou pontos).
                # go.Scatter: Tipo de gráfico de dispersão/linha.
                fig_ind.add_trace(go.Scatter(x=df_att['def 1'], y=df_att['Tensão (MPa)'], name='Canal 1',
                                             line=dict(color='#FF4B4B', width=1.2)))
                fig_ind.add_trace(go.Scatter(x=df_att['def 2'], y=df_att['Tensão (MPa)'], name='Canal 2',
                                             line=dict(color='#00CC96', width=1.2)))
                fig_ind.add_trace(go.Scatter(x=df_att['def media'], y=df_att['Tensão (MPa)'], name='Média',
                                             line=dict(color='white', width=2.5)))

                # Reta E: Conecta os pontos P1 e P2 para mostrar visualmente a inclinação do cálculo.
                fig_ind.add_trace(go.Scatter(x=[x_p2, x_p1], y=[y_p2, t_p1], mode='lines+markers', name='Reta E',
                                             line=dict(color='yellow', width=4), marker=dict(size=10, symbol='circle')))

                # update_layout: Configura aspetos estéticos como título e tema escuro.
                fig_ind.update_layout(template='plotly_dark', height=400, title=f"Visualização: {nome_cp}")
                # st.plotly_chart: Renderiza o gráfico do Plotly no site do Streamlit.
                st.plotly_chart(fig_ind, use_container_width=True)

                # .drop(columns=[...]): Remove colunas desnecessárias para limpar a visualização da tabela.
                df_att_clean = df_att.drop(columns=['Scan', 'Data', 'Horário'])

                # 1. Cria uma linha com os valores máximos absolutos de cada coluna numérica
                # .abs(): Converte tudo para positivo antes de calcular (importante se houver deslocamentos negativos)
                # .max(numeric_only=True): Encontra o maior valor apenas nas colunas de números
                # .to_frame(): Transforma o resultado (que era uma lista vertical) em uma tabela
                # .T: 'Transpõe' a tabela, fazendo o que era coluna virar uma linha horizontal
                linha_maximos = df_att_clean.abs().max(numeric_only=True).to_frame().T

                # 2. Renomeia o índice (o 'nome' da linha) para que apareça escrito 'Valores Máximos' no lugar do número 0
                linha_maximos.index = ['Valores Máximos']

                # 3. Concatena (empilha) as duas tabelas: a linha de máximos entra no topo e o df_att_clean vem logo abaixo
                # O resultado df_csv_max é uma nova tabela com uma linha extra de destaque no começo
                df_csv_max = pd.concat([linha_maximos, df_att_clean])



                # st.button: Só executa o código indentado abaixo dele se for clicado.
                if st.button(label=f'Exibir dados de {nome_cp}', key=f"btn_{f_key}"):
                    st.dataframe(df_csv_max, use_container_width=True)

                # .append(): Adiciona os resultados deste CP à lista que será usada no ranking e Excel.
                resultados_gerais.append({
                    "ID": nome_cp, "Original": arquivo.name, "Modulo": E, "Tmax": t_max,
                    "x1": x_p1, "y1": t_p1, "x2": x_p2, "y2": y_p2, "col_x": col_x_calc
                })
                # Armazena o dataframe limpo em um dicionário para recuperar na hora de gerar o Excel.
                dict_todos_dados[arquivo.name] = df_att_clean

            except Exception as e:
                # Exibe uma mensagem de erro vermelha se algo falhar no processamento (ex: arquivo corrompido).
                st.error(f"Erro no processamento: {e}")

    # --- 4. RELATÓRIOS FINAIS (SÓ APARECEM SE HOUVER RESULTADOS) ---
    if resultados_gerais:
        st.divider()
        st.markdown('<p class="big-font">📊 Relatórios Finais</p>', unsafe_allow_html=True)
        # pd.DataFrame(lista): Transforma a lista de dicionários em uma tabela resumo.
        df_res = pd.DataFrame(resultados_gerais)

        st.write("### Sobreposição de Curvas (Tensão x Deformação Média)")
        fig_global = go.Figure()
        for r in resultados_gerais:
            dg = dict_todos_dados[r['Original']]
            fig_global.add_trace(go.Scatter(x=dg['def media'], y=dg['Tensão (MPa)'], name=r['ID']))
        fig_global.update_layout(template='plotly_dark', height=500)
        st.plotly_chart(fig_global, use_container_width=True)

        st.divider()

        st.write("### Ranking do Módulo de Elasticidade (MPa)")
        # px.bar: Forma simplificada de criar gráfico de barras.
        # color='Modulo': Faz as barras terem cores diferentes baseadas no valor.
        fig_bar = px.bar(df_res, x='ID', y='Modulo', color='Modulo', text_auto='.2s', color_continuous_scale='Reds')
        fig_bar.update_layout(template='plotly_dark', height=500)
        st.plotly_chart(fig_bar, use_container_width=True)

        # --- 5. GERAÇÃO DO EXCEL MESTRE ---
        buffer = BytesIO()  # "Arquivo" temporário.
        # pd.ExcelWriter: Inicia o motor do Excel (XlsxWriter).
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # sheet_name='Resumo': Cria a primeira aba com os dados globais.
            df_res[['ID', 'Modulo', 'Tmax', 'Original']].to_excel(writer, sheet_name='Resumo', index=False)

            for r in resultados_gerais:
                sheet = r['ID'][:31]  # O Excel limita o nome da aba a 31 caracteres.
                df_ex = dict_todos_dados[r['Original']]
                df_ex.to_excel(writer, sheet_name=sheet, index=False)
                ws = writer.sheets[sheet]  # Seleciona a aba para escrever coisas extras (gráficos).

                # ws.write: Escreve dados em células específicas (ex: L1, M1).
                ws.write('L1', 'X_Reta');
                ws.write('M1', 'Y_Reta')
                ws.write('L2', r['x2']);
                ws.write('L3', r['x1'])
                ws.write('M2', r['y2']);
                ws.write('M3', r['y1'])
                ws.write('K5', 'E')
                # ws.write_formula: Insere uma fórmula de cálculo real dentro da célula do Excel.
                ws.write_formula('L5', '=(M3-M2)/(L3-L2)')

                # add_chart: Cria um gráfico nativo do Excel.
                chart = writer.book.add_chart({'type': 'scatter', 'subtype': 'straight'})

                # .get_loc: Descobre em qual coluna (número) está a informação desejada.
                idx_x = df_ex.columns.get_loc(r['col_x'])
                idx_y = df_ex.columns.get_loc('Tensão (MPa)')

                # Configura a série de dados da curva completa.
                chart.add_series({
                    'name': 'Curva',
                    # categories: Eixo X [aba, linha_inicial, col, linha_final, col]
                    'categories': [sheet, 1, idx_x, len(df_ex), idx_x],
                    # values: Eixo Y
                    'values': [sheet, 1, idx_y, len(df_ex), idx_y],
                    'line': {'color': '#D9D9D9', 'width': 1.5}
                })
                # Configura a série de dados da reta vermelha do Módulo E.
                chart.add_series({
                    'name': f'Módulo E ({r["Modulo"]:.2f})',
                    'categories': [sheet, 1, 11, 2, 11],  # Referência à coluna L
                    'values': [sheet, 1, 12, 2, 12],  # Referência à coluna M
                    'line': {'color': 'red', 'width': 2},
                    'marker': {'type': 'circle', 'size': 6, 'fill': {'color': 'red'}, 'border': {'color': 'red'}}
                })

                # Configurações de títulos e eixos do gráfico do Excel.
                chart.set_title({'name': f'Análise: {r["ID"]}'})
                chart.set_x_axis({'name': 'Deformação', 'major_gridlines': {'visible': True}})
                chart.set_y_axis({'name': 'Tensão (MPa)', 'major_gridlines': {'visible': True}})
                chart.set_chartarea({'border': {'none': True}})
                # Insere o gráfico na aba do Excel na posição O2.
                ws.insert_chart('O2', chart)

        # st.download_button: Pega os dados binários do 'buffer' e oferece o download para o usuário.
        st.download_button("📊 Baixar Excel Completo", buffer.getvalue(), "Relatorio_Final.xlsx")
