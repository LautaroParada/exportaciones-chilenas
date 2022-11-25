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

# Exportaciones de bienes FOB (millones de dólares)
exportaciones_bienes = cleaner('F068.B1.FLU.Z.0.C.N.Z.Z.Z.Z.6.0.M', rolling_=False).resample('Q').sum().rolling(window=4).sum()
# Servicios, exportaciones (millones de dólares)
exportaciones_servicios = cleaner('F068.B2.FLU.Z.0.C.N.Z.T.Z.Z.6.0.T', window=4).to_period('Q').to_timestamp('Q')

comercio = exportaciones_bienes.join(exportaciones_servicios, rsuffix='_1')
comercio.columns = ['bienes', 'servicios']
comercio.fillna(method='ffill', inplace=True)
comercio['total_exportaciones'] = comercio['bienes'] + comercio['servicios']
comercio = comercio.divide(comercio['total_exportaciones'], axis=0) * 100

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    comercio.index,
    comercio['bienes'],
    comercio['servicios'],
    colors=['tab:blue', 'tab:orange'], 
    labels=['Bienes', 'Servicios'],
    alpha=0.5
    )
fig.suptitle('Balanza de pagos: Composición exportaciones totales', fontweight='bold')
plt.title('Seguimiento anual (TTM)')
ax.set_ylabel('Porcentaje respecto a las exportaciones totales (%)')
ax.legend(loc='lower left')
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
ax.set_ylabel('Millones de dólares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje acumulado de exportaciones de bienes (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones de bienes chilenos', fontweight='bold')
plt.title('Último dato reportado')

