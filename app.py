

import pandas as pd
import streamlit as st
import plotly.graph_objects as go


st.set_page_config(layout="wide")


#mostrar tab com dados enviados, e mostrar os 2 tipos de gráficos :D

st.title('Visualização de dados ')
# carregando arquivo CSV
upload_arquivo_csv=st.file_uploader(
    label='Insira sua tabela no formato csv aqui:',
    type='csv'
)

if upload_arquivo_csv is not None:
    try:
        #fazendo com que o arquivo csv seja um dataframe legível (pandas)
        df_upload_arquivo_csv=pd.read_csv(upload_arquivo_csv,
                                          sep=';',#indicando para o pandas que o separador de colunas é ponto e virgula
                                          decimal = ',',#indicando para o pandas que o separador de decimais é virgula, mude ae
                                          thousands='.',#indica ao pandas que milhares se separa com ponto, muda ae pow
                                          skiprows=[1])#indicando par ao pandas que você deve ignorar a segunda linha do arquivo


        df_upload_arquivo_csv.columns=df_upload_arquivo_csv.columns.str.strip() #retirando espaços vazios das colunas


        st.success('Arquivo carregado com sucesso ! ') #exibindo mensagem de sucesso ao usuário
        st.write('As primeiras 10 linhas do seu arquivo a seguir:')
        st.dataframe(df_upload_arquivo_csv.head(10))#exibindo a tabela do arquivo CSV (apenas as 10 primeiras linhas)

        if st.button('Ver todo o arquivo csv'):

            st.dataframe(df_upload_arquivo_csv)

        colunas_excluir = st.multiselect('Selecione as colunas a serem excluídas', df_upload_arquivo_csv.columns,
                                         default=df_upload_arquivo_csv.columns[[0,4,5]].tolist())

        colunas_manter =[col for col in df_upload_arquivo_csv.columns if col not in colunas_excluir]

        st.write('Nova Tabela Atualizada: ')
        df_upl_csv_att = df_upload_arquivo_csv[colunas_manter]



        df_upl_csv_att['Ch3 (N)'] = df_upl_csv_att['Ch3 (kgf)']*9.81
        diam_cil = st.number_input('Digite o Valor do diâmetro do cilindro (mm) : ', value=50)
        ar_cil = 3.14159265358979*diam_cil**2/4
        st.write(f'A área do cilindro corresponde a {ar_cil:.2f} mm² ')
        df_upl_csv_att['Tensão de compressão (MPa)'] = abs(df_upl_csv_att['Ch3 (N)'] / ar_cil)
        compr_inicial = st.number_input('Digite o Valor do comprimento inicial do cilindro (mm) : ', value=50)
        def_1 = abs(df_upl_csv_att['Ch1 (mm)'] / compr_inicial)
        df_upl_csv_att.insert(1,'deformação 1 (mm)',def_1)
        def_2 = abs(df_upl_csv_att['Ch2 (mm)'] / compr_inicial)
        df_upl_csv_att.insert(3, 'deformação 2 (mm)', def_2)
        def_med = ((df_upl_csv_att['deformação 1 (mm)'] + df_upl_csv_att['deformação 2 (mm)']) / 2)

        df_upl_csv_att.insert(4, 'deformação media (mm)' ,def_med)




        linha_maximos= df_upl_csv_att.abs().max(numeric_only=True).to_frame().T
        linha_maximos.index = ['Valores Máximos']
        df_csv_max = pd.concat([linha_maximos,df_upl_csv_att])
        st.dataframe(df_csv_max, use_container_width=True)
        #
        # st.write('Plotando com Streamlit ')
        #
        # df_grafico_def1 = df_upl_csv_att[['Tensão de compressão (MPa)','deformação 1 (mm)']]
        # df_grafico_def1=df_grafico_def1.set_index('deformação 1 (mm)')
        # st.line_chart(df_grafico_def1)
        #
        # df_grafico_def2 = df_upl_csv_att[['Tensão de compressão (MPa)', 'deformação 2 (mm)']]
        # df_grafico_def2 = df_grafico_def2.set_index('deformação 2 (mm)')
        # st.line_chart(df_grafico_def2)

        st.write('Plotando com Plotly')
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_upl_csv_att['deformação 1 (mm)'].abs(),
            y=df_upl_csv_att['Tensão de compressão (MPa)'],
            mode = 'lines',
            name='Canal 1',
            line=dict(color='yellow')

         ))

        fig.add_trace(go.Scatter(
            x=df_upl_csv_att['deformação 2 (mm)'].abs(),
            y=df_upl_csv_att['Tensão de compressão (MPa)'],
            mode='lines',
            name='Canal 2',
            line=dict(color='orange')

        ))
        fig.add_trace(go.Scatter(
            x=df_upl_csv_att['deformação media (mm)'].abs(),
            y=df_upl_csv_att['Tensão de compressão (MPa)'],
            mode='lines',
            name='Canal 3',
            line=dict(color='blue'),
            visible = 'legendonly'

        ))



        fig.update_layout(
            title='Tensão vs Deformação (canal 1 e 2 ) ',
            xaxis_title = 'Deformação (mm)',
            yaxis_title = 'Tensão (MPa)',
            template = 'plotly_white'
        )
        st.plotly_chart(fig)

        fig1 = go.Figure()

        fig1.add_trace(go.Scatter(
            x=df_upl_csv_att['deformação media (mm)'].abs(),
            y=df_upl_csv_att['Tensão de compressão (MPa)'],
            mode='lines',
            name='Canal 3',
            line=dict(color='blue')

        ))

        fig1.update_layout(
            title='Tensão vs Deformação (Média) ',
            xaxis_title='Deformação (mm)',
            yaxis_title='Tensão (MPa)',
            template='plotly_white'
        )
        st.plotly_chart(fig1)
    except Exception as e:
        st.error(f'Erro ao carregar o arquivo {e}. Certifique-se que seja um arquivo CSV válido.')












