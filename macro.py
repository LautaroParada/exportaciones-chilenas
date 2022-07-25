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

# Por seguridad, es mejor guardar las contraseñas y usuarios en las variables de entorno
bcch_user = os.environ['BCCH_USER']
bcch_pwd = os.environ['BCCH_PWD']

# Creación de la instancia
client = BancoCentralDeChile(bcch_user, bcch_pwd)

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
    serie_ = pd.DataFrame(client.get_macro(serie=serie))
    serie_['value'] = pd.to_numeric(serie_['value'], errors='coerce')
    serie_['indexDateString'] = pd.to_datetime(serie_['indexDateString'], format='%d-%m-%Y')
    serie_.set_index('indexDateString', inplace=True)
    del serie_['statusCode']
    
    if (resam is not None) & (operations is not None):
        serie_ = serie_.resample(resam).agg(operations)
        # renombrar las columnas
        serie_.columns = ['_'.join(x) for x in serie_.columns]
        return serie_
    else:
        return serie_

#%% Exportaciones de los principales productos chilenos

# Solicitar los datos
exportaciones = cleaner('F068.B1.FLU.Z.0.C.N.Z.Z.Z.Z.6.0.M', resam='Q', operations=['sum'])
exp_mineras = cleaner('F068.B1.FLU.A.0.C.N.Z.Z.Z.Z.6.0.M', resam='Q', operations=['sum'])
exp_agro = cleaner('F068.B1.FLU.B.0.C.N.Z.Z.Z.Z.6.0.M', resam='Q', operations=['sum'])
exp_ind = cleaner('F068.B1.FLU.C.0.C.N.Z.Z.Z.Z.6.0.M', resam='Q', operations=['sum'])

# Unir todo
exportaciones = exportaciones.join(exp_mineras, rsuffix='_min').join(exp_agro, rsuffix='_agro').join(exp_ind, rsuffix='_ind')
# cambiar los nombres
exportaciones.columns = ['total_fob', 'mineras', 'agropecuaria', 'industriales']

# Crear porcentajes de cada serie por cada mes
exportaciones_porcion = exportaciones.divide(exportaciones['total_fob'], axis=0) * 100

fig, ax = plt.subplots(figsize=(10, 5))

ax.stackplot(
    exportaciones_porcion.index,
    exportaciones_porcion['mineras'],
    exportaciones_porcion['agropecuaria'],
    exportaciones_porcion['industriales'],
    alpha=0.5
    )
fig.suptitle('Desglose de las exportaciones chilenas', fontweight='bold')
plt.title('Categorias principales, periodicidad trimestral')
ax.set_ylabel('Porcentaje respecto a las exportaciones totales (%)')
ax.legend(['Minería', 'Agropecuario-silvícola y pesquero', 'Industriales'], 
          loc='lower left')
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