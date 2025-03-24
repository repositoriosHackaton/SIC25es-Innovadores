#Funciones del bot
import requests
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import openai
import pandas as pd
import csv
import re
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurar las claves API
load_dotenv("keys.env")

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configurar la API de OpenAI
openai.api_key = OPENAI_API_KEY

# Diccionario de códigos de moneda
CURRENCY_CODES = {
    'euro': 'EUR', 'eur': 'EUR', 'euros': 'EUR',
    'dolar': 'USD', 'dólares': 'USD', 'dolares': 'USD', 'usd': 'USD',
    'libra': 'GBP', 'libras': 'GBP', 'gbp': 'GBP',
    'yen': 'JPY', 'yenes': 'JPY', 'jpy': 'JPY',
    'franco suizo': 'CHF', 'chf': 'CHF',
    'dolar canadiense': 'CAD', 'dólar canadiense': 'CAD', 'cad': 'CAD',
    'dolar australiano': 'AUD', 'dólar australiano': 'AUD', 'aud': 'AUD',
    'yuan': 'CNY', 'cny': 'CNY',
    'peso mexicano': 'MXN', 'mxn': 'MXN',
    'real brasileño': 'BRL', 'real brasileno': 'BRL', 'brl': 'BRL'
}

# Carpeta para almacenar los datos históricos
DATA_FOLDER = 'data'
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

def detect_intent(text):
    """
    Detecta la intención del usuario basándose en el texto de entrada.
    Opciones: conversion, graph, prediction, history, compare
    """
    text = text.lower()
    
    # Palabras clave para cada intención
    conversion_keywords = ['convertir', 'cambiar', 'conversion', 'conversión', 'equivale', 'valor', 'cuánto', 'cuanto', 'a dólares', 'a euros']
    graph_keywords = ['gráfico', 'grafico', 'gráfica', 'grafica', 'chart', 'tendencia', 'histórico', 'historico']
    prediction_keywords = ['predicción', 'prediccion', 'predecir', 'futuro', 'prever', 'pronóstico', 'pronostico', 'estimación', 'estimacion']
    history_keywords = ['hace', 'anterior', 'pasado', 'antes', 'historia', 'histórico', 'historico', 'atrás', 'atras']
    compare_keywords = ['compara', 'comparar', 'comparación', 'comparacion', 'diferencia', 'versus', 'vs', 'cambio entre']
    
    # Buscar palabras clave en el texto
    for keyword in history_keywords:
        if keyword in text:
            return "history"
    
    for keyword in compare_keywords:
        if keyword in text:
            return "compare"
    
    for keyword in prediction_keywords:
        if keyword in text:
            return "prediction"
        
    for keyword in graph_keywords:
        if keyword in text:
            return "graph"
    
    for keyword in conversion_keywords:
        if keyword in text:
            return "conversion"
    
    # Verificar si hay números y monedas (probable conversión)
    if any(c.isdigit() for c in text) and any(currency in text for currency in CURRENCY_CODES.keys()):
        return "conversion"
    
    # Por defecto, asumimos que es una consulta de conversión
    return "conversion"

def detect_currencies(text):
    """
    Detecta las monedas mencionadas en el texto.
    Retorna una lista de códigos de moneda.
    """
    text = text.lower()
    detected_currencies = []
    
    # Buscar códigos de moneda directos (EUR/USD, etc.)
    pairs = [p for p in text.split() if '/' in p]
    for pair in pairs:
        parts = pair.split('/')
        if len(parts) == 2:
            base, quote = parts
            if base.upper() in [code.upper() for code in CURRENCY_CODES.values()]:
                detected_currencies.append(base.upper())
            if quote.upper() in [code.upper() for code in CURRENCY_CODES.values()]:
                detected_currencies.append(quote.upper())
    
    # Buscar nombres de monedas en el texto
    for name, code in CURRENCY_CODES.items():
        if name in text and code not in detected_currencies:
            detected_currencies.append(code)
    
    return detected_currencies