ax.text(0.15, -0.25,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    exportaciones_porcion.index,
    exportaciones_porcion['Minería'],
    exportaciones_porcion['Agropecuario'],
    exportaciones_porcion['Industriales'],
    colors=['tab:orange', 'tab:green', 'tab:blue'],
    labels=['Minería', 'Agropecuario', 'Industriales'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las principales categorías de exportaciones de bienes chilenos', fontweight='bold')
plt.title('Seguimiento anual (TTM)')
ax.set_ylabel('Porcentaje respecto a las exportaciones de bienes (%)')
ax.legend(loc='lower left')
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
ax2.set_ylabel('Porcentaje acumulado de exportaciones mineras (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones mineras chilenas', fontweight='bold')
plt.title('Último dato reportado')

ax.text(0.15, -0.2,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

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
    colors=['tab:blue', 'tab:grey', 'gold', 'tab:purple', 'tab:green', 'tab:red'],
    labels=['Hierro', 'Plata', 'Oro', 'Molibdeno', 'Litio', 'Sal'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las exportaciones mineras chilenas', fontweight='bold')
plt.title('Seguimiendo anual (TTM), Sin el cobre.')
ax.set_ylabel('Porcentaje respecto a las exportaciones mineras totales (%)')
ax.legend(loc='upper left')
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
    colors=['tab:orange', 'tab:grey'],
    labels=['Cátodos', 'Concentrados'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las exportaciones relacionadas al Cobre', fontweight='bold')
plt.title('Seguimiento anual (TTM)')
ax.set_ylabel('Porcentaje respecto a las exportaciones mineras totales (%)')
ax.legend(loc='lower left')
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
ax2.set_ylabel('Porcentaje acumulado de exportaciones ASP (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones agropecuario-silvícola y pesquero (ASP) chilenas', fontweight='bold')
plt.title('Último dato reportado')

ax.text(0.15, -0.25,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    agropecuario_proporcion.index,
    agropecuario_proporcion['Semillas'],
    agropecuario_proporcion['Silvicola'],
    agropecuario_proporcion['Pesca'],
    colors=['tab:brown', 'tab:green', 'tab:blue'],
    labels=['Semillas', 'Sector silvícola', 'Pesca extractiva'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las exportaciones agropecuario-silvícola y pesquero (ASP) chilenas', fontweight='bold')
plt.title('Seguimiendo anual (TTM), Sin el sector frutícola.')
ax.set_ylabel('Porcentaje respecto a las exportaciones ASP (%)')
ax.legend(loc='lower left')
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
ax2.set_ylabel('Porcentaje acumulado de exportaciones del sector frutícola (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones sector frutícola chileno', fontweight='bold')
plt.title('Último dato reportado')

ax.text(0.15, -0.25,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

#%% Grafico de torta para el sector fruticola
from matplotlib.patches import ConnectionPatch
# https://matplotlib.org/stable/gallery/pie_and_polar_charts/bar_of_pie.html#sphx-glr-gallery-pie-and-polar-charts-bar-of-pie-py
# Seleccionando los datos para el pie chart

# make figure and assign axis objects
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
fig.subplots_adjust(wspace=0)

# pie chart parameters
overall_ratios = agropecuario_proporcion.iloc[-1, 1:].to_list()
labels = agropecuario_proporcion.iloc[-1, 1:].index.to_list()
explode = [0.1, 0, 0, 0]
# rotate so that first wedge is split by the x-axis
angle = -30.25 * overall_ratios[0]
wedges, *_ = ax1.pie(overall_ratios, autopct='%0.1f%%', startangle=angle,
                     labels=labels, explode=explode)

# bar chart parameters
sector_fruticola = uvas.join(manzanas, rsuffix='_1').join(peras, rsuffix='_2').join(arandanos, rsuffix='_3').join(kiwis, rsuffix='_4').join(ciruelas, rsuffix='_5').join(cerezas, rsuffix='_6').join(paltas, rsuffix='_7')
sector_fruticola.columns = ['Uvas', 'Manzanas', 'Peras', 'Arandanos', 'Kiwis', 'Ciruelas', 'Cerezas', 'Paltas'] 

sector_fruticola_porcion = sector_fruticola.divide(agropecuario['Frutícola'], axis=0).iloc[-1, :].sort_values(ascending=True) * 100

age_ratios = sector_fruticola_porcion.to_list()
age_labels = sector_fruticola_porcion.index.to_list()
bottom = 1
width = .2

# Adding from the top matches the legend.
for j, (height, label) in enumerate(reversed([*zip(age_ratios, age_labels)])):
    bottom -= height
    # ARREGLAR A UN DEGRADE
    bc = ax2.bar(0, height, width, bottom=bottom, color='tab:purple', label=label, alpha=0.1 + (1/len(age_labels)) * j)
    ax2.bar_label(bc, labels=[f"{round(height, 1)}%"], label_type='center')

ax2.set_title('Desglose exportaciones\nsector Frutícula', fontweight='bold')
ax2.legend()
ax2.axis('off')
ax2.set_xlim(- 1 * width, 1 * width)

# use ConnectionPatch to draw lines between the two plots
theta1, theta2 = wedges[0].theta1, wedges[0].theta2
center, r = wedges[0].center, wedges[0].r
bar_height = sum(age_ratios)

# draw top connecting line
x = r * np.cos(np.pi / 180 * theta2) + center[0]
y = r * np.sin(np.pi / 180 * theta2) + center[1]
con = ConnectionPatch(xyA=(-width / 2, 0), coordsA=ax2.transData,
                      xyB=(x, y), coordsB=ax1.transData)
con.set_color([0, 0, 0])
con.set_linewidth(4)
ax2.add_artist(con)

# draw bottom connecting line
x = r * np.cos(np.pi / 180 * theta1) + center[0]
y = r * np.sin(np.pi / 180 * theta1) + center[1]
con = ConnectionPatch(xyA=(-width / 2, -bar_height+1), coordsA=ax2.transData,
                      xyB=(x, y), coordsB=ax1.transData)
con.set_color([0, 0, 0])
ax2.add_artist(con)
con.set_linewidth(4)

ax1.text(0.15, -0.12,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

#%% Categoria: Industriales

alimentos = cleaner('F068.B1.FLU.C1.0.C.N.Z.Z.Z.Z.6.0.M')
bebidas = cleaner('F068.B1.FLU.C2.0.C.N.Z.Z.Z.Z.6.0.M')
forestal = cleaner('F068.B1.FLU.C3.0.C.N.Z.Z.Z.Z.6.0.M')
celulosa = cleaner('F068.B1.FLU.C4.0.C.N.Z.Z.Z.Z.6.0.M')
quimicos = cleaner('F068.B1.FLU.C5.0.C.N.Z.Z.Z.Z.6.0.M')
metalica = cleaner('F068.B1.FLU.C6.0.C.N.Z.Z.Z.Z.6.0.M')
maquinaria = cleaner('F068.B1.FLU.C7.0.C.N.Z.Z.Z.Z.6.0.M')
otros = cleaner('F068.B1.FLU.C9.0.C.N.Z.Z.Z.Z.6.0.M')

industriales = exp_ind.join(alimentos, rsuffix='_1').join(bebidas, rsuffix='_2').join(forestal, rsuffix='_3').join(celulosa, rsuffix='_4').join(quimicos, rsuffix='_5').join(metalica, rsuffix='_6').join(maquinaria, rsuffix='_7').join(otros, rsuffix='_8')
industriales.columns = ['total_industrial_fob', 'Alimentos', 'Bebidas\ny tabaco', 'Forestal y\nmuebles de\nmadera', 'Celulosa, papel\ny otros', 'Productos\nquímicos', 'Industria metálica\nbasica', 'Maquinaria y\nequipos', 'Otros']
industriales_proporcion = industriales.divide(industriales['total_industrial_fob'], axis=0) * 100

# Grafico pareto industriales
pareto_industriales = pd.DataFrame(
    data=industriales.iloc[-1, 1:].values,
    columns=['count'],
    index=industriales.columns[1:]
    )

# ordenarlas de manera descendente
pareto_industriales = pareto_industriales.sort_values(by='count', ascending=False)

# añadir una columna del porcentaje acumulado
pareto_industriales['cumperc'] = pareto_industriales['count'].cumsum() / pareto_industriales['count'].sum() * 100

# Crear el grafico
fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.bar(pareto_industriales.index, pareto_industriales['count'], color='tab:blue')
#añadir una linea de porcentaje acumulado
ax2.plot(pareto_industriales.index, pareto_industriales['cumperc'], color='tab:orange', marker='D', ms=4)
ax2.axhline(y=80, color='tab:orange', linestyle='dashed')
ax2.yaxis.set_major_formatter(PercentFormatter())
# especificar el color de los ejes
ax.tick_params(axis='y', colors='tab:blue')
ax.set_ylabel('Millones de dolares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje acumulado de exportaciones industriales (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones industriales chilenas', fontweight='bold')
plt.title('Último dato reportado')

ax.text(0.15, -0.3,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    industriales_proporcion.index,
    industriales_proporcion['Alimentos'],
    industriales_proporcion['Bebidas\ny tabaco'],
    industriales_proporcion['Forestal y\nmuebles de\nmadera'],
    industriales_proporcion['Celulosa, papel\ny otros'],
    industriales_proporcion['Productos\nquímicos'],
    industriales_proporcion['Industria metálica\nbasica'],
    industriales_proporcion['Maquinaria y\nequipos'],
    industriales_proporcion['Otros'],
    labels=['Alimentos', 'Bebidas y tabaco', 'Forestal y muebles de madera',
               'Celulosa, papel y otros', 'Productos químicos', 'Industria metálica basica',
               'Maquinaria y equipos', 'Otros'],
    colors=['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple',
            'tab:brown', 'tab:pink', 'tab:grey'],
    alpha=0.5
    )
fig.suptitle('Proporción histórica de las exportaciones industriales chilenas', fontweight='bold')
plt.title('Seguimiendo anual (TTM)')
ax.set_ylabel('Porcentaje respecto a las exportaciones industriales (%)')
ax.legend(loc='upper left')
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

# Desglose categoria alimentos
harina_pescado = cleaner('F068.B1.FLU.C11.0.C.N.Z.Z.Z.Z.6.0.M')
aceite_pescado = cleaner('F068.B1.FLU.C1E.0.C.N.Z.Z.Z.Z.6.0.M')
salmon = cleaner('F068.B1.FLU.C13.0.C.N.Z.Z.Z.Z.6.0.M')
trucha = cleaner('F068.B1.FLU.C14.0.C.N.Z.Z.Z.Z.6.0.M')
merluza = cleaner('F068.B1.FLU.C15.0.C.N.Z.Z.Z.Z.6.0.M')
conservas_pescado = cleaner('F068.B1.FLU.C16.0.C.N.Z.Z.Z.Z.6.0.M')
moluscos = cleaner('F068.B1.FLU.C17.0.C.N.Z.Z.Z.Z.6.0.M')
fruta_desh = cleaner('F068.B1.FLU.C18.0.C.N.Z.Z.Z.Z.6.0.M')
fruta_cong = cleaner('F068.B1.FLU.C19.0.C.N.Z.Z.Z.Z.6.0.M')
fruta_jugo = cleaner('F068.B1.FLU.C1A.0.C.N.Z.Z.Z.Z.6.0.M')
fruta_conserva = cleaner('F068.B1.FLU.C1B.0.C.N.Z.Z.Z.Z.6.0.M')
carne_ave = cleaner('F068.B1.FLU.C1C.0.C.N.Z.Z.Z.Z.6.0.M')
carne_cerdo = cleaner('F068.B1.FLU.C1D.0.C.N.Z.Z.Z.Z.6.0.M')

alimentos_industriales = alimentos.join(harina_pescado, rsuffix='_1').join(aceite_pescado, rsuffix='_2').join(salmon, rsuffix='_3').join(trucha, rsuffix='_4').join(merluza, rsuffix='_5').join(conservas_pescado, rsuffix='_6').join(moluscos, rsuffix='_7').join(fruta_desh, rsuffix='_8').join(fruta_cong, rsuffix='_9').join(fruta_jugo, rsuffix='_10').join(fruta_conserva, rsuffix='_11').join(carne_ave, rsuffix='_12').join(carne_cerdo, rsuffix='_13')
alimentos_industriales.columns = ['total_fob_alimentos', 'Harina de\npescado', 'Aceite de\npescado',
                                  'Salmón', 'Trucha', 'Merluza', 'Conservas\nde pescado',
                                  'Moluscos y\ncrustáceos', 'Fruta\ndeshidratada',
                                  'Fruta\ncongelada', 'Jugo fruta', 'Fruta\nconserva',
                                  'Carne\nde ave', 'Carne\nde cerdo']

alimentos_industriales_porcion = alimentos_industriales.divide(alimentos_industriales['total_fob_alimentos'], axis=0) * 100

# Grafico pareto industriales-ALIMENTOS
pareto_alimentos = pd.DataFrame(
    data=alimentos_industriales.iloc[-1, 1:].values,
    columns=['count'],
    index=alimentos_industriales.columns[1:]
    )

# ordenarlas de manera descendente
pareto_alimentos = pareto_alimentos.sort_values(by='count', ascending=False)

# añadir una columna del porcentaje acumulado
pareto_alimentos['cumperc'] = pareto_alimentos['count'].cumsum() / pareto_alimentos['count'].sum() * 100

# Crear el grafico de Pareto
fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.bar(pareto_alimentos.index, pareto_alimentos['count'], color='tab:blue')
#añadir una linea de porcentaje acumulado
ax2.plot(pareto_alimentos.index, pareto_alimentos['cumperc'], color='tab:orange', marker='D', ms=4)
ax2.axhline(y=80, color='tab:orange', linestyle='dashed')
ax2.yaxis.set_major_formatter(PercentFormatter())
# especificar el color de los ejes
ax.tick_params(axis='y', colors='tab:blue')
ax.set_ylabel('Millones de dolares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje acumulado de exportaciones de alimentos (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=45)

fig.suptitle('Gráfico de Pareto de las exportaciones de alimentos chilenos', fontweight='bold')
plt.title('Último dato reportado')

ax.text(0.15, -0.3,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

# Evolución historica
fig, ax= plt.subplots(figsize=(10, 5))

ax.stackplot(
    alimentos_industriales_porcion.index,
    alimentos_industriales_porcion['Harina de\npescado'],
    alimentos_industriales_porcion['Aceite de\npescado'],
    alimentos_industriales_porcion['Salmón'],
    alimentos_industriales_porcion['Trucha'],
    alimentos_industriales_porcion['Merluza'],
    alimentos_industriales_porcion['Conservas\nde pescado'],
    alimentos_industriales_porcion['Moluscos y\ncrustáceos'],
    alimentos_industriales_porcion['Fruta\ndeshidratada'],
    alimentos_industriales_porcion['Fruta\ncongelada'],
    alimentos_industriales_porcion['Jugo fruta'],
    alimentos_industriales_porcion['Fruta\nconserva'],
    alimentos_industriales_porcion['Carne\nde ave'],
    alimentos_industriales_porcion['Carne\nde cerdo'],
    alpha=0.5,
    colors=['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 
            'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray',
            'lime', 'tab:cyan', 'black', 'fuchsia', 'gold']
    )
fig.suptitle('Proporción histórica de las exportaciones de alimentos chilenos', fontweight='bold')
plt.title('Seguimiendo anual (TTM)')
ax.set_ylabel('Porcentaje respecto a las exportaciones de alimentos (%)')
ax.legend(['Harina de pescado', 'Aceite de pescado', 'Salmón', 'Trucha',
           'Merluza', 'Conservas de pescado','Moluscos y crustáceos', 
           'Fruta deshidratada','Fruta congelada', 'Jugo fruta', 
           'Fruta conserva','Carne de ave', 'Carne de cerdo'], loc='upper left')
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

#%% Pareto de todos los subsectores de las exportaciones

subsectores_exportaciones = mineras.iloc[:, 1:].join(agropecuario.iloc[:, 1:]).join(industriales.iloc[:, 1:])
subsectores_exportaciones.columns = ['Cobre', 'Hierro', 'Plata', 'Oro', 'Molibdeno', 
                                     'Litio', 'Sal', 'Frutícola', 'Semillas', 
                                     'Silvicola', 'Pesca', 'Alimentos', 'Bebidas', 
                                     'Forestal', 'Celulosa', 
                                     'Químicos','Ind metálica', 
                                     'Maquinaria', 'Otros Industriales']

# Pareto con el cobre
# Grafico pareto de los subsectores exportadores
pareto_subsectores_exportaciones = pd.DataFrame(
    data=subsectores_exportaciones.iloc[-1, :].values,
    columns=['count'],
    index=subsectores_exportaciones.columns[:]
    )

# ordenarlas de manera descendente
pareto_subsectores_exportaciones = pareto_subsectores_exportaciones.sort_values(by='count', ascending=False)

# añadir una columna del porcentaje acumulado
pareto_subsectores_exportaciones['cumperc'] = pareto_subsectores_exportaciones['count'].cumsum() / pareto_subsectores_exportaciones['count'].sum() * 100

# Crear el grafico de Pareto
fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.bar(pareto_subsectores_exportaciones.index, pareto_subsectores_exportaciones['count'], color='tab:blue')
#añadir una linea de porcentaje acumulado
ax2.plot(pareto_subsectores_exportaciones.index, pareto_subsectores_exportaciones['cumperc'], color='tab:orange', marker='D', ms=4)
ax2.axhline(y=80, color='tab:orange', linestyle='dashed')
ax2.yaxis.set_major_formatter(PercentFormatter())
# especificar el color de los ejes
ax.tick_params(axis='y', colors='tab:blue')
ax.set_ylabel('Millones de dolares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje acumulado de exportaciones de bienes (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=90)

fig.suptitle('Gráfico de Pareto de las exportaciones de bienes chilenos', fontweight='bold')
plt.title('Último dato reportado')

ax.text(0.15, -0.3,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

# PAreto sin el cobre

# Grafico pareto de los subsectores exportadores
pareto_subsectores_exportaciones = pd.DataFrame(
    data=subsectores_exportaciones.iloc[-1, 1:].values,
    columns=['count'],
    index=subsectores_exportaciones.columns[1:]
    )

# ordenarlas de manera descendente
pareto_subsectores_exportaciones = pareto_subsectores_exportaciones.sort_values(by='count', ascending=False)

# añadir una columna del porcentaje acumulado
pareto_subsectores_exportaciones['cumperc'] = pareto_subsectores_exportaciones['count'].cumsum() / pareto_subsectores_exportaciones['count'].sum() * 100

# Crear el grafico de Pareto
fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.bar(pareto_subsectores_exportaciones.index, pareto_subsectores_exportaciones['count'], color='tab:blue')
#añadir una linea de porcentaje acumulado
ax2.plot(pareto_subsectores_exportaciones.index, pareto_subsectores_exportaciones['cumperc'], color='tab:orange', marker='D', ms=4)
ax2.axhline(y=80, color='tab:orange', linestyle='dashed')
ax2.yaxis.set_major_formatter(PercentFormatter())
# especificar el color de los ejes
ax.tick_params(axis='y', colors='tab:blue')
ax.set_ylabel('Millones de dolares (USD)', color='tab:blue')
ax2.tick_params(axis='y', colors='tab:orange')
ax2.set_ylabel('Porcentaje acumulado de exportaciones de bienes (%)', color='tab:orange')
ax.tick_params(axis='x', labelrotation=90)

fig.suptitle('Gráfico de Pareto de las exportaciones de bienes chilenos, se EXCLUYE el cobre.', fontweight='bold')
plt.title('Último dato reportado')

ax.text(0.15, -0.3,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

#%% Terminos de Comercio
from matplotlib.dates import datestr2num

def cleaner_dolar(serie:str, resam:str=None, operations:list=None):
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
    serie_ = pd.DataFrame(client.get_macro(serie=serie))
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

# Exportaciones de bienes (FOB) -> F068.B1.FLU.Z.0.C.N.Z.Z.Z.Z.6.0.M
# Importaciones de bienes FOB (millones de dólares) -> F068.B1.FLU.Z.0.D.N.0.T.Z.Z.6.0.M
exportaciones = cleaner('F068.B1.FLU.Z.0.C.N.Z.Z.Z.Z.6.0.M').to_period('M').to_timestamp('M')
importaciones = cleaner('F068.B1.FLU.Z.0.D.N.0.T.Z.Z.6.0.M').to_period('M').to_timestamp('M')
dolar = cleaner_dolar('F073.TCO.PRE.Z.D').resample('M').median().to_period('M').to_timestamp('M')

tot = (exportaciones / importaciones) * 100

fig, ax = plt.subplots(figsize=(10, 5))
ax2 = ax.twinx()

ax.plot(tot, color='tab:blue')
ax2.plot(dolar.filter(items=tot.index, axis=0), color='tab:green')
ax.grid(True, linestyle='--')
fig.suptitle('Terminos de comercio en Chile (TOT) y su relación con el dólar (mediana mensual)', fontweight='bold')
plt.title('TOT = Exportaciones / Importaciones, seguimiento anual (TTM)')
ax.set_ylabel('Ratio (%)', color='tab:blue')
ax.tick_params(axis='y', labelcolor='tab:blue')
ax2.set_ylabel('Tipo de cambio del dólar, mediana mensual', color='tab:green')
ax2.tick_params(labelcolor='tab:green')

ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

# recesiones
# hay que chequear si la accion existia en ese tiempo o no
    # Subprime
ax.axvspan(datestr2num('2007-12-01'), datestr2num('2009-06-30'), color='grey', alpha=0.5)
    # Covid-19
ax.axvspan(datestr2num('2020-01-01'), datestr2num('2020-04-30'), color='grey', alpha=0.5)

ax.text(0.7, -0.12,  
         "Las áreas sombreadas indican las recesiones de EEUU.", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black')

# Graph source
ax.text(0.2, -0.12,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

fig, ax = plt.subplots(figsize=(10, 5))

import statsmodels.api as sm
cycle, trend = sm.tsa.filters.hpfilter(tot.dropna(), 1600*3**4)

ax.plot(tot, color='tab:blue')
ax.plot(trend, color='tab:orange')
ax.grid(True, linestyle='--')
ax.axhline(y=100, color='tab:red', linestyle='dashed')
fig.suptitle('Terminos de comercio en Chile (TOT o Terms of Trade)', fontweight='bold')
plt.title('TOT = Exportaciones / Importaciones, seguimiento anual (TTM)')

ax.legend(['TOT', 'Filtro de Hodrick–Prescott', 'Paridad TOT'])
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_ylabel('Ratio (%)')

# recesiones
# hay que chequear si la accion existia en ese tiempo o no
    # Subprime
ax.axvspan(datestr2num('2007-12-01'), datestr2num('2009-06-30'), color='grey', alpha=0.5)
    # Covid-19
ax.axvspan(datestr2num('2020-01-01'), datestr2num('2020-04-30'), color='grey', alpha=0.5)

ax.text(0.7, -0.12,  
         "Las áreas sombreadas indican las recesiones de EEUU.", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black')

# Graph source
ax.text(0.2, -0.12,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()

# Relación entre el dolar y el TOT
index_to_follow = tot.dropna().index
tot = tot.dropna().values.flatten()
dolar = dolar.filter(items=index_to_follow, axis=0).values.flatten()

fig, ax = plt.subplots(figsize=(10, 5))

# calculando la regresion (x=desempleo, y=inflacion)
modelo = np.poly1d(np.polyfit(dolar, tot, 1))
# Calculando el R2
from sklearn.metrics import r2_score
r_2 = r2_score(tot, modelo(dolar))

ax.scatter(dolar, tot, color='tab:blue')
ax.plot(dolar, modelo(dolar), color='tab:orange')
fig.suptitle('Relación entre los terminos de comercio (TOT) y el precio del dólar', fontweight='bold')
plt.title('Datos desde Enero 2003 hasta el dato más reciente')
ax.set_ylabel('Terms of Trade (Terminos de Comercio) de Chile')
ax.set_xlabel('Tipo de cambio del dólar, mediana mensual')
ax.text(0.8, 0.8,  
         r"$R^{2} = $" + f"{round(r_2,2)}", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=24, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

# Graph source
ax.text(0.2, -0.17,  
         "Fuente: Banco Central de Chile   Gráfico: Lautaro Parada", 
         horizontalalignment='center',
         verticalalignment='center', 
         transform=ax.transAxes, 
         fontsize=8, 
         color='black',
         bbox=dict(facecolor='tab:gray', alpha=0.5))

plt.show()