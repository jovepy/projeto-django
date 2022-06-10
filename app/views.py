from django.shortcuts import render
import pandas as pd
import numpy as np
import requests
from datetime import date, timedelta

def consult_historic():
    dates = pd.date_range(date.today()-timedelta(120), date.today(), freq='MS') 
    serie = pd.DataFrame()
    
    for DATE in dates:
    
    
        HISTORY   = 'inf_diario_fi_{}'.format(DATE.strftime('%Y%m'))
        
        try:
            url ='http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/{}.zip'.format(HISTORY)
            
            parcial = pd.read_csv(url, sep=';')  
            
            serie = pd.concat([serie, parcial], ignore_index=True,axis=0)
            
        except Exception as e: 
            print(e)
    serie = serie.groupby(['CNPJ_FUNDO','DT_COMPTC']).last()
    serie = serie.loc[serie['VL_PATRIM_LIQ'] >0]
    serie = serie.loc[serie['NR_COTST'] > 1500]
    serie = serie.loc[serie['TP_FUNDO'] == 'FI']
    return(serie)

def structure_data():
    df = consult_historic()

    df_estruturado = pd.DataFrame()
   
    for cnpj in df.index.get_level_values(0).drop_duplicates():
        if len(df.loc[cnpj]) >50:
            aux = df.loc[cnpj]
            aux = aux['VL_PATRIM_LIQ']/aux['NR_COTST']    
            
            df_estruturado = pd.concat([df_estruturado,
                                       pd.DataFrame(aux,columns=[cnpj])],
                                       axis=1)
            
    var_dia = df_estruturado.pct_change().fillna(0)
    var_acum = (1+var_dia).cumprod()-1
    
    var_longo = (1+var_dia).rolling(15).apply(np.prod).mean()-1
    std_longo = (1+var_dia).rolling(15).apply(np.prod).std()-1
   
    aux = pd.DataFrame(var_longo)
    aux = aux.loc[aux[0] > 0]
    cnpjs = list(aux.index)
    
    aux = pd.DataFrame(std_longo)
    aux = aux.loc[aux[0] <= aux[0].mean()]
    cnpjs = list(aux.index)
    var_dia = var_dia.T.loc[cnpjs].T
    var_longo = var_longo.T.loc[cnpjs].T
    
    CDI = 0.0095 #calcular cdi acumulado de 30 dias
   
    IS = ((var_longo - CDI)/ (std_longo)).dropna()
    IS = IS.sort_values().loc[IS>0]
    var_acum = var_acum.T.loc[IS.index].T    
    return (IS,var_acum) #somente retorna os com sharpe positivo


# Create your views here.
def home(request):
    return render(request, 'index.html')

def assessor(request):
    sharpe, historic = structure_data()
    data = {}
    data['CNPJ'] = list(sharpe.index())
    data['sharpe'] = list(sharpe.values[0])
    data['historic'] = (historic)
    return render(request, 'assessor.html', data)