def detect_time_period(text):
    """
    Detecta el período de tiempo mencionado en el texto.
    Retorna un diccionario con tipo (days, weeks, months) y cantidad.
    """
    text = text.lower()
    
    # Patrones para diferentes períodos de tiempo
    day_patterns = [r'(\d+)\s*(?:día|dia|días|dias|day|days)', r'hace\s*(\d+)\s*(?:día|dia|días|dias|day|days)']
    week_patterns = [r'(\d+)\s*(?:semana|semanas|week|weeks)', r'hace\s*(\d+)\s*(?:semana|semanas|week|weeks)']
    month_patterns = [r'(\d+)\s*(?:mes|meses|month|months)', r'hace\s*(\d+)\s*(?:mes|meses|month|months)']
    
    # Buscar coincidencias
    for pattern in day_patterns:
        match = re.search(pattern, text)
        if match:
            return {'type': 'days', 'value': int(match.group(1))}
    
    for pattern in week_patterns:
        match = re.search(pattern, text)
        if match:
            return {'type': 'weeks', 'value': int(match.group(1))}
    
    for pattern in month_patterns:
        match = re.search(pattern, text)
        if match:
            return {'type': 'months', 'value': int(match.group(1))}
    
    # Valores por defecto
    if 'semana' in text or 'semanas' in text or 'week' in text or 'weeks' in text:
        return {'type': 'weeks', 'value': 1}
    elif 'mes' in text or 'meses' in text or 'month' in text or 'months' in text:
        return {'type': 'months', 'value': 1}
    else:
        return {'type': 'days', 'value': 7}  # Por defecto, una semana

def check_conversion_request(text):
    """
    Analiza el texto para identificar una solicitud de conversión.
    Retorna amount, source_currency, target_currency
    """
    text = text.lower()
    
    try:
        # Primero intentamos con NLP
        nlp_result = analyze_text_with_openai(text)
        if nlp_result and all(key in nlp_result for key in ['amount', 'source_currency', 'target_currency']):
            return nlp_result['amount'], nlp_result['source_currency'], nlp_result['target_currency']
    except Exception as e:
        logger.error(f"Error al usar OpenAI para analizar el texto: {e}")
        # Continuamos con el método basado en reglas
    
    # Método alternativo basado en reglas si NLP falla
    # Buscar números en el texto
    amount = None
    numbers = [word for word in text.split() if word.replace('.', '', 1).isdigit()]
    if numbers:
        amount = float(numbers[0].replace(',', '.'))
    
    # Detectar monedas
    currencies = detect_currencies(text)
    if len(currencies) >= 2:
        source_currency, target_currency = currencies[0], currencies[1]
    elif len(currencies) == 1:
        # Buscar preposiciones "a", "en", "por" para determinar dirección
        parts = text.split()
        try:
            currency_index = next(i for i, part in enumerate(parts) 
                              if any(curr in part.lower() for curr in CURRENCY_CODES.keys()))
            if "a" in parts[currency_index:] or "en" in parts[currency_index:] or "por" in parts[currency_index:]:
                # La moneda mencionada primero es la fuente
                source_currency = currencies[0]
                target_currency = "USD"  # Predeterminado
            else:
                # La moneda mencionada es el objetivo
                source_currency = "EUR"  # Predeterminado
                target_currency = currencies[0]
        except (StopIteration, IndexError):
            source_currency = currencies[0]
            target_currency = "USD"  # Predeterminado
    else:
        # Si no se detecta ninguna moneda, usar valores predeterminados
        source_currency = "EUR"
        target_currency = "USD"
    
    # Si no se detectó cantidad, usar 1 como predeterminado
    if amount is None:
        amount = 1.0
    
    return amount, source_currency, target_currency

