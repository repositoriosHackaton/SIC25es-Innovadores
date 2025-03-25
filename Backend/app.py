# app.py
from flask import Flask, render_template, request, jsonify
from bot_functions import *

app = Flask(__name__, template_folder='../Frontend', static_folder='../Frontend/static')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_forex_data', methods=['POST'])
def get_forex_data():
    data = request.get_json()
    if not data:
        logger.error("No se recibieron datos en la solicitud.")
        return jsonify({"error": "No se recibieron datos en la solicitud."}), 400

    user_input = data.get('user_input')
    if not user_input:
        logger.error("Falta el campo 'user_input' en la solicitud.")
        return jsonify({"error": "Falta el campo 'user_input' en la solicitud."}), 400

    logger.info(f"user_input recibido: {user_input}")

    # Detectar la intención del usuario
    intent = detect_intent(user_input)

    if intent == "conversion":
        # Procesar la solicitud de conversión
        amount, source_currency, target_currency = check_conversion_request(user_input)
        if not amount or not source_currency or not target_currency:
            return jsonify({"error": "No se pudo procesar la solicitud. Asegúrate de usar un formato como '100 euros a dólares'."}), 400

        # Obtener la cotización
        quote = get_forex_quote(source_currency, target_currency)
        if quote:
            converted_amount = amount * quote['mid_price']
            response = {
                "intent": "conversion",
                "amount": amount,
                "from_currency": source_currency,
                "to_currency": target_currency,
                "converted_amount": converted_amount,
                "exchange_rate": quote['mid_price'],
                "bid_price": quote['bid_price'],
                "ask_price": quote['ask_price'],
                "timestamp": quote['timestamp']
            }
            return jsonify(response)
        else:
            return jsonify({"error": "Could not fetch forex data. Please check the currencies and try again."}), 500

    elif intent == "graph":
        # Lógica para gráfico
        currencies = detect_currencies(user_input)
        if len(currencies) >= 2:
            base_currency, target_currency = currencies[0], currencies[1]
        elif len(currencies) == 1:
            base_currency, target_currency = currencies[0], "USD"
        else:
            base_currency, target_currency = "USD", "EUR"

        # Detectar el período de tiempo
        period = detect_time_period(user_input)
        
        # Generar el gráfico
        graph_buffer = generate_rate_graph(base_currency, target_currency, period)
        if graph_buffer:
            return graph_buffer.getvalue(), 200, {'Content-Type': 'image/png'}
        else:
            return jsonify({"error": "Could not generate graph. Please try again later."}), 500
        
    elif intent == "prediction":
        # Procesar la solicitud de predicción
        currencies = detect_currencies(user_input)
        if len(currencies) >= 2:
            base_currency, target_currency = currencies[0], currencies[1]
        elif len(currencies) == 1:
            base_currency, target_currency = currencies[0], "USD"
        else:
            base_currency, target_currency = "USD", "EUR"

        # Detectar el período de tiempo
        period = detect_time_period(user_input)
        
        # Obtener la predicción
        prediction = predict_rates(base_currency, target_currency, period)
        if prediction:
            response = {
                "intent": "prediction",
                "base_currency": base_currency,
                "target_currency": target_currency,
                "current_rate": prediction['current_rate'],
                "predicted_rates": prediction['predicted_rates'],
                "trend_percentage": prediction['trend_percentage'],
                "trend_direction": prediction['trend_direction'],
                "time_description": prediction['time_description']
            }
            return jsonify(response)
        else:
            return jsonify({"error": "Could not generate prediction. Please try again later."}), 500

    elif intent == "history":
        # Procesar la solicitud de histórico
        currencies = detect_currencies(user_input)
        if len(currencies) >= 2:
            base_currency, target_currency = currencies[0], currencies[1]
        elif len(currencies) == 1:
            base_currency, target_currency = currencies[0], "USD"
        else:
            base_currency, target_currency = "USD", "EUR"

        # Detectar el período de tiempo
        period = detect_time_period(user_input)
        
        # Obtener datos históricos
        historical_data = get_historical_price(base_currency, target_currency, period)
        if historical_data:
            response = {
                "intent": "history",
                "base_currency": base_currency,
                "target_currency": target_currency,
                "historical_date": historical_data['historical_date'],
                "historical_rate": historical_data['historical_rate'],
                "current_rate": historical_data['current_rate'],
                "change_value": historical_data['change_value'],
                "change_percentage": historical_data['change_percentage'],
                "time_description": historical_data['time_description']
            }
            return jsonify(response)
        else:
            return jsonify({"error": "Could not fetch historical data. Please try again later."}), 500

    elif intent == "compare":
        # Procesar la solicitud de comparación
        currencies = detect_currencies(user_input)
        if len(currencies) >= 2:
            base_currency, target_currency = currencies[0], currencies[1]
        elif len(currencies) == 1:
            base_currency, target_currency = currencies[0], "USD"
        else:
            base_currency, target_currency = "USD", "EUR"

        # Detectar los períodos de tiempo
        period1 = detect_time_period(user_input)
        period2 = detect_time_period(user_input.split("y")[1]) if "y" in user_input else None
        
        # Obtener la comparación
        comparison = compare_currency_periods(base_currency, target_currency, period1, period2)
        if comparison:
            return jsonify(comparison)
        else:
            return jsonify({"error": "Could not compare currency periods. Please try again later."}), 500
    
    elif intent == "currencies":
        # Procesar la solicitud de monedas disponibles
        currencies = get_available_currencies()
        if currencies:
            response = {
                "intent": "currencies",
                "currencies": currencies
            }
            return jsonify(response)
        else:
            return jsonify({"error": "No se pudieron obtener las monedas disponibles."}), 500

    else:
        # Intención desconocida o no relacionada con divisas
        return jsonify({
            "intent": "unknown",
            "message": "Lo siento, no puedo procesar esa solicitud. Soy un asistente especializado en divisas. Puedes preguntarme sobre conversiones, gráficos, predicciones, datos históricos o comparaciones de monedas."
        })

# Agregar una nueva ruta para obtener noticias de divisas
@app.route('/get_forex_news', methods=['GET'])
def get_news():
    news = get_forex_news()
    if news:
        return jsonify({"news": news})
    else:
        return jsonify({"error": "No se pudieron obtener noticias de divisas."}), 500

if __name__ == '__main__':
    app.run(debug=True)