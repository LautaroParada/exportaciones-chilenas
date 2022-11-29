# -*- coding: utf-8 -*-
"""
Created on Mon Nov 28 17:11:42 2022

@author: lauta
"""

import os

# Cargar mis claves para las APIs desde las variables de entorno.
bcch_user = os.environ['BCCH_USER']
bcch_pwd = os.environ['BCCH_PWD']
api_key = os.environ['API_EOD']

from bcch import BancoCentralDeChile
from eod import EodHistoricalData
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
import requests
warnings.filterwarnings('ignore')

# Creación de las instancias
client = EodHistoricalData(api_key)
client_bcch = BancoCentralDeChile(bcch_user, bcch_pwd)

"""
Empresas a valorar en el articulo
- Alimentos(salmon) -> BLUMAR O CAMANCHACA
- Quimicos y Litio -> SQM
- Fruticola -> HF
- Celulosa y Forestas -> CMPC
- Bebidas -> CONCHATORO
"""

# Datos referenciales para todo el script
stock = 'SQM.US'
indice_mercado = 'F013.IBC.IND.N.7.LAC.CL.CLP.BLO.D' # IPSA
tasa_impuestos = 0.27
exchange = stock[stock.index('.'):][1:] # extraer el exchange de la accion

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

def price_normalizer(data:dict, columna_tiempo:str='date'):
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

def valor_pte_flujos(flujos_proyectados:list, periodos:int, tasa_dcto:float):
    """
    Calculo del valor presente de una serie de datos
    Parameters
    ----------
    flujos_proyectados : list
        Flujos de caja libre proyectados para la accion.
    periodos : int
        Numero de años a proyectar el flujo de caja.
    Returns
    -------
    TYPE float
        Suma del valor presente de los flujos de caja proyectados.
    """
    ffc_proyectados = [ flujos_proyectados[i-1]/( (1+tasa_dcto)**i ) for i in range(1, periodos) ]
    return sum(ffc_proyectados)

def porcentaje_accion(ref1, ref2):
    return round(((ref1 - ref2) / ref2)*100, 2)

def cleaner_macro_valorizacion(serie:str, resam:str=None, operations:list=None):
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
    
def bulk_fundamental(market:str, offset:int, api_token:str=api_key, limit:int=500, timeout_:int=300):
    params = {
        'api_token':api_token,
        'fmt':'json',
        'limit': limit,
        'offset': offset}
    resp_ = requests.get(url=f"http://eodhistoricaldata.com/api/bulk-fundamentals/{market}",
                         params=params,
                         timeout=timeout_)
    if resp_.status_code == 200:
        return resp_.json()
    else:
        resp_.raise_for_status()
        
#%% Datos financieros fundamentales para los calculos

# considerar si tiene flujos de caja en dolares para
# transformarlos a CLP
stock_fundamentals = client.get_fundamental_equity(stock)
# Ingresos netos 
inc_ = fundamental_caller(stock, filter_='Financials::Income_Statement::quarterly').fillna(0)
# Flujos de caja   
cf_ = fundamental_caller(stock, filter_='Financials::Cash_Flow::quarterly').fillna(0)
# Balance. Debe ser dividido por 4, debido a que ya estan anualizado
bs_ = fundamental_caller(stock, filter_='Financials::Balance_Sheet::quarterly').fillna(0) / 4

# Solicitar los datos iniciales para el exchange
market_fundamentals = bulk_fundamental(market=exchange, offset=0)
# Extraer metricas utiles para el estudios
# Caso empresa
stock_roe = stock_fundamentals['Highlights']['ReturnOnEquityTTM']
stock_pb = stock_fundamentals['Valuation']['PriceBookMRQ']

# Caso mercado
mercado_roe = []
mercado_pb = []

# iterar por cada accion para extraer los datos fundamentales del mercado
for stock_, _ in market_fundamentals.items():
    # Solo extraer compañias denominadas en pesos chilenos
    if market_fundamentals[stock_]['General']['CurrencyCode'] == 'CLP':
        mercado_roe.append(market_fundamentals[stock_]['Highlights']['ReturnOnEquityTTM'])
        
precios_indice_mercado = cleaner_macro_valorizacion(indice_mercado).dropna()

#%% Paso 1: margenes operacionales antes de impuestos (EBITDA margin)

ebitda = inc_['netIncome'] + inc_['depreciationAndAmortization'] +\
    inc_['interestExpense'] + inc_['incomeTaxExpense']

ebitda_margin = (ebitda / inc_['totalRevenue']).mean()

#%% Paso 2: Estimar la tasa de costo de capital
import fredpy as fp
fp.api_key = '97314157aa982d413b0388ed05758cbb'

beta_estadistico = stock_fundamentals['Technicals']['Beta']
# retornos mensuales anualizados
r_e = float(
    precios_indice_mercado.resample('M').mean().pct_change().dropna().mean().values * 12
    )
