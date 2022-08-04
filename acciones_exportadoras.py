# -*- coding: utf-8 -*-
"""
Created on Thu Jul 28 10:48:24 2022

@author: lauta
"""

import os

# cargar las variables de entorno
api_key = os.environ['API_EOD']
# Por seguridad, es mejor guardar las contraseñas y usuarios en las variables de entorno
bcch_user = os.environ['BCCH_USER']
bcch_pwd = os.environ['BCCH_PWD']

from eod import EodHistoricalData
from bcch import BancoCentralDeChile
import pandas as pd
import requests
import numpy as np

# Crear la instancia
client = EodHistoricalData(api_key)
client_bcch = BancoCentralDeChile(bcch_user, bcch_pwd)
# Datos referenciales al codigo
indice_mercado = 'SPIPSA.INDX'

def fundamental_caller(stock_ticker:str, filter_:str, delete_extras:bool=True, resample_:bool=False):
    """
    Solicitar los datos a la API EOD Historical data y dejarla lista para usar.
    Parameters
    ----------
    stock_ticker : str
        codigo acción junto a su exchange.
    filter_ : str
        Campos a solicitar en la solicitud.
    delete_extras : bool, optional
        Campos inncesarios para el analisis. The default is True.
    resample_ : bool, optional
        Remuestrar a una frecuencia de tiempo superior?. The default is False.
    Returns
    -------
    temp_ : pd.DataFrame
        Datos financieros fundamentales para la acción en una base TTM.
    """
    # solcitar los datos
    temp_ = pd.DataFrame(
        client.get_fundamental_equity(
            stock_ticker, 
            filter_=filter_
            )
        ).T[::-1]
    
    # borrar la moneda de la accion
    if delete_extras:
        temp_.drop('currency_symbol', axis=1, inplace=True)
        # borrar la fecha de subida del informe
        temp_.drop('filing_date', axis=1, inplace=True)
        
    # hacer del index la fecha
    temp_['date'] = pd.to_datetime(temp_['date'])
    temp_.set_index('date', inplace=True)
    
    # Todos los datos a numerico
    temp_ = temp_.apply(pd.to_numeric, errors='ignore')
    
    # calcular en base a TTM
    temp_ = temp_.rolling(window=4, min_periods=4).sum()
    
    if resample_:
        temp_ = temp_.resample('Y').sum()
    
    return temp_

def cleaner(serie:str, resam:str=None, operations:list=None):
    """
    Limpiar la serie proveniente del la APIy dejarla lista para ocupar

    Parameters
    ----------
    serie : str
        id de la serie macro a solicitar.
    resam : str
        frecuencia para el resampling.
    operation : list
        operación(es) para agregar los datos resampliandos.

    Returns
    -------
    pandas DataFrame
        serie lista para ocupar.

    """
    serie_ = pd.DataFrame(client_bcch.get_macro(serie=serie))
    serie_['value'] = pd.to_numeric(serie_['value'], errors='coerce')
    serie_['indexDateString'] = pd.to_datetime(serie_['indexDateString'], format='%d-%m-%Y')
    serie_.set_index('indexDateString', inplace=True)
    del serie_['statusCode']
    
    if resam is not None:
        if operations is not None:
            serie_ = serie_.resample(resam).agg(operations)
            # renombrar las columnas
            serie_.columns = ['_'.join(x) for x in serie_.columns]
            return serie_
        else:
            print('Ocupar ')
    else:
        return serie_
    
def beta_normalizer(data:dict, columna_tiempo:str='date'):
    """
    Normalizar los datos de precios para el instrumento solicitado
    Parameters
    ----------
    data : dict
        Precios del instrumento en base OHLCV.
    columna_tiempo : str, optional
        Nombre de columna de tiempo. The default is 'date'.
    Returns
    -------
    data : pd.Series
        Datos normalizados.
    """
    data = pd.DataFrame(data)
    # transformar a tiempo
    data[columna_tiempo] = pd.to_datetime(data[columna_tiempo])
    # incorporarlo como indice
    data.set_index(columna_tiempo, inplace=True)
    return data
    
#%% Filtrar por las acciones expuestas a los sectores exportadores

