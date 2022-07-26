# -*- coding: utf-8 -*-
"""
Created on Mon Jul 25 11:28:38 2022

@author: lauta
"""

import os

from bcch import BancoCentralDeChile

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter

# Por seguridad, es mejor guardar las contraseñas y usuarios en las variables de entorno
bcch_user = os.environ['BCCH_USER']
bcch_pwd = os.environ['BCCH_PWD']

# Creación de la instancia
client = BancoCentralDeChile(bcch_user, bcch_pwd)

def cleaner(serie:str, rolling_:bool=True, window:int=12, operacion_:str='sum'):
    """
    Solicitar datos a la API del Banco central por medio del cliente
    bcch. Adicionamente se hacen operaciones para limpiar los datos.

    Parameters
    ----------
    serie : str
        codigo de la serie.
    rolling_ : bool, optional
        Seguimiento anual?. The default is True.
    window : int
        Numero de periodos para el calculo
    operacion_ : str, optional
        Operación para hacer el re-muestreo. The default is None.

    Returns
    -------
    serie_ : TYPE
        Datos historicos para la serie solicitada.

    """
    serie_ = pd.DataFrame(client.get_macro(serie=serie))
    serie_['value'] = pd.to_numeric(serie_['value'], errors='coerce')
    serie_['indexDateString'] = pd.to_datetime(serie_['indexDateString'], format='%d-%m-%Y')
    serie_.set_index('indexDateString', inplace=True)
    del serie_['statusCode']
    
    # casos posibles
    try:
        if (rolling_) & (operacion_ == 'sum'):
            serie_ = serie_.rolling(window=window).sum()
            return serie_
        
        elif (rolling_) & (operacion_ == 'mean'):
            serie_ = serie_.rolling(window=window).mean()
            return serie_
        else:
            return serie_
    except:
        print("Los unicos valores validos para la operacion son 'sum' y 'mean'")

#%% Exportaciones de los principales productos chilenos

# Solicitar los datos
exportaciones = cleaner('F068.B1.FLU.Z.0.C.N.Z.Z.Z.Z.6.0.M')
exp_mineras = cleaner('F068.B1.FLU.A.0.C.N.Z.Z.Z.Z.6.0.M')
exp_agro = cleaner('F068.B1.FLU.B.0.C.N.Z.Z.Z.Z.6.0.M')
exp_ind = cleaner('F068.B1.FLU.C.0.C.N.Z.Z.Z.Z.6.0.M')

# Unir todo
exportaciones = exportaciones.join(exp_mineras, rsuffix='_min').join(exp_agro, rsuffix='_agro').join(exp_ind, rsuffix='_ind')
# cambiar los nombres
exportaciones.columns = ['total_fob', 'Minería', 'Agropecuario', 'Industriales']

# Crear porcentajes de cada serie por cada mes
exportaciones_porcion = exportaciones.divide(exportaciones['total_fob'], axis=0) * 100

# Grafico pareto exportaciones totales
pareto_exportaciones = pd.DataFrame(
    data=exportaciones.iloc[-1, 1:].values,
    columns=['count'],
    index=exportaciones.columns[1:]
    )

# ordenarlas de manera descendente
pareto_exportaciones = pareto_exportaciones.sort_values(by='count', ascending=False)

# añadir una columna del porcentaje acumulado
pareto_exportaciones['cumperc'] = pareto_exportaciones['count'].cumsum() / pareto_exportaciones['count'].sum() * 100

# Crear el grafico
fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.bar(pareto_exportaciones.index, pareto_exportaciones['count'], color='tab:blue')
#añadir una linea de porcentaje acumulado
ax2.plot(pareto_exportaciones.index, pareto_exportaciones['cumperc'], color='tab:orange', marker='D', ms=4)
ax2.axhline(y=80, color='tab:orange', linestyle='dashed')
ax2.yaxis.set_major_formatter(PercentFormatter())
# especificar el color de los ejes
ax.tick_params(axis='y', colors='tab:blue')
ax.set_ylabel('Millones de dolares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje respecto al total (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones chilenas totales', fontweight='bold')
plt.title('Último dato reportado')

