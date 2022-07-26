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
stock = 'SQM-B.SN'
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
stock_pe = stock_fundamentals['Valuation']['TrailingPE']
stock_forward_pe = stock_fundamentals['Valuation']['ForwardPE']
stock_ps = stock_fundamentals['Valuation']['PriceSalesTTM']
stock_ev_ebitda = stock_fundamentals['Valuation']['EnterpriseValueEbitda']
stock_yield = stock_fundamentals['Highlights']['DividendYield']
stock_peg = stock_fundamentals['Highlights']['PEGRatio']
stock_op_margin = stock_fundamentals['Highlights']['OperatingMarginTTM']
# Industria de la acción
stock_industry = stock_fundamentals['General']['Sector']

# Caso industry
industry_roe = []
industry_pb = []
industry_pe = []
industry_forward_pe = []
industry_ps = []
industry_ev_ebitda = []
industry_yield = []
industry_peg = []
industry_op_margin = []

# Caso mercado
mercado_roe = []
mercado_pb = []
mercado_pe = []
mercado_forward_pe = []
mercado_ps = []
mercado_ev_ebitda = []
mercado_yield = []
mercado_peg = []
mercado_op_margin = []

# iterar por cada accion para extraer los datos fundamentales del MERCADO
for stock_, _ in market_fundamentals.items():
    # Solo extraer compañias denominadas en pesos chilenos
    if market_fundamentals[stock_]['General']['CurrencyCode'] == 'CLP':
        mercado_roe.append(market_fundamentals[stock_]['Highlights']['ReturnOnEquityTTM'])
        mercado_pb.append(market_fundamentals[stock_]['Valuation']['PriceBookMRQ'])
        mercado_pe.append(market_fundamentals[stock_]['Valuation']['TrailingPE'])
        mercado_forward_pe.append(market_fundamentals[stock_]['Valuation']['ForwardPE'])
        mercado_ps.append(market_fundamentals[stock_]['Valuation']['PriceSalesTTM'])
        mercado_ev_ebitda.append(market_fundamentals[stock_]['Valuation']['EnterpriseValueEbitda'])
        mercado_yield.append(market_fundamentals[stock_]['Highlights']['DividendYield'])
        mercado_peg.append(market_fundamentals[stock_]['Highlights']['PEGRatio'])
        mercado_op_margin.append(market_fundamentals[stock_]['Highlights']['OperatingMarginTTM'])
        
# iterar por cada accion para extraer los datos fundamentales de la INDUSTRIA
for stock_, _ in market_fundamentals.items():
    # Solo extraer compañias denominadas en pesos chilenos
    if market_fundamentals[stock_]['General']['CurrencyCode'] == 'CLP':
        if market_fundamentals[stock_]['General']['Sector'] == stock_industry:
            industry_roe.append(market_fundamentals[stock_]['Highlights']['ReturnOnEquityTTM'])
            industry_pb.append(market_fundamentals[stock_]['Valuation']['PriceBookMRQ'])
            industry_pe.append(market_fundamentals[stock_]['Valuation']['TrailingPE'])
            industry_forward_pe.append(market_fundamentals[stock_]['Valuation']['ForwardPE'])
            industry_ps.append(market_fundamentals[stock_]['Valuation']['PriceSalesTTM'])
            industry_ev_ebitda.append(market_fundamentals[stock_]['Valuation']['EnterpriseValueEbitda'])
            industry_yield.append(market_fundamentals[stock_]['Highlights']['DividendYield'])
            industry_peg.append(market_fundamentals[stock_]['Highlights']['PEGRatio'])
            industry_op_margin.append(market_fundamentals[stock_]['Highlights']['OperatingMarginTTM'])
            
        
precios_indice_mercado = cleaner_macro_valorizacion(indice_mercado).dropna()

#%% Paso 1: margenes operacionales antes de impuestos (EBITDA margin)

ebitda = inc_['netIncome'] + inc_['depreciationAndAmortization'] +\
    inc_['interestExpense'] + inc_['incomeTaxExpense']

ebitda_margin = (ebitda / inc_['totalRevenue']).mean()

#%% Paso 2: Estimar la tasa de costo de capital
import fredpy as fp
fp.api_key = os.environ['API_FRED']

