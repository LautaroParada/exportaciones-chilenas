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
import warnings
import requests
warnings.filterwarnings('ignore')

# Creación de las instancias
client = EodHistoricalData(api_key)
client_bcch = BancoCentralDeChile(bcch_user, bcch_pwd)

# Datos referenciales para todo el script
stock = 'CMPC.SN'
commodity_referencia = 'LB.COMM' 
indice_mercado = 'SPIPSA.INDX' # IPSA
years_forecast = 5
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
for stock, _ in market_fundamentals.items():
    # Solo extraer compañias denominadas en pesos chilenos
    if market_fundamentals[stock]['General']['CurrencyCode'] == 'CLP':
        mercado_roe.append(market_fundamentals[stock]['Highlights']['ReturnOnEquityTTM'])
        
# Solicitando los precios del commodity asociado a la empresa
commodity_prices = price_normalizer(
    client.get_prices_eod(commodity_referencia)
    ).resample('Q').median()
        