"""
                        count     cumperc
Alimentos           11638.844820   24.226723
Químicos             7618.352962   40.084631
Frutícola            6444.117625   53.498321
Litio                4032.777568   61.892709
Celulosa             3548.134698   69.278294
Forestal             3158.625687   75.853101
Hierro               2192.439177   80.416751
----------------------------------------------------
Bebidas              2166.643474   84.926706
Maquinaria           2124.928348   89.349830
Ind metálica         1321.550493   92.100690
Otros Industriales   1145.132740   94.484330
Oro                   846.254854   96.245844
Semillas              562.485613   97.416680
Molibdeno             483.855079   98.423844
Plata                 387.402982   99.230239
Sal                   164.182236   99.571991
Pesca                 147.696908   99.879428
Silvicola              57.924527  100.000000

Filtros:
    Mercados: mayores betas tienden a menores ROE (debil)
    Valorizaciones: PB menores tienden a mayores ROE (mediano)
    MAyores ROA, implican mayores ROE (fuerte)
    La deuda no tiene ninguna relación con el ROE (fuerte)
    Menores yields tienden (debilmente) a menores ROE
"""
# solicitar todas las empresas del mercado chileno
simbolos = pd.DataFrame(
    client.get_exchange_symbols(
        exchange='SN'
        )
    )

# 2. Filtrar solo por las que esten en CLP.
simbolos = simbolos[simbolos['Currency'] == 'CLP']

# Solicitar a cada empresa el sector en que se encuentra, para así
# caracterizar las industrias disponibles en la API
industrias_empresas = pd.DataFrame()
import time
import math
for row in range(simbolos.shape[0]):
    try:
        ind_ = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='General')['Industry']
        sec_ = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='General')['Sector']
        # parte de valorización
        ev_ebitda = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Valuation::EnterpriseValueEbitda')
        ev_rev = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Valuation::EnterpriseValueRevenue')
        pb = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Valuation::PriceBookMRQ')
        ps = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Valuation::PriceSalesTTM')
        pe = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Valuation::TrailingPE')
        # Highlights
        roe = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Highlights::ReturnOnEquityTTM')
        roa = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Highlights::ReturnOnAssetsTTM')
        # ROIC = NOPAT / Avergae Invested Capital = (EBIT*(1-tax)) / (Fixed Assets + Net Working Capital)
        inc_ = fundamental_caller(simbolos.iloc[row, 0] + ".SN", filter_='Financials::Income_Statement::quarterly')
        bs_ = fundamental_caller(simbolos.iloc[row, 0] + ".SN", filter_='Financials::Balance_Sheet::quarterly')
        taxes = (inc_['incomeTaxExpense'] / inc_['incomeBeforeTax'])[-4:].mean()
        if math.isnan(taxes):
            taxes = 0.27 # https://tradingeconomics.com/chile/corporate-tax-rate
        capital = (bs_.netWorkingCapital + bs_.nonCurrentAssetsTotal).rolling(window=4).mean()
        if (math.isnan(capital[-1])) & (sec_!='Financial Services'):
            capital = bs_.netInvestedCapital.rolling(window=4).mean()
            roic = ((inc_['incomeBeforeTax']*(1-taxes)) / capital)[-4:].mean()
            
        elif sec_=='Financial Services':
            roic = roe
        
        else:
            roic = ((inc_['incomeBeforeTax']*(1-taxes)) / capital)[-4:].mean()
        
        op_margin = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Highlights::OperatingMarginTTM')
        mkt_cap = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Highlights::MarketCapitalization')
        # parte de technicals
        beta = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='Technicals::Beta')
        # parte dividendos
        payout = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='SplitsDividends::PayoutRatio')
        fw_yield = client.get_fundamental_equity(simbolos.iloc[row, 0] + ".SN", filter_='SplitsDividends::ForwardAnnualDividendYield')
        new_row = pd.DataFrame([{
            'empresa':simbolos.iloc[row, 0] + ".SN", 
            'sector':sec_,
            'industria': ind_,
            'ev_ebitda': ev_ebitda,
            'ev_rev': ev_rev,
            'pb': pb,
            'ps': ps,
            'pe': pe,
            'roe':roe,
            'roa': roa,
            'roic':roic,
            'op_margin': op_margin,
            'mkt_cap': float(mkt_cap),
            'beta': float(beta),
            'payout': payout,
            'fw_yield': fw_yield,
                                 }])
        industrias_empresas = pd.concat([industrias_empresas, new_row]).reset_index(drop=True)
        print(f"{simbolos.iloc[row, 0] + '.SN'}")
    except:
        print(f"No se pudo para {simbolos.iloc[row, 0] + '.SN'}")
    time.sleep(2)
    
#%% Limpiando los datos
industrias_empresas.sort_values(by=['sector', 'industria'], inplace=True)
industrias_empresas.set_index('empresa', inplace=True)
# imputar NA en cada columna por la mediana de cada sector, si es el unico, medinana del mercado
sectors = industrias_empresas.sector.value_counts().index.to_list()
for sec in sectors:
    # solo columnas numericas
    temp_ = industrias_empresas[industrias_empresas['sector']==sec].select_dtypes(exclude = ['object'])
    temp_columns = temp_.columns
    # ir por cada columna llenada los NAs con la mediana
    for col in temp_columns:
        industrias_empresas[col].replace(
            to_replace=np.nan, 
            value=industrias_empresas[col].median(), 
            inplace=True
            )
    
    print(f"Listo el sector de {sec}")
    
