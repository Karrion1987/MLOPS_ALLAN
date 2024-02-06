from typing import Union, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
from dateutil import parser
from typing import List
import pyarrow.parquet as pq
import os
import string
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from fastapi.encoders import jsonable_encoder
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
# Creacion de una aplicacion FastApi

app = FastAPI()

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def read_root_html():
    message = """
    <style>
        body {
            background-color: #f0f0f0;
            color: #333;
            font-family: Arial, sans-serif;
        }

        div {
            width: 100%;
            text-align: center;
            margin: auto;
        }

        .welcome-message {
            font-size: 24px;
            margin-bottom: 10px;
            color: #6c757d; /* Gris */
        }

        .invite-message {
            font-size: 18px;
            margin-bottom: 20px;
            color: #7952b3; /* Violeta */
        }

        .collaborate-message {
            font-size: 16px;
            color: #6c757d; /* Gris */
        }

        .button-container {
            display: flex;
            justify-content: center;
            margin-top: 20px;
        }

        .main-button {
            font-size: 16px;
            color: #fff;
            background-color: #7952b3; /* Violeta */
            border: none;
            padding: 10px 20px;
            cursor: pointer;
        }

        .main-button:hover {
            background-color: #6a4b9e; /* Cambio de color al pasar el ratón sobre el botón */
        }
    </style>
    <div>
        <div class="welcome-message">¡Bienvenido a mi Proyecto de MLOPS en Henry!</div>
        <div class="invite-message">Te invito a explorar el fascinante mundo de Machine Learning y Ops.</div>
        <div class="collaborate-message">Te comparto mi sistema de recomendacion de la plataforma STEAM.</div>
        <div class="button-container">
            <form action='/redirect' style="display: inline-block;">
                <input class="main-button" type='submit' value='Continuar'>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=message)

@app.get("/redirect", include_in_schema=False)
def redirect_to_docs():
    link = "https://api-functions.onrender.com/docs"
    raise HTTPException(status_code=302, detail="Redirecting", headers={"Location": link})


# ejecutar uvicorn main:app --reload para cargar en el servidor



# ------- FUNCION developer ----------

@app.get("/developer/{desarrollador}")
def developer(desarrollador: str):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_parquet = os.path.join(current_directory, 'data', 'df_games_etl.parquet')
    df_games_etl = pq.read_table(path_to_parquet).to_pandas()


    # Filtrar el DataFrame por la empresa desarrolladora
    df_desarrollador = df_games_etl[df_games_etl['developer'] == desarrollador].copy()

    def obtener_anio(fecha):
        try:
            # Intentar convertir la fecha al formato de fecha
            fecha_obj = parser.parse(fecha)
            return fecha_obj.year
        except:
            # Si no se puede convertir, retornar un valor nulo o manejarlo según sea necesario
            return None

    # Crear la columna "anio" extrayendo el año de la columna "release_date"
    df_desarrollador['anio'] = df_desarrollador['release_date'].apply(obtener_anio).astype('Int64')

    # Contar la cantidad de items por año
    cantidad_items_por_año = df_desarrollador.groupby('anio').size().reset_index(name='cantidad_items')

    # Contar la cantidad de items gratuitos por año
    cantidad_items_gratuitos_por_año = (df_desarrollador[df_desarrollador['es_gratis']].groupby('anio').size().reset_index(name='cantidad_items_gratuitos')).astype('Int64')

    # Fusionar los DataFrames para obtener la cantidad total y gratuita por año
    resultado = pd.merge(cantidad_items_por_año, cantidad_items_gratuitos_por_año, on='anio', how='left').fillna(0)

    # Calcular el porcentaje de contenido gratuito por año
    resultado['porcentaje_gratuito'] = ((resultado['cantidad_items_gratuitos'] / resultado['cantidad_items']) * 100).round(2)

    # Convertir el resultado a formato JSON para que pueda ser retornado por FastAPI
    resultado_json = resultado.to_dict(orient='records')

    return resultado_json


# ------- FUNCION userdata ----------

@app.get("/userdata/{user_id}")
def userdata(user_id: str):

    # Lee los archivos parquet de la carpeta data
    current_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_parquet = os.path.join(current_directory, 'data', 'df_gastos_items.parquet')
    df_gastos_items = pq.read_table(path_to_parquet).to_pandas()

    current_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_parquet = os.path.join(current_directory, 'data', 'df_reviews_etl.parquet')
    df_reviews_etl = pq.read_table(path_to_parquet).to_pandas()


    # Filtra por el usuario de interés
    usuario = df_reviews_etl[df_reviews_etl['user_id'] == user_id]

    if usuario.empty:
        raise HTTPException(status_code=404, detail="User not found")

    # Convertir user_id a tipo string para asegurarse de que coincida con el tipo de datos en los DataFrames
    user_id = str(user_id)

    # Calcula la cantidad de dinero gastado para el usuario de interés
    cantidad_dinero = df_gastos_items[df_gastos_items['user_id'] == user_id]['price'].iloc[0]

    # Busca el count_item para el usuario de interés
    count_items = df_gastos_items[df_gastos_items['user_id'] == user_id]['items_count'].iloc[0]

    # Calcula el total de recomendaciones realizadas por el usuario de interés
    total_recomendaciones = usuario['recommend'].sum()

    # Calcula el total de reviews realizada por todos los usuarios
    total_reviews = len(df_reviews_etl['user_id'].unique())

    # Calcula el porcentaje de recomendaciones realizadas por el usuario de interés
    porcentaje_recomendaciones = (total_recomendaciones / total_reviews) * 100

    return {
        'cantidad_dinero': int(cantidad_dinero),
        'porcentaje_recomendacion': round(float(porcentaje_recomendaciones), 2),
        'total_items': int(count_items)
    }

# ------- FUNCION user_for_genre ----------

@app.get("/user_for_genre/{genre}", response_model=dict)
def user_for_genre(genre: str):

    # Lee el archivo parquet de la carpeta data
    current_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_parquet = os.path.join(current_directory, 'data', 'df_games_genres.parquet')
    df_games_genres = pq.read_table(path_to_parquet).to_pandas()
    path_to_parquet = os.path.join(current_directory, 'data', 'df_users_horas.parquet')
    df_users_horas = pq.read_table(path_to_parquet).to_pandas()
    
    df_games_genres = df_games_genres.sample(frac=0.1, random_state=42)
    df_users_horas = df_users_horas.sample(frac=0.1, random_state=42)

    # Une ambos dataframes
    df_genres_horas = df_games_genres.merge(df_users_horas, on='item_id', how='right')

    # Filtra el DataFrame resultante para obtener solo las filas relacionadas con el género dado
    df_filtered = df_genres_horas[df_genres_horas['genres'] == genre]

    if df_filtered.empty:
        return {"message": "No data found for the given genre"}

    # Encontrar el usuario que acumula más horas jugadas para el género dado
    max_user = df_filtered.groupby('user_id')['playtime_forever'].sum().idxmax()

    # Filtrar el DataFrame para obtener solo las filas relacionadas con el usuario que acumula más horas
    df_user_max_hours = df_filtered[df_filtered['user_id'] == max_user]

    # Agrupar por año y sumar las horas jugadas
    horas_por_anio = df_user_max_hours.groupby('anio')['playtime_forever'].sum()

    # Construir el diccionario de resultados
    result_dict = {
        "Usuario con más horas jugadas para Género X": max_user,
        "Horas jugadas": [{"Año": int(year), "Horas": int(hours)} for year, hours in horas_por_anio.reset_index().to_dict(orient='split')['data']]
    }

    return result_dict


# ------- FUNCION best_developer_year ----------


# Definir la ruta de FastAPI para la función best_developer_year
@app.get("/best_developer/{year}", response_model=List[dict])

def best_developer_year(year: int):

    # Lee el archivo parquet de la carpeta data
    current_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_parquet = os.path.join(current_directory, 'data', 'df_best_developer_anio.parquet')
    df_best_developer_anio = pq.read_table(path_to_parquet).to_pandas()


    # Filtra el DataFrame para el año dado y donde recommend es True y sentiment_analysis es positivo
    df_filtered = df_best_developer_anio[(df_best_developer_anio['anio'] == year) &
                                         (df_best_developer_anio['recommend'] == True) &
                                         (df_best_developer_anio['sentiment_analysis'] > 1)]

    if df_filtered.empty:
        return None

    # Agrupar por desarrollador y contar la cantidad de juegos recomendados
    top_developers = df_filtered.groupby('developer')['recommend'].sum().sort_values(ascending=False).head(3)

    # Construir el resultado como una lista de diccionarios
    result = [{"Top {}".format(i + 1): developer} for i, (developer, _) in enumerate(top_developers.items())]

    return result


# ------- FUNCION developer_reviews_analysis ----------

# Definir la ruta de FastAPI para la función developer_reviews_analysis
@app.get("/developer-reviews-analysis/{desarrollador}")
def developer_reviews_analysis_endpoint(desarrollador: str):

    # Lee el archivo parquet de la carpeta data
    current_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_parquet = os.path.join(current_directory, 'data', 'df_developer_anio.parquet')
    df_developer_anio = pq.read_table(path_to_parquet).to_pandas()


    # Filtra el DataFrame para el desarrollador dado
    df_filtered = df_developer_anio[df_developer_anio['developer'] == desarrollador]


    if df_filtered.empty:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros para el desarrollador {desarrollador}")

    # Agrupar por análisis de sentimiento y contar la cantidad de registros
    analysis_counts = df_filtered.groupby('sentiment_analysis').size().to_dict()

    # Construir el resultado como un diccionario con una lista
    result = {desarrollador: [f'Negative = {analysis_counts.get(0, 0)}', f'Positive = {analysis_counts.get(2, 0)}']}

    return result

# ------- FUNCION Recomendacion_juego ----------

@app.get("/recommendations/{title}")
def get_recommendations(title: str):

    # Lee el archivo parquet de la carpeta data
    current_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_parquet = os.path.join(current_directory, 'data', 'df_recomendacion_juego.parquet')
    df_recomendacion_juego = pq.read_table(path_to_parquet).to_pandas()
    
    
    df = df_recomendacion_juego

    # Configuración de TF-IDF
    tfidf = TfidfVectorizer(stop_words='english')
    df['ntags'] = df['ntags'].fillna('')
    tfidf_matrix = tfidf.fit_transform(df['ntags'])
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

    indices = pd.Series(df.index, index=df['app_name']).drop_duplicates()

    try:
        # Obtener el índice del juego en la matriz de similitud coseno
        idx = indices[title]

        # Obtener las puntuaciones de similitud para el juego
        sim_scores = list(enumerate(cosine_sim[idx]))

        # Ordenar las puntuaciones de similitud por orden descendente
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

        # Obtener los índices de los 5 juegos más similares
        game_indices = [i[0] for i in sim_scores[1:6]]

        # Obtener los títulos de los 5 juegos más similares
        recommendations = df['app_name'].iloc[game_indices]

        return JSONResponse(content={'title': title, 'recommendations': recommendations.tolist()})

    except KeyError:
        raise HTTPException(status_code=404, detail=f'El juego {title} no se encuentra en el DataFrame.')



# ------- FUNCION recomendacion_user ----------

@app.get("/recomendacion_usuario/{user_id}")
def get_recomendacion_usuario(user_id: str):

    # Lee el archivo parquet de la carpeta data
    current_directory = os.path.dirname(os.path.abspath(__file__))
    path_to_parquet = os.path.join(current_directory, 'data', 'df_recomendacion_user.parquet')
    df_recomendacion_user = pq.read_table(path_to_parquet).to_pandas()

    try:

        # Crear una instancia de TfidfVectorizer con stop words en inglés
        tfidf = TfidfVectorizer(stop_words='english')

        # Rellenar los valores nulos en la columna 'app_name' con una cadena vacía
        df_recomendacion_user['app_name'] = df_recomendacion_user['app_name'].fillna('')

        # Aplicar la transformación TF-IDF a los datos de la columna 'app_name'
        tfidf_matrix = tfidf.fit_transform(df_recomendacion_user['app_name'])

        # Calcular la similitud coseno entre los juegos utilizando linear_kernel
        cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

        # Obtener el índice del usuario específico en el DataFrame
        matching_users = df_recomendacion_user[df_recomendacion_user['user_id'] == user_id]

        if not matching_users.empty:
            user_index = matching_users.index[0]

            # Obtener las recomendaciones basadas en similitud coseno y los filtros requeridos
            recomendaciones_user = []
            seen_games = set()  # Utilizar un conjunto para evitar duplicados
            for i, score in sorted(enumerate(cosine_sim[user_index]), key=lambda x: x[1], reverse=True):
                if df_recomendacion_user['recommend'][i] and df_recomendacion_user['sentiment_analysis'][i] in [0, 1, 2]:
                    app_name = df_recomendacion_user['app_name'][i]
                    if app_name not in seen_games:
                        recomendaciones_user.append({"app_name": app_name, "similarity": score})
                        seen_games.add(app_name)

            # Seleccionar las primeras 5 recomendaciones
            top_recommendations = recomendaciones_user[:5]

            # Preparar respuesta JSON
            response_data = {"user_id": user_id, "recommendations": top_recommendations}
            return JSONResponse(content=jsonable_encoder(response_data))
        else:
            return JSONResponse(content=jsonable_encoder({"error": f"No se encontró el usuario con ID: {user_id}"}))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))