plt.show()

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    exportaciones_porcion.index,
    exportaciones_porcion['Minería'],
    exportaciones_porcion['Agropecuario'],
    exportaciones_porcion['Industriales'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las principales categorías de exportaciones chilenas', fontweight='bold')
plt.title('Seguimiendo anual (TTM)')
ax.set_ylabel('Porcentaje respecto a las exportaciones totales (%)')
ax.legend(['Minería', 'Agropecuario-silvícola y pesquero', 'Industriales'], loc='lower left')
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

ax.text(0.15, -0.12,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

#%% Categoria: Mineria

cobre = cleaner('F068.B1.FLU.A1.0.C.N.Z.Z.Z.Z.6.0.M')
catodos = cleaner('F068.B1.FLU.A2.0.C.N.Z.Z.Z.Z.6.0.M')
concentrado = cleaner('F068.B1.FLU.A3.0.C.N.Z.Z.Z.Z.6.0.M')
hierro = cleaner('F068.B1.FLU.A4.0.C.N.Z.Z.Z.Z.6.0.M')
plata = cleaner('F068.B1.FLU.A5.0.C.N.Z.Z.Z.Z.6.0.M')
oro = cleaner('F068.B1.FLU.A6.0.C.N.Z.Z.Z.Z.6.0.M')
molibdeno = cleaner('F068.B1.FLU.A7.0.C.N.Z.Z.Z.Z.6.0.M')
litio = cleaner('F068.B1.FLU.A8.0.C.N.Z.Z.Z.Z.6.0.M')
sal = cleaner('F068.B1.FLU.A9.0.C.N.Z.Z.Z.Z.6.0.M')

mineras = exp_mineras.join(cobre, rsuffix='_1').join(hierro, rsuffix='_2').join(plata, rsuffix='_3').join(oro, rsuffix='_4').join(molibdeno, rsuffix='_5').join(litio, rsuffix='_6').join(sal, rsuffix='_7')
mineras.columns = ['total_mineras_fob', 'Cobre', 'Hierro', 'Plata', 'Oro', 'Molibdeno', 'Litio', 'Sal']

# Crear porcentajes de cada serie por cada mes
mineras_porcion = mineras.divide(mineras['total_mineras_fob'], axis=0) * 100

# Grafico pareto mineria
pareto_mineria = pd.DataFrame(
    data=mineras.iloc[-1, 1:].values,
    columns=['count'],
    index=mineras.columns[1:]
    )

# ordenarlas de manera descendente
pareto_mineria = pareto_mineria.sort_values(by='count', ascending=False)

# añadir una columna del porcentaje acumulado
pareto_mineria['cumperc'] = pareto_mineria['count'].cumsum() / pareto_mineria['count'].sum() * 100

# Crear el grafico
fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.bar(pareto_mineria.index, pareto_mineria['count'], color='tab:blue')
#añadir una linea de porcentaje acumulado
ax2.plot(pareto_mineria.index, pareto_mineria['cumperc'], color='tab:orange', marker='D', ms=4)
ax2.yaxis.set_major_formatter(PercentFormatter())
# especificar el color de los ejes
ax.tick_params(axis='y', colors='tab:blue')
ax.set_ylabel('Millones de dolares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje respecto al total (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones mineras chilenas', fontweight='bold')
plt.title('Último dato reportado')

plt.show()

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    mineras.index,
    mineras_porcion['Hierro'],
    mineras_porcion['Plata'],
    mineras_porcion['Oro'],
    mineras_porcion['Molibdeno'],
    mineras_porcion['Litio'],
    mineras_porcion['Sal'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las exportaciones mineras chilenas', fontweight='bold')
plt.title('Seguimiendo anual (TTM), Sin el cobre.')
ax.set_ylabel('Porcentaje respecto a las exportaciones mineras totales (%)')
ax.legend(mineras.columns[2:].to_list(), loc='upper left')
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

ax.text(0.15, -0.12,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

#Mineras de cobre
mineras_cobre = exp_mineras.join(catodos, lsuffix='_fob', rsuffix='_1').join(concentrado, rsuffix='_2')
mineras_cobre.columns = ['mineras_fob', 'catodos', 'concentrados']
mineras_cobre = mineras_cobre.divide(mineras_cobre['mineras_fob'], axis=0) * 100

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    mineras_cobre.index,
    mineras_cobre['catodos'],
    mineras_cobre['concentrados'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las exportaciones de Cobre', fontweight='bold')
plt.title('Seguimiento anual, solo subcomponentes del Cobre')
ax.set_ylabel('Porcentaje respecto a las exportaciones de cobre (%)')
ax.legend(['Catodos', 'Concentrados'], loc='lower left')
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

ax.text(0.15, -0.12,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

#%% Categoria: Agropecuario-silvícola y pesquero

fruticolas = cleaner('F068.B1.FLU.B1.0.C.N.Z.Z.Z.Z.6.0.M')
semillas = cleaner('F068.B1.FLU.B2.0.C.N.Z.Z.Z.Z.6.0.M') # es lo mismo que otros
silvicola = cleaner('F068.B1.FLU.B3.0.C.N.Z.Z.Z.Z.6.0.M')
pesca = cleaner('F068.B1.FLU.B4.0.C.N.Z.Z.Z.Z.6.0.M')

agropecuario = exp_agro.join(fruticolas, rsuffix='_1').join(semillas, rsuffix='_2').join(silvicola, rsuffix='_3').join(pesca, rsuffix='_4')
agropecuario.columns = ['total_agro_fob', 'Frutícola', 'Semillas', 'Silvicola', 'Pesca']
agropecuario_proporcion = agropecuario.divide(agropecuario['total_agro_fob'], axis=0) * 100

# Grafico pareto agropecuario
pareto_agropecuario = pd.DataFrame(
    data=agropecuario.iloc[-1, 1:].values,
    columns=['count'],
    index=agropecuario.columns[1:]
    )

# ordenarlas de manera descendente
pareto_agropecuario = pareto_agropecuario.sort_values(by='count', ascending=False)

# añadir una columna del porcentaje acumulado
pareto_agropecuario['cumperc'] = pareto_agropecuario['count'].cumsum() / pareto_agropecuario['count'].sum() * 100

# Crear el grafico
fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.bar(pareto_agropecuario.index, pareto_agropecuario['count'], color='tab:blue')
#añadir una linea de porcentaje acumulado
ax2.plot(pareto_agropecuario.index, pareto_agropecuario['cumperc'], color='tab:orange', marker='D', ms=4)
ax2.yaxis.set_major_formatter(PercentFormatter())
# especificar el color de los ejes
ax.tick_params(axis='y', colors='tab:blue')
ax.set_ylabel('Millones de dolares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje respecto al total (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones agropecuario-silvícola y pesquero chilenas', fontweight='bold')
plt.title('Último dato reportado')

plt.show()

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    agropecuario_proporcion.index,
    agropecuario_proporcion['Semillas'],
    agropecuario_proporcion['Silvicola'],
    agropecuario_proporcion['Pesca'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las exportaciones agropecuario-silvícola y pesquero (ASP) chilenas', fontweight='bold')
plt.title('Seguimiendo anual (TTM), Sin el sector frutícola.')
ax.set_ylabel('Porcentaje respecto a las exportaciones ASP totales (%)')
ax.legend(mineras.columns[2:].to_list(), loc='upper left')
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

ax.text(0.15, -0.12,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

# Desgloce del sector fruticola
uvas = cleaner('F068.B1.FLU.B11.0.C.N.Z.Z.Z.Z.6.0.M')
manzanas = cleaner('F068.B1.FLU.B12.0.C.N.Z.Z.Z.Z.6.0.M')
peras = cleaner('F068.B1.FLU.B13.0.C.N.Z.Z.Z.Z.6.0.M')
arandanos = cleaner('F068.B1.FLU.B14.0.C.N.Z.Z.Z.Z.6.0.M')
kiwis = cleaner('F068.B1.FLU.B15.0.C.N.Z.Z.Z.Z.6.0.M')
ciruelas = cleaner('F068.B1.FLU.B16.0.C.N.Z.Z.Z.Z.6.0.M')
cerezas = cleaner('F068.B1.FLU.B17.0.C.N.Z.Z.Z.Z.6.0.M')
paltas = cleaner('F068.B1.FLU.B18.0.C.N.Z.Z.Z.Z.6.0.M')

sector_fruticola = uvas.join(manzanas, rsuffix='_1').join(peras, rsuffix='_2').join(arandanos, rsuffix='_3').join(kiwis, rsuffix='_4').join(ciruelas, rsuffix='_5').join(cerezas, rsuffix='_6').join(paltas, rsuffix='_7')
sector_fruticola.columns = ['Uvas', 'Manzanas', 'Peras', 'Arandanos', 'Kiwis', 'Ciruelas', 'Cerezas', 'Paltas']

# Grafico pareto agropecuario fruticola
sector_fruticola = pd.DataFrame(
    data=sector_fruticola.iloc[-1, :].values,
    columns=['count'],
    index=sector_fruticola.columns
    )

# ordenarlas de manera descendente
sector_fruticola = sector_fruticola.sort_values(by='count', ascending=False)

# añadir una columna del porcentaje acumulado
sector_fruticola['cumperc'] = sector_fruticola['count'].cumsum() / sector_fruticola['count'].sum() * 100

# Crear el grafico
fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.bar(sector_fruticola.index, sector_fruticola['count'], color='tab:blue')
#añadir una linea de porcentaje acumulado
ax2.plot(sector_fruticola.index, sector_fruticola['cumperc'], color='tab:orange', marker='D', ms=4)
ax2.axhline(y=80, color='tab:orange', linestyle='dashed')
ax2.yaxis.set_major_formatter(PercentFormatter())
# especificar el color de los ejes
ax.tick_params(axis='y', colors='tab:blue')
ax.set_ylabel('Millones de dolares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje respecto al total (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones sector frutícola chileno', fontweight='bold')
plt.title('Último dato reportado')

plt.show()

#%% Categoria: Industriales