def analyze_text_with_openai(text):
    """
    Utiliza la API de OpenAI para analizar el texto y extraer información relevante.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que analiza solicitudes de conversión de divisas. Extrae la cantidad, la moneda de origen y la moneda de destino del texto del usuario."},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Validar y normalizar los códigos de moneda
        if 'source_currency' in result:
            source = result['source_currency'].lower()
            result['source_currency'] = CURRENCY_CODES.get(source, source.upper())
        
        if 'target_currency' in result:
            target = result['target_currency'].lower()
            result['target_currency'] = CURRENCY_CODES.get(target, target.upper())
        
        return result
    except Exception as e:
        logger.error(f"Error al analizar el texto con OpenAI: {e}")
        return None

def get_forex_quote(base_currency, target_currency):
    """
    Obtiene la cotización actual de un par de divisas utilizando Alpha Vantage.
    Guarda el resultado en un archivo CSV si ha cambiado.
    """
    try:
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={base_currency}&to_currency={target_currency}&apikey={ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        
        if "Realtime Currency Exchange Rate" in data:
            exchange_rate = data["Realtime Currency Exchange Rate"]
            mid_price = float(exchange_rate['5. Exchange Rate'])
            # Calcular bid/ask con un spread ficticio del 0.5%
            spread = mid_price * 0.0025
            bid_price = mid_price - spread
            ask_price = mid_price + spread
            timestamp = exchange_rate['6. Last Refreshed']
            
            # Guardar en CSV si el precio ha cambiado
            save_rate_to_csv(base_currency, target_currency, mid_price, bid_price, ask_price, timestamp)
            
            return {
                'mid_price': mid_price,
                'bid_price': bid_price,
                'ask_price': ask_price,
                'timestamp': timestamp
            }
        else:
            logger.error(f"Error al obtener datos de Alpha Vantage: {data}")
            return None
    except Exception as e:
        logger.error(f"Error al obtener la cotización: {e}")
        return None

def save_rate_to_csv(base_currency, target_currency, mid_price, bid_price, ask_price, timestamp):
    """
    Guarda la tasa de cambio en un archivo CSV.
    Solo guarda si el precio es diferente al último guardado.
    """
    try:
        pair = f"{base_currency}_{target_currency}"
        file_path = os.path.join(DATA_FOLDER, f"{pair}_history.csv")
        
        # Comprobar si ya existe el archivo
        file_exists = os.path.isfile(file_path)
        
        # Si existe, verificar si el último precio es diferente
        if file_exists:
            try:
                df = pd.read_csv(file_path)
                if not df.empty and abs(df.iloc[-1]['mid_price'] - mid_price) < 0.0001:
                    # El precio no ha cambiado significativamente, no guardamos
                    return
            except Exception as e:
                logger.error(f"Error al leer el archivo CSV: {e}")
        
        # Crear dataframe con los nuevos datos
        new_data = pd.DataFrame({
            'timestamp': [timestamp],
            'mid_price': [mid_price],
            'bid_price': [bid_price],
            'ask_price': [ask_price]
        })
        
        # Guardar en CSV (append si ya existe)
        if file_exists:
            new_data.to_csv(file_path, mode='a', header=False, index=False)
        else:
            new_data.to_csv(file_path, index=False)
        
        logger.info(f"Guardada nueva cotización para {pair}: {mid_price}")
    
    except Exception as e:
        logger.error(f"Error al guardar la tasa en CSV: {e}")

def get_historical_rates_from_api(base_currency, target_currency, days=30):
    """
    Obtiene datos históricos de tipo de cambio utilizando Alpha Vantage.
    """
    try:
        url = f"https://www.alphavantage.co/query?function=FX_DAILY&from_symbol={base_currency}&to_symbol={target_currency}&outputsize=compact&apikey={ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        
        if "Time Series FX (Daily)" in data:
            time_series = data["Time Series FX (Daily)"]
            dates = []
            rates = []
            
            # Ordenar por fecha y tomar los últimos 'days' días
            sorted_dates = sorted(time_series.keys(), reverse=True)[:days]
            
            for date in sorted_dates:
                dates.append(date)
                rates.append(float(time_series[date]['4. close']))
            
            # Invertir listas para que estén en orden cronológico
            dates.reverse()
            rates.reverse()
            
            return {
                'dates': dates,
                'rates': rates
            }
        else:
            logger.error(f"Error al obtener datos históricos de Alpha Vantage: {data}")
            return None
    except Exception as e:
        logger.error(f"Error al obtener tasas históricas: {e}")
        return None

def get_historical_rates_from_csv(base_currency, target_currency, days=30):
    """
    Obtiene datos históricos de tipo de cambio desde el archivo CSV local.
    """
    try:
        pair = f"{base_currency}_{target_currency}"
        file_path = os.path.join(DATA_FOLDER, f"{pair}_history.csv")
        
        if not os.path.isfile(file_path):
            logger.info(f"No se encontró archivo histórico para {pair}. Intentando con API.")
            return None
        
        df = pd.read_csv(file_path)
        
        # Convertir timestamp a datetime y ordenar
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Filtrar por los últimos 'days' días
        cutoff_date = datetime.now() - timedelta(days=days)
        df_filtered = df[df['timestamp'] >= cutoff_date]
        
        if df_filtered.empty:
            logger.info(f"No hay datos suficientes en CSV para {pair}. Intentando con API.")
            return None
        
        dates = df_filtered['timestamp'].dt.strftime('%Y-%m-%d').tolist()
        rates = df_filtered['mid_price'].tolist()
        
        return {
            'dates': dates,
            'rates': rates
        }
    
    except Exception as e:
        logger.error(f"Error al obtener tasas históricas desde CSV: {e}")
        return None

def get_historical_rates(base_currency, target_currency, days=30):
    """
    Obtiene datos históricos, primero intenta desde el CSV local y luego desde la API.
    """
    # Primero intentamos obtener desde CSV
    historical_data = get_historical_rates_from_csv(base_currency, target_currency, days)
    
    # Si no hay datos en CSV o son insuficientes, usamos la API
    if not historical_data:
        historical_data = get_historical_rates_from_api(base_currency, target_currency, days)
        if not historical_data:
            logger.error(f"No se pudieron obtener datos históricos para {base_currency}/{target_currency} desde la API.")
            return None
    
    return historical_data

def get_rate_at_date(base_currency, target_currency, target_date):
    """
    Obtiene la tasa de cambio en una fecha específica.
    target_date debe ser un objeto datetime.
    """
    try:
        pair = f"{base_currency}_{target_currency}"
        file_path = os.path.join(DATA_FOLDER, f"{pair}_history.csv")
        
        if not os.path.isfile(file_path):
            logger.info(f"No se encontró archivo histórico para {pair}.")
            return None
        
        df = pd.read_csv(file_path)
        
        # Convertir timestamp a datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Encontrar la entrada más cercana a la fecha objetivo
        target_date_str = target_date.strftime('%Y-%m-%d')
        df['date_diff'] = abs(df['timestamp'] - pd.to_datetime(target_date_str))
        closest_idx = df['date_diff'].idxmin()
        
        rate_data = df.loc[closest_idx]
        
        return {
            'date': rate_data['timestamp'].strftime('%Y-%m-%d'),
            'mid_price': rate_data['mid_price'],
            'bid_price': rate_data['bid_price'],
            'ask_price': rate_data['ask_price']
        }
    
    except Exception as e:
        logger.error(f"Error al obtener tasa para fecha específica: {e}")
        return None

def generate_rate_graph(base_currency, target_currency, period=None):
    """
    Genera un gráfico de tipo de cambio histórico.
    Si se proporciona period, se utiliza para determinar el rango de tiempo.
    """
    try:
        # Determinar el número de días
        days = 30  # Valor por defecto
        if period:
            if period['type'] == 'days':
                days = period['value']
            elif period['type'] == 'weeks':
                days = period['value'] * 7
            elif period['type'] == 'months':
                days = period['value'] * 30
        
        historical_data = get_historical_rates(base_currency, target_currency, days)
        
        if not historical_data:
            logger.error("No se pudieron obtener datos históricos para generar el gráfico.")
            return None
        
        plt.figure(figsize=(10, 6))
        plt.plot(range(len(historical_data['dates'])), historical_data['rates'], marker='o')
        
        # Agregar etiquetas de fechas legibles
        if len(historical_data['dates']) > 10:
            # Si hay muchas fechas, mostrar solo algunas
            step = len(historical_data['dates']) // 5
            tick_positions = range(0, len(historical_data['dates']), step)
            tick_labels = [historical_data['dates'][i] for i in tick_positions]
        else:
            tick_positions = range(len(historical_data['dates']))
            tick_labels = historical_data['dates']
        
        plt.xticks(tick_positions, tick_labels, rotation=45)
        
        time_description = f"{days} días"
        if period and period['type'] == 'weeks':
            time_description = f"{period['value']} semana(s)"
        elif period and period['type'] == 'months':
            time_description = f"{period['value']} mes(es)"
        
        plt.title(f'Tipo de Cambio {base_currency}/{target_currency} - Últimos {time_description}')
        plt.ylabel(f'Tasa de Cambio ({target_currency})')
        plt.xlabel('Fecha')
        plt.grid(True)
        plt.tight_layout()
        
        # Guardar el gráfico en un buffer de bytes
        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close()
        
        return buffer
    except Exception as e:
        logger.error(f"Error al generar el gráfico: {e}")
        return None

def predict_rates(base_currency, target_currency, period=None):
    """
    Realiza una predicción de tasas de cambio para un período futuro.
    Si se proporciona period, se utiliza para determinar el rango de tiempo.
    """
    try:
        # Determinar el número de días para la predicción
        prediction_days = 7  # Valor por defecto (una semana)
        training_days = 30   # Días para el entrenamiento
        
        if period:
            if period['type'] == 'days':
                prediction_days = period['value']
            elif period['type'] == 'weeks':
                prediction_days = period['value'] * 7
            elif period['type'] == 'months':
                prediction_days = period['value'] * 30
        
        # Obtener datos históricos para el entrenamiento
        historical_data = get_historical_rates(base_currency, target_currency, training_days)
        
        if not historical_data:
            logger.error("No se pudieron obtener datos históricos para la predicción.")
            return None
        
        rates = historical_data['rates']
        
        # Método simple: tendencia lineal
        x = np.array(range(len(rates)))
        y = np.array(rates)
        
        # Calcula la tendencia lineal
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        
        # Extrapola para los próximos días
        future_days = np.array(range(len(rates), len(rates) + prediction_days))
        predicted_values = p(future_days)
        
        # Calcular la tendencia porcentual
        current_rate = rates[-1]
        future_rate = predicted_values[-1]
        trend_percentage = ((future_rate - current_rate) / current_rate) * 100
        trend_direction = "al alza" if trend_percentage > 0 else "a la baja"
        
        # Formatear fechas para el resultado
        last_date = datetime.strptime(historical_data['dates'][-1], "%Y-%m-%d")
        future_dates = [(last_date + timedelta(days=i+1)).strftime("%Y-%m-%d") for i in range(prediction_days)]
        
        # Descripción del período
        time_description = f"{prediction_days} días"
        if period and period['type'] == 'weeks':
            time_description = f"{period['value']} semana(s)"
        elif period and period['type'] == 'months':
            time_description = f"{period['value']} mes(es)"
        
        # Crear respuesta
        result = {
            'current_rate': float(current_rate),
            'predicted_rates': [{'date': date, 'rate': float(rate)} for date, rate in zip(future_dates, predicted_values)],
            'trend_percentage': float(f"{trend_percentage:.2f}"),
            'trend_direction': trend_direction,
            'time_description': time_description
        }
        
        return result
    except Exception as e:
        logger.error(f"Error al predecir tasas de cambio: {e}")
        return None

def get_historical_price(base_currency, target_currency, period):
    """
    Obtiene el precio histórico de una moneda en un período específico en el pasado.
    """
    try:
        # Calcular la fecha objetivo
        days_ago = 0
        if period['type'] == 'days':
            days_ago = period['value']
        elif period['type'] == 'weeks':
            days_ago = period['value'] * 7
        elif period['type'] == 'months':
            days_ago = period['value'] * 30
        
        target_date = datetime.now() - timedelta(days=days_ago)
        
        # Obtener la tasa en esa fecha
        rate_data = get_rate_at_date(base_currency, target_currency, target_date)
        
        if not rate_data:
            logger.error(f"No se encontraron datos para {base_currency}/{target_currency} hace {days_ago} días.")
            return None
        
        # Obtener la tasa actual para comparación
        current_quote = get_forex_quote(base_currency, target_currency)
        
        if not current_quote:
            logger.error(f"No se pudo obtener la cotización actual para {base_currency}/{target_currency}.")
            return None
        
        # Calcular el cambio porcentual
        change_percentage = ((current_quote['mid_price'] - rate_data['mid_price']) / rate_data['mid_price']) * 100
        
        # Descripción del período
        time_description = f"{period['value']} día(s)"
        if period['type'] == 'weeks':
            time_description = f"{period['value']} semana(s)"
        elif period['type'] == 'months':
            time_description = f"{period['value']} mes(es)"
        
        return {
            'base_currency': base_currency,
            'target_currency': target_currency,
            'historical_date': rate_data['date'],
            'historical_rate': rate_data['mid_price'],
            'current_rate': current_quote['mid_price'],
            'change_value': current_quote['mid_price'] - rate_data['mid_price'],
            'change_percentage': change_percentage,
            'time_description': time_description
        }
    
    except Exception as e:
        logger.error(f"Error al obtener precio histórico: {e}")
        return None

def compare_currency_periods(base_currency, target_currency, period1, period2=None):
    """
    Compara el valor de una moneda en dos períodos diferentes.
    Si period2 es None, se compara con el valor actual.
    """
    try:
        # Calcular las fechas objetivo
        days_ago1 = 0
        if period1['type'] == 'days':
            days_ago1 = period1['value']
        elif period1['type'] == 'weeks':
            days_ago1 = period1['value'] * 7
        elif period1['type'] == 'months':
            days_ago1 = period1['value'] * 30
        
        target_date1 = datetime.now() - timedelta(days=days_ago1)
        rate_data1 = get_rate_at_date(base_currency, target_currency, target_date1)
        
        if not rate_data1:
            logger.error(f"No se encontraron datos para {base_currency}/{target_currency} hace {days_ago1} días.")
            return None
        
        if period2:
            # Calcular la segunda fecha
            days_ago2 = 0
            if period2['type'] == 'days':
                days_ago2 = period2['value']
            elif period2['type'] == 'weeks':
                days_ago2 = period2['value'] * 7
            elif period2['type'] == 'months':
                days_ago2 = period2['value'] * 30
            
            target_date2 = datetime.now() - timedelta(days=days_ago2)
            rate_data2 = get_rate_at_date(base_currency, target_currency, target_date2)
            
            if not rate_data2:
                logger.error(f"No se encontraron datos para {base_currency}/{target_currency} hace {days_ago2} días.")
                return None
            
            # Descripción de los períodos
            time_description1 = f"{period1['value']} día(s)"
            if period1['type'] == 'weeks':
                time_description1 = f"{period1['value']} semana(s)"
            elif period1['type'] == 'months':
                time_description1 = f"{period1['value']} mes(es)"
            
            time_description2 = f"{period2['value']} día(s)"
            if period2['type'] == 'weeks':
                time_description2 = f"{period2['value']} semana(s)"
            elif period2['type'] == 'months':
                time_description2 = f"{period2['value']} mes(es)"
            
            # Calcular el cambio porcentual
            change_percentage = ((rate_data2['mid_price'] - rate_data1['mid_price']) / rate_data1['mid_price']) * 100
            
            return {
                'base_currency': base_currency,
                'target_currency': target_currency,
                'period1': {
                    'description': f"Hace {time_description1}",
                    'date': rate_data1['date'],
                    'rate': rate_data1['mid_price']
                },
                'period2': {
                    'description': f"Hace {time_description2}",
                    'date': rate_data2['date'],
                    'rate': rate_data2['mid_price']
                },
                'change_value': rate_data2['mid_price'] - rate_data1['mid_price'],
                'change_percentage': change_percentage
            }
        else:
            # Comparar con el valor actual
            current_quote = get_forex_quote(base_currency, target_currency)
            
            if not current_quote:
                logger.error(f"No se pudo obtener la cotización actual para {base_currency}/{target_currency}.")
                return None
            
            # Calcular el cambio porcentual
            change_percentage = ((current_quote['mid_price'] - rate_data1['mid_price']) / rate_data1['mid_price']) * 100
            
            # Descripción del período
            time_description1 = f"{period1['value']} día(s)"
            if period1['type'] == 'weeks':
                time_description1 = f"{period1['value']} semana(s)"
            elif period1['type'] == 'months':
                time_description1 = f"{period1['value']} mes(es)"
            
            return {
                'base_currency': base_currency,
                'target_currency': target_currency,
                'period1': {
                    'description': f"Hace {time_description1}",
                    'date': rate_data1['date'],
                    'rate': rate_data1['mid_price']
                },
                'current_period': {
                    'description': "Actual",
                    'date': current_quote['timestamp'],
                    'rate': current_quote['mid_price']
                },
                'change_value': current_quote['mid_price'] - rate_data1['mid_price'],
                'change_percentage': change_percentage
            }
    
    except Exception as e:
        logger.error(f"Error al comparar períodos: {e}")
        return None