beta_estadistico = stock_fundamentals['Technicals']['Beta']
# retornos mensuales anualizados
r_e = float(
    precios_indice_mercado.resample('M').mean().pct_change().dropna().mean().values * 12
    )
# Bono de gobierno a 10 años - EE.UU. | Dias de trading 250
r_f_us = float(cleaner_macro_valorizacion('F019.TBG.TAS.10.D').dropna().rolling(window=250).mean().iloc[-1]) / 100
# Expectativas de inflación en 11 meses (variación 12 meses, mediana)
exp_inf_cl = float(cleaner_macro_valorizacion('F089.IPC.V12.14.M').iloc[-1]) / 100
# 1-Year Expected Inflation -> https://fred.stlouisfed.org/series/EXPINF1YR
exp_inf_us = float(fp.series('EXPINF1YR').data.iloc[-1]) / 100

# Tasa libre de riesgo local transformada
# pagina 159 libro damodoran
r_f = ((1+r_f_us) * ((1+exp_inf_cl) / (1+exp_inf_us))) - 1

equity_risk_premium = r_e - r_f

cost_of_equity = r_f + beta_estadistico * equity_risk_premium

total_debt = (bs_['shortTermDebt'] + bs_['longTermDebt'])[-1]
total_equity_ = bs_['totalStockholderEquity'][-1]
de = total_debt / total_equity_

# Calculado el costo de capital para la firma
# Spread EMBI Chile (promedio, puntos base)
spread_chile = float(cleaner_macro_valorizacion('F019.SPS.PBP.91.D').dropna().rolling(window=250).mean().iloc[-1]) / 10000
cost_of_debt = r_f + spread_chile
cost_of_capital = cost_of_equity * (1 - de) + cost_of_debt * (1-tasa_impuestos) * de

#%% Paso 3: Estimar la tasa de reinversión
# Calculando el ROC
# https://www.youtube.com/watch?v=c5iigcEppZw&t=82s
# https://research-doc.credit-suisse.com/docView?language=ENG&format=PDF&sourceid=csplusresearchcp&document_id=806230540&serialid=dBve3cH%2BHSFm1zoXnWVgkwZUHD2g0c1RqyUyHTE3o%2BM%3D&cspId=null
nopat = inc_['ebit'] * (1-tasa_impuestos)
invested_capital = (bs_['netReceivables'] + bs_['inventory'] - bs_['accountsPayable']) +\
    bs_['propertyPlantAndEquipmentNet'] + bs_['goodWill'] + bs_['otherAssets']
    
roc = np.mean(nopat / invested_capital)

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
        available_shares = max(available_shares, available_shares_)
        del available_shares_
except:
    available_shares = client.get_fundamental_equity(stock, filter_='SharesStats::SharesOutstanding')

cash = bs_['cashAndEquivalents'][-1]
non_op_assets = bs_['otherAssets'][-1]
# https://www.investopedia.com/terms/n/noncontrolling_interest.asp#:~:text=Key%20Takeaways-,A%20non%2Dcontrolling%20interest%2C%20also%20known%20as%20a%20minority%20interest,decisions%20or%20votes%20by%20themselves.
minority_interest = bs_['noncontrollingInterestInConsolidatedEntity'][-1]

value_per_share = (value_op_assets + cash + non_op_assets - total_debt - minority_interest) / available_shares

# Transformando a CLP si es que el balance está en dolares
if stock_fundamentals['Financials']['Income_Statement']['currency_symbol'] == 'USD':
    # solicitar datos del tipo de cambio oficial -> Promedio mensual movil
    usdclp = price_normalizer(
        client.get_prices_eod('USDCLP.FOREX')
        ).close.rolling(
            window=20
            ).median()[-1]
    value_per_share_clp = usdclp * value_per_share

#%% Tests

precio_mercado_accion = price_normalizer(
    client.get_prices_eod(stock)
    ).close.iloc[-1]