# Bono de gobierno a 10 años - EE.UU.
r_f_us = float(cleaner_macro_valorizacion('F019.TBG.TAS.10.D').dropna().rolling(window=20).mean().iloc[-1]) / 100
# Expectativas de inflación en 11 meses (variación 12 meses, mediana)
exp_inf_cl = float(cleaner_macro_valorizacion('F089.IPC.V12.14.M').iloc[-1]) / 100
# 1-Year Expected Inflation -> https://fred.stlouisfed.org/series/EXPINF1YR
exp_inf_us = float(fp.series('EXPINF1YR').data.iloc[-1]) / 100

# Tasa libre de riesgo local transformada
# pagina 159 libro damodoran
r_f = ((1+r_f_us) * ((1+exp_inf_cl) / (1+exp_inf_us))) - 1

equity_risk_premium = r_e - r_f

cost_of_equity = r_f + beta_estadistico * equity_risk_premium

total_debt = (bs_['shortTermDebt'] + bs_['longTermDebt'] + bs_['shortLongTermDebt'])[-1]
total_equity_ = stock_fundamentals['Highlights']['MarketCapitalization']
de = total_debt / total_equity_

# Calculado el costo de capital para la firma
# Spread EMBI Chile (promedio, puntos base)
spread_chile = float(cleaner_macro_valorizacion('F019.SPS.PBP.91.D').dropna().rolling(window=20).mean().iloc[-1]) / 10000
cost_of_debt = r_f + spread_chile
cost_of_capital = cost_of_equity * (1 - de) + cost_of_debt * (1-tasa_impuestos) * de

#%% Paso 3: Estimar la tasa de reinversión
# Calculando el ROC
# https://www.youtube.com/watch?v=c5iigcEppZw&t=82s
# https://research-doc.credit-suisse.com/docView?language=ENG&format=PDF&sourceid=csplusresearchcp&document_id=806230540&serialid=dBve3cH%2BHSFm1zoXnWVgkwZUHD2g0c1RqyUyHTE3o%2BM%3D&cspId=null
nopat = inc_['ebit'] * (1-tasa_impuestos)
invested_capital = (bs_['netReceivables'] + bs_['inventory'] - bs_['accountsPayable']) +\
    bs_['propertyPlantAndEquipmentNet'] + bs_['goodWill'] + bs_['otherAssets']
    
roc = (nopat / invested_capital)[-1]


# Tasa de crecimiento perpetuo
# PIB, volumen a precios del año anterior encadenado, referencia 2018 (miles de millones de pesos encadenados)
pib_ = float(
    cleaner_macro_valorizacion('F032.PIB.FLU.R.CLP.EP18.Z.Z.0.T').pct_change().rolling(window=16).median().iloc[-1].values
    )

reinvested_rate = pib_ / roc

#%% Paso 4: calcular el valor de los activos operativos
# Calcular la proyeccion de ingresos operacionales normalizados 
normalized_op_income = ebitda_margin * inc_['totalRevenue'][-1]

value_op_assets = (normalized_op_income * (1+pib_)*(1-tasa_impuestos)*(1-reinvested_rate)) / (cost_of_capital - pib_)

#%% Paso 5: Valor por accion

# Calculo de las acciones circulantes

try:
    available_shares = client.get_fundamental_equity(stock, filter_='outstandingShares::quarterly')['0']['shares']
    available_shares_ = client.get_fundamental_equity(stock, filter_='SharesStats::SharesOutstanding')
    
    if available_shares > 0 and available_shares_ > 0:
        available_shares = min(available_shares, available_shares_)
        del available_shares_
except:
    available_shares = client.get_fundamental_equity(stock, filter_='SharesStats::SharesOutstanding')

cash = bs_['cashAndEquivalents'][-1]
non_op_assets = bs_['otherAssets'][-1]
# https://www.investopedia.com/terms/n/noncontrolling_interest.asp#:~:text=Key%20Takeaways-,A%20non%2Dcontrolling%20interest%2C%20also%20known%20as%20a%20minority%20interest,decisions%20or%20votes%20by%20themselves.
minority_interest = bs_['noncontrollingInterestInConsolidatedEntity'][-1]

value_per_share = (value_op_assets + cash + non_op_assets - total_debt - minority_interest) / available_shares

#%% Tests

precio_mercado_accion = price_normalizer(
    client.get_prices_eod(stock)
    ).close.iloc[-1]

if value_per_share > precio_mercado_accion:
    print(f"{stock_fundamentals['General']['Name']} cotiza por DEBAJO de la estimación de valor ({porcentaje_accion(value_per_share, precio_mercado_accion)}%)")
else:
    print(f"{stock_fundamentals['General']['Name']} cotiza por SOBRE de la estimación de valor ({porcentaje_accion(precio_mercado_accion, value_per_share)}%)")