#%% Agregando el wacc
# calculo de la tasa de retorno exigida al patrimonio
# retornos promedios anualizados del indice de mercado elegido
r_m = beta_normalizer(client.get_prices_eod(indice_mercado)).resample('M').mean().close.pct_change().dropna().mean()*100*12
# tasa libre de riesgo (bono chileno + spread empresas chilenas)
r_f = client.get_instrument_ta('US10Y.INDX', function='ema', period=20, filter_='last_ema') +\
    ( cleaner('F019.SPS.PBP.91.D').ewm(span=20).mean().iloc[-1, 0] / 100 ) # el spread esta en puntos base
# tasa de descuento para el patrimonio
# Discount rate = Cost of Equity = Risk Free Rate + (Levered Beta * Equity Risk Premium)
# calcular el wacc para accion del mercado chileno
industrias_empresas['wacc'] = (r_f + industrias_empresas['beta']*(r_m - r_f)) / 100 # volver a decimal 

#%% Agregando la tasa de crecimiento permanente

# PIB, volumen a precios del año anterior encadenado, referencia 2018 (miles de millones de pesos encadenados)
pib_ = cleaner('F032.PIB.FLU.R.CLP.EP18.Z.Z.0.T').pct_change().rolling(window=16).mean() * 4

# Ocupare el promedio a largo plazo de chile
import statsmodels.api as sm
# El autor del filtro recomienda 1600 para data trimestral
cycle, trend = sm.tsa.filters.hpfilter(pib_.dropna(), 1600)
# El último dato es el que importa
perpetual_growth_rate = trend[-1]

#%% Version Damodoran pb vs pb
industrias_empresas['mv_bv'] = (industrias_empresas['roic']-perpetual_growth_rate)/\
    (industrias_empresas['wacc']-perpetual_growth_rate)

industrias_empresas['roic_wacc'] = industrias_empresas['roic'] - industrias_empresas['wacc']
industrias_empresas['roe_r'] = industrias_empresas['roe'] - perpetual_growth_rate

#%% Graficando los resultados
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score
# Filtrar por las empresas del quintal 60 hacia arriba en market cap (3er quintil)
mkt_cap_filter = pd.to_numeric(industrias_empresas['mkt_cap'], errors='coerce').quantile(0.6)
# filtrar las empresas que tengan un roic mayor que la tasa permanente de retorno
empresas = industrias_empresas
# empresas = empresas[empresas['wacc']>perpetual_growth_rate]

empresas = empresas[empresas['mv_bv']<=10]
empresas = empresas[empresas['mkt_cap']>=mkt_cap_filter]


x = empresas.roic_wacc.values.flatten() * 100
y = empresas.mv_bv.values.flatten()

modelo = np.poly1d(np.polyfit(x, y, 1))
r_2 = r2_score(y, modelo(x))

fig, ax = plt.subplots(figsize=(10, 5))

ax.scatter(x, y, color='tab:blue')
ax.plot(x, modelo(x), color='tab:orange')
fig.suptitle('Relación entre MV/BV y el Spread del ROIC del mercado chileno', fontweight='bold')
plt.title('Se consideran empresas en el 4to y 5to quintil de cap. bursátil')
ax.set_ylabel('MV/BV')
ax.set_xlabel('ROIC - WACC (%)')
# limites de valorización
ax.axhline(y=np.median(y), color='tab:red', linestyle='dashed')
ax.axvline(x=np.median(x), color='tab:red', linestyle='dashed')
ax.fill_betweenx(y=np.linspace(np.median(y), np.max(y)), x1=np.min(x), x2=np.median(x), 
                 facecolor='tab:red', alpha=0.4, edgecolor="tab:red")
ax.fill_betweenx(y=np.linspace(np.min(y), np.median(y)), x1=np.median(x), x2=np.max(x), facecolor='tab:green', alpha=0.4)
ax.text(0.4, 0.8,  
         r"$R^{2} = $" + f"{round(r_2,2)}", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=24, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

# Graph source
ax.text(0.2, -0.17,  
         "Fuente: EOD Historical Data   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

# Empresas subvaloradas
subvaloradas = industrias_empresas[(industrias_empresas['roic_wacc']>=np.median(x)) & (industrias_empresas['mv_bv']<=np.median(y))].index.to_list()
print(f"Las empresas infravaloradas para el mercado chileno son: {subvaloradas}")