if stock_fundamentals['Financials']['Income_Statement']['currency_symbol'] == 'USD':
    if value_per_share_clp > precio_mercado_accion:
        print(f"{stock_fundamentals['General']['Name']} cotiza por DEBAJO de la estimación de valor ({porcentaje_accion(value_per_share_clp, precio_mercado_accion)}%)")
    else:
        print(f"{stock_fundamentals['General']['Name']} cotiza por SOBRE de la estimación de valor ({porcentaje_accion(precio_mercado_accion, value_per_share_clp)}%)")
        
    valor_instrinsico = value_per_share_clp

else:
    if value_per_share > precio_mercado_accion:
        print(f"{stock_fundamentals['General']['Name']} cotiza por DEBAJO de la estimación de valor ({porcentaje_accion(value_per_share, precio_mercado_accion)}%)")
    else:
        print(f"{stock_fundamentals['General']['Name']} cotiza por SOBRE de la estimación de valor ({porcentaje_accion(precio_mercado_accion, value_per_share)}%)")
        
    valor_instrinsico = value_per_share


#%% Graficos
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Grafico del DCF
# Extraer la moneda de la accion
nombre_moneda = client.get_fundamental_equity(stock, filter_='General::CurrencyName')
codigo_moneda = client.get_fundamental_equity(stock, filter_='General::CurrencyCode')

# ratings de Wall Street
try:
    wall_street_price = stock_fundamentals['Highlights']['WallStreetTargetPrice']
except:
    wall_street_price = 0
    
# Analistas
try:
    analyst_target = stock_fundamentals['AnalystRatings']['TargetPrice']
except:
    analyst_target = 0
    
# Grafico de valorización y analisis de sensibilidad
fig, ax = plt.subplots(figsize=(10, 5))
estados = ('Precio\nactual', 'Valor\nIntrínseco', 'Wall\nStreet', 'Objetivo\nAnalistas')
y_pos = np.arange(len(estados))
precios = np.array([precio_mercado_accion, valor_instrinsico, wall_street_price, analyst_target])

ax.barh(y_pos, precios, align='center', color='black')
ax.set_yticks(y_pos, labels=estados)
ax.invert_yaxis()  # labels read top-to-bottom
ax.set_xlabel(f"{nombre_moneda} ({codigo_moneda})")

fig.suptitle('Precio actual vs Valor Intrínseco', fontweight='bold')
plt.title(f"¿Cuál es el valor intrínseco de {stock[:stock.index('.')]} al observar sus flujos de caja futuros?")

# Rangos de sensibilidad
# antes se evalua cual precio es mayor para el limite superior
if precio_mercado_accion > valor_instrinsico:
    precio_mayor = precio_mercado_accion
    precio_menor = valor_instrinsico
else:
    precio_mayor = valor_instrinsico
    precio_menor = precio_mercado_accion
    
# Subvalorado
ax.axvspan(0, valor_instrinsico*0.8, alpha=0.5, color='forestgreen')
# Valor justo
ax.axvspan(valor_instrinsico*0.8, valor_instrinsico*1.2, alpha=0.5, color='gold')
# Sobrevalorado
ax.axvspan(valor_instrinsico*1.2, precio_mayor*1.4, alpha=0.5, color='darkred')

# Graph source
ax.text(0.15, -0.12,  
         "Fuente: EOD Historical Data   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

ax.text(0.8, -0.12,  
         "Metologia: DCF por Aswath Damodaran", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black')

plt.show()

#  Bellow Fair Value
if precio_mercado_accion > valor_instrinsico * 1.2:
    print(f"{stock[:stock.index('.')]} ({codigo_moneda}${round(precio_mercado_accion, 2)}) cotiza por SOBRE mi estimación de valor justo ({codigo_moneda}${round(valor_instrinsico, 2)})")
elif (precio_mercado_accion >= valor_instrinsico * 0.8) & (precio_mercado_accion <= valor_instrinsico * 1.2):
    print(f"{stock[:stock.index('.')]} ({codigo_moneda}${round(precio_mercado_accion, 2)}) cotiza DENTRO de mi estimación de valor justo ({codigo_moneda}${round(valor_instrinsico, 2)})")
elif precio_mercado_accion < valor_instrinsico * 0.8:
    print(f"{stock[:stock.index('.')]} ({codigo_moneda}${round(precio_mercado_accion, 2)}) cotiza por DEBAJO de mi estimación de valor justo ({codigo_moneda}${round(valor_instrinsico, 2)})")

#%% Price to Earnings

# Trailing Price to Earnings
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(industry_pe, bins=21, color='dimgray')
ax.axvline(x=stock_pe, color='navy', linestyle='solid', linewidth=5)
ax.axvline(x=np.median(industry_pe), color='gold', linestyle='solid', linewidth=5)
# Subvalorado
ax.axvspan(np.min(industry_pe), np.median(industry_pe)*0.99, alpha=0.5, color='forestgreen')
# Sobrevalorado
ax.axvspan(np.median(industry_pe)*1.01, np.max(industry_pe), alpha=0.5, color='darkred')

fig.suptitle("Relación precio-beneficio (PE) vs el Sector", fontweight='bold')
plt.title(f"¿Cómo se compara el PE de {stock[:stock.index('.')]} vs con otras empresas del sector {stock_industry}?")
ax.set_ylabel('Número de compañias')

ax.text(0.15, -0.12,  
         "Fuente: End Of Day Historical data    Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

ax.text(0.7, -0.12,  
         "Azul = PE Compañia | Amarillo = Mediana sector", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black')

plt.show()

#%% Price to book

fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(mercado_pb, bins=21, color='dimgray')
ax.axvline(x=stock_pb, color='navy', linestyle='solid', linewidth=5)
ax.axvline(x=np.median(mercado_pb), color='gold', linestyle='solid', linewidth=5)
# Subvalorado
ax.axvspan(np.min(mercado_pb), np.median(mercado_pb)*0.99, alpha=0.5, color='forestgreen')
# Sobrevalorado
ax.axvspan(np.median(mercado_pb)*1.01, np.max(mercado_pb), alpha=0.5, color='darkred')

fig.suptitle("Relación precio-valor contable (PB) vs el Sector ", fontweight='bold')
plt.title(f"¿Cómo se compara el PB de {stock[:stock.index('.')]} vs con otras empresas del sector {stock_industry}?")
ax.set_ylabel('Número de compañias')

ax.text(0.15, -0.12,  
         "Fuente: End Of Day Historical data    Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

ax.text(0.7, -0.12,  
         "Azul = PE Compañia | Amarillo = Mediana sector", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black')

plt.show()

#%% Trailing Price to Sales
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(industry_ps, bins=21, color='dimgray')
ax.axvline(x=stock_ps, color='navy', linestyle='solid', linewidth=5)
ax.axvline(x=np.median(industry_ps), color='gold', linestyle='solid', linewidth=5)
# Subvalorado
ax.axvspan(np.min(industry_ps), np.median(industry_ps)*0.99, alpha=0.5, color='forestgreen')
# Sobrevalorado
ax.axvspan(np.median(industry_ps)*1.01, np.max(industry_ps), alpha=0.5, color='darkred')

fig.suptitle("Relación precio/ventas (PS) vs el Sector", fontweight='bold')
plt.title(f"¿Cómo se compara el PS de {stock[:stock.index('.')]} vs con otras empresas del sector {stock_industry}?")
ax.set_ylabel('Número de compañias')

ax.text(0.15, -0.12,  
         "Fuente: End Of Day Historical data    Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

ax.text(0.7, -0.12,  
         "Azul = PE Compañia | Amarillo = Mediana sector", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black')

plt.show()

#%% PEG

from matplotlib import cm

from matplotlib.patches import Circle, Wedge, Rectangle
def degree_range(n): 
    start = np.linspace(0,180,n+1, endpoint=True)[0:-1]
    end = np.linspace(0,180,n+1, endpoint=True)[1::]
    mid_points = start + ((end-start)/2.)
    return np.c_[start, end], mid_points

def rot_text(ang): 
    rotation = np.degrees(np.radians(ang) * np.pi / np.pi - np.radians(90))
    return rotation

def gauge(labels=['BAJO','MEDIO','ALTO','MUY ALTO','EXTREMO'], \
          colors='jet_r', arrow=1, title='', fname=False): 
    
    """
    some sanity checks first
    
    """
    
    N = len(labels)
    
    if arrow > N: 
        raise Exception("\n\nThe category ({}) is greated than \
        the length\nof the labels ({})".format(arrow, N))
 
    
    """
    if colors is a string, we assume it's a matplotlib colormap
    and we discretize in N discrete colors 
    """
    
    if isinstance(colors, str):
        cmap = cm.get_cmap(colors, N)
        cmap = cmap(np.arange(N))
        colors = cmap[::-1,:].tolist()
    if isinstance(colors, list): 
        if len(colors) == N:
            colors = colors[::-1]
        else: 
            raise Exception("\n\nnumber of colors {} not equal \
            to number of categories{}\n".format(len(colors), N))

    """
    begins the plotting
    """
    
    fig, ax = plt.subplots()

    ang_range, mid_points = degree_range(N)

    labels = labels[::-1]
    
    """
    plots the sectors and the arcs
    """
    patches = []
    for ang, c in zip(ang_range, colors): 
        # sectors
        patches.append(Wedge((0.,0.), .4, *ang, facecolor='w', lw=2))
        # arcs
        patches.append(Wedge((0.,0.), .4, *ang, width=0.10, facecolor=c, lw=2, alpha=0.5))
    
    [ax.add_patch(p) for p in patches]

    
    """
    set the labels (e.g. 'LOW','MEDIUM',...)
    """

    for mid, lab in zip(mid_points, labels): 

        ax.text(0.35 * np.cos(np.radians(mid)), 0.35 * np.sin(np.radians(mid)), lab, \
            horizontalalignment='center', verticalalignment='center', fontsize=14, \
            fontweight='bold', rotation = rot_text(mid))

    """
    set the bottom banner and the title
    """
    r = Rectangle((-0.4,-0.1),0.8,0.1, facecolor='w', lw=2)
    ax.add_patch(r)
    
    ax.text(0, -0.05, title, horizontalalignment='center', \
         verticalalignment='center', fontsize=22, fontweight='bold')

    """
    plots the arrow now
    """
    
    pos = mid_points[abs(arrow - N)]
    
    ax.arrow(0, 0, 0.225 * np.cos(np.radians(pos)), 0.225 * np.sin(np.radians(pos)), \
                 width=0.04, head_width=0.09, head_length=0.1, fc='k', ec='k')
    
    ax.add_patch(Circle((0, 0), radius=0.02, facecolor='k'))
    ax.add_patch(Circle((0, 0), radius=0.01, facecolor='w', zorder=11))

    """
    removes frame and ticks, and makes axis equal and tight
    """
    
    ax.set_frame_on(False)
    ax.axes.set_xticks([])
    ax.axes.set_yticks([])
    ax.axis('equal')
    plt.tight_layout()
    if fname:
        fig.savefig(fname, dpi=200)
    
    
    # Graph source
    ax.text(0.3, 0.03,  
             "Fuente: End Of Day Historical data    Gráfico: Lautaro Parada", 
             horizontalalignment='center',
             verticalalignment='center', 
             transform=ax.transAxes, 
             fontsize=8, 
             color='black',
             bbox=dict(facecolor='tab:gray', alpha=0.5))
    
try:
    # https://www.investopedia.com/ask/answers/06/pegratioearningsgrowthrate.asp#:~:text=The%20price%2Fearnings%20to%20growth,by%20its%20percentage%20growth%20rate.
    # Eliminar los datos iniciales del TTM y luego calcular el promedio movil de 4 periodos (anual)
    eps_growth = inc_.drop(inc_[inc_.netIncome == 0].index).netIncome.pct_change().rolling(window=4).mean()[-1]
    peg = stock_pe / (eps_growth*100)
    # considerar la categoria del peg
    if peg > 0 and peg < 0.5:
        arrow_ = 1
    elif peg >= 0.5 and peg < 1:
        arrow_ = 2
    elif peg >= 1 and peg < 1.5:
        arrow_ = 3
    elif peg >= 1.5:
        arrow_ = 4
    # graficar 
    gauge(labels=['BAJO','MEDIO','ALTO','EXTREMO'], \
      colors=['#007A00','#0063BF','#FFCC00','#ED1C24'], arrow=arrow_, title=f"Ratio PEG para {stock[:stock.index('.')]}") 

except:
    print("No se pudo calcular el PEG")