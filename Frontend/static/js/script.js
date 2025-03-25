// Mostrar fecha actual
const currentDateElement = document.getElementById("current-date")
const options = { weekday: "long", year: "numeric", month: "long", day: "numeric" }
currentDateElement.textContent = new Date().toLocaleDateString("es-ES", options)

// Toggle sidebar en móvil
document.getElementById("sidebarToggle").addEventListener("click", () => {
  document.querySelector(".sidebar").classList.toggle("active")
})

// Cerrar sidebar al hacer clic fuera de ella
document.addEventListener("click", (event) => {
  const sidebar = document.querySelector(".sidebar")
  const sidebarToggle = document.getElementById("sidebarToggle")

  if (
    sidebar.classList.contains("active") &&
    !sidebar.contains(event.target) &&
    event.target !== sidebarToggle &&
    !sidebarToggle.contains(event.target)
  ) {
    sidebar.classList.remove("active")
  }
})

// Modificar la función para cargar noticias reales
function loadForexNews() {
  const newsContainer = document.getElementById("news-container")
  newsContainer.innerHTML =
    '<div class="loading-news"><i class="fas fa-spinner fa-spin"></i> Cargando noticias...</div>'

  fetch("/get_forex_news")
    .then((response) => response.json())
    .then((data) => {
      newsContainer.innerHTML = ""

      if (data.error) {
        newsContainer.innerHTML = `<div class="news-error"><i class="fas fa-exclamation-circle"></i> ${data.error}</div>`
        return
      }

      if (!data.news || data.news.length === 0) {
        newsContainer.innerHTML = '<div class="news-error">No hay noticias disponibles en este momento.</div>'
        return
      }

      data.news.forEach((news) => {
        // Formatear la fecha
        const publishDate = new Date(news.time_published)
        const formattedDate = publishDate.toLocaleDateString("es-ES", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        })

        // Limitar el resumen a 120 caracteres
        const summary = news.summary.length > 120 ? news.summary.substring(0, 120) + "..." : news.summary

        const newsItem = document.createElement("div")
        newsItem.className = "news-item"
        newsItem.innerHTML = `
                    <div class="news-title">${news.title}</div>
                    <div class="news-date"><i class="far fa-clock"></i> ${formattedDate}</div>
                    <div class="news-summary">${summary}</div>
                    <div class="news-tags">
                        ${news.currencies.map((currency) => `<span class="currency-badge">${currency}</span>`).join("")}
                    </div>
                    <a href="${news.url}" target="_blank" class="news-link">Leer más <i class="fas fa-external-link-alt"></i></a>
                `
        newsContainer.appendChild(newsItem)
      })
    })
    .catch((error) => {
      console.error("Error al cargar noticias:", error)
      newsContainer.innerHTML =
        '<div class="news-error"><i class="fas fa-exclamation-circle"></i> Error al cargar noticias.</div>'
    })
}

// Modificar el evento de clic para el botón de actualizar noticias
document.getElementById("refreshNews").addEventListener("click", function () {
  this.querySelector("i").classList.add("fa-spin")
  loadForexNews()
  setTimeout(() => {
    this.querySelector("i").classList.remove("fa-spin")
  }, 1000)
})

// Modificar la función de manejo del formulario para manejar respuestas desconocidas
document.getElementById("forexForm").addEventListener("submit", (event) => {
  event.preventDefault()
  const userInput = document.getElementById("user_input").value

  if (!userInput.trim()) return

  // Crear mensaje del usuario
  const chatContainer = document.querySelector(".chat-container")
  const userMessageDiv = document.createElement("div")
  userMessageDiv.className = "message user-message"
  userMessageDiv.textContent = userInput
  chatContainer.appendChild(userMessageDiv)

  // Limpiar el input
  document.getElementById("user_input").value = ""

  // Mostrar el div de resultado
  const resultDiv = document.getElementById("result")
  resultDiv.style.display = "block"
  resultDiv.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; gap: 10px;">
        <i class="fas fa-spinner fa-spin"></i> Procesando solicitud...
    </div>`

  // Limpiar el gráfico
  document.getElementById("graph").innerHTML = ""

  // Desplazarse hacia abajo
  chatContainer.scrollTop = chatContainer.scrollHeight

  fetch("/get_forex_data", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_input: userInput }),
  })
    .then((response) => {
      // Verificar el tipo de contenido
      const contentType = response.headers.get("content-type")

      if (contentType && contentType.includes("application/json")) {
        return response.json().then((data) => ({ data, isJson: true }))
      } else if (contentType && contentType.includes("image/png")) {
        return response.blob().then((blob) => ({ data: blob, isJson: false }))
      } else {
        throw new Error("Formato de respuesta no reconocido")
      }
    })
    .then(({ data, isJson }) => {
      // Eliminar el mensaje de "Procesando solicitud"
      resultDiv.innerHTML = "" // Limpiar el contenido del div de resultados
      // Crear un nuevo div para la respuesta del bot
      const botMessageDiv = document.createElement("div")
      botMessageDiv.className = "message bot-message" // Puedes agregar una clase para estilizarlo

      if (isJson) {
        // Procesar respuesta JSON
        if (data.error) {
          botMessageDiv.innerHTML = `<p style="color: var(--negative-color);"><i class="fas fa-exclamation-circle"></i> Error: ${data.error}</p>`
        } else if (data.intent === "conversion") {
          // Mostrar resultado de conversión
          const resultHtml = `
                    <h2><i class="fas fa-exchange-alt"></i> Resultado de la Conversión</h2>
                    <p>${data.amount} ${data.from_currency} = <strong style="font-size: 1.2em; color: #e2e8f0;">${data.converted_amount.toFixed(2)} ${data.to_currency}</strong></p>
                    <div style="background-color: var(--secondary-color); border-radius: 8px; padding: 16px; margin-top: 16px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span>Tasa de cambio:</span>
                            <strong>${data.exchange_rate.toFixed(4)}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span>Precio de compra:</span>
                            <strong>${data.bid_price.toFixed(4)}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span>Precio de venta:</span>
                            <strong>${data.ask_price.toFixed(4)}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 0.9em; color: #94a3b8;">
                            <span>Última actualización:</span>
                            <span>${data.timestamp}</span>
                        </div>
                    </div>
                `
          botMessageDiv.innerHTML = resultHtml
        } else if (data.intent === "prediction") {
          // Mostrar resultado de predicción
          let predictionsHtml = `
                    <h2><i class="fas fa-chart-line"></i> Predicción para ${data.base_currency}/${data.target_currency}</h2>
                    <div style="display: flex; align-items: center; margin-bottom: 16px;">
                        <div style="flex: 1; background-color: var(--secondary-color); border-radius: 8px; padding: 16px;">
                            <div style="font-size: 0.9em; color: #94a3b8;">Tasa actual</div>
                            <div style="font-size: 1.5em; font-weight: 600; margin-top: 4px;">${data.current_rate.toFixed(4)}</div>
                        </div>
                        <div style="flex: 1; background-color: var(--secondary-color); border-radius: 8px; padding: 16px; margin-left: 16px;">
                            <div style="font-size: 0.9em; color: #94a3b8;">Tendencia (${data.time_description})</div>
                            <div style="font-size: 1.5em; font-weight: 600; margin-top: 4px; color: ${data.trend_percentage > 0 ? "var(--positive-color)" : "var(--negative-color)"}">
                                ${data.trend_percentage > 0 ? "↑" : "↓"} ${Math.abs(data.trend_percentage).toFixed(2)}%
                            </div>
                        </div>
                    </div>
                    <p>Tendencia: <strong>${data.trend_direction}</strong> para los próximos ${data.time_description}</p>
                    <table class="prediction-table">
                        <thead>
                            <tr>
                                <th>Fecha</th>
                                <th>Tasa prevista</th>
                                <th>Cambio</th>
                            </tr>
                        </thead>
                        <tbody>
                `

          data.predicted_rates.forEach((item) => {
            const change = ((item.rate - data.current_rate) / data.current_rate) * 100
            const changeColor = change > 0 ? "var(--positive-color)" : change < 0 ? "var(--negative-color)" : "#e2e8f0"
            predictionsHtml += `
                        <tr>
                            <td>${item.date}</td>
                            <td>${item.rate.toFixed(4)}</td>
                            <td style="color: ${changeColor}">
                                ${change > 0 ? "+" : ""}${change.toFixed(2)}%
                            </td>
                        </tr>
                    `
          })

          predictionsHtml += `
                        </tbody>
                    </table>
                `
          botMessageDiv.innerHTML = predictionsHtml
        } else if (data.intent === "history") {
          // Mostrar resultado histórico
          const resultHtml = `
                    <h2><i class="fas fa-history"></i> Datos Históricos</h2>
                    <div style="display: flex; margin-bottom: 20px;">
                        <div style="flex: 1; background-color: var(--secondary-color); border-radius: 8px; padding: 16px;">
                            <div style="font-size: 0.9em; color: #94a3b8;">Hace ${data.time_description} (${data.historical_date})</div>
                            <div style="font-size: 1.5em; font-weight: 600; margin-top: 4px;">${data.historical_rate.toFixed(4)} ${data.target_currency}</div>
                        </div>
                        <div style="flex: 1; background-color: var(--secondary-color); border-radius: 8px; padding: 16px; margin-left: 16px;">
                            <div style="font-size: 0.9em; color: #94a3b8;">Actual</div>
                            <div style="font-size: 1.5em; font-weight: 600; margin-top: 4px;">${data.current_rate.toFixed(4)} ${data.target_currency}</div>
                        </div>
                    </div>
                    <div style="background-color: var(--secondary-color); border-radius: 8px; padding: 16px; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-size: 0.9em; color: #94a3b8;">Cambio</div>
                            <div style="font-size: 1.2em; font-weight: 600; margin-top: 4px;">
                                ${data.change_value > 0 ? "+" : ""}${data.change_value.toFixed(4)} ${data.target_currency}
                            </div>
                        </div>
                        <div style="font-size: 1.8em; font-weight: 600; color: ${data.change_percentage > 0 ? "var(--positive-color)" : "var(--negative-color)"}">
                            ${data.change_percentage > 0 ? "↑" : "↓"} ${Math.abs(data.change_percentage).toFixed(2)}%
                        </div>
                    </div>
                `
          botMessageDiv.innerHTML = resultHtml
        } else if (data.intent === "compare") {
          // Mostrar resultado de comparación
          const resultHtml = `
                    <h2><i class="fas fa-balance-scale"></i> Comparación de Precios</h2>
                    <div style="display: flex; margin-bottom: 20px;">
                        <div style="flex: 1; background-color: var(--secondary-color); border-radius: 8px; padding: 16px;">
                            <div style="font-size: 0.9em; color: #94a3b8;">${data.period1.description} (${data.period1.date})</div>
                            <div style="font-size: 1.5em; font-weight: 600; margin-top: 4px;">${data.period1.rate.toFixed(4)} ${data.target_currency}</div>
                        </div>
                        <div style="flex: 1; background-color: var(--secondary-color); border-radius: 8px; padding: 16px; margin-left: 16px;">
                            <div style="font-size: 0.9em; color: #94a3b8;">${data.period2 ? data.period2.description : data.current_period.description}</div>
                            <div style="font-size: 1.5em; font-weight: 600; margin-top: 4px;">${data.period2 ? data.period2.rate.toFixed(4) : data.current_period.rate.toFixed(4)} ${data.target_currency}</div>
                        </div>
                    </div>
                    <div style="background-color: var(--secondary-color); border-radius: 8px; padding: 16px; display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-size: 0.9em; color: #94a3b8;">Cambio</div>
                            <div style="font-size: 1.2em; font-weight: 600; margin-top: 4px;">
                                ${data.change_value > 0 ? "+" : ""}${data.change_value.toFixed(4)} ${data.target_currency}
                            </div>
                        </div>
                        <div style="font-size: 1.8em; font-weight: 600; color: ${data.change_percentage > 0 ? "var(--positive-color)" : "var(--negative-color)"}">
                            ${data.change_percentage > 0 ? "↑" : "↓"} ${Math.abs(data.change_percentage).toFixed(2)}%
                        </div>
                    </div>
                `
          botMessageDiv.innerHTML = resultHtml
        } else if (data.intent === "currencies") {
          // Mostrar monedas disponibles
          let currenciesHtml = `
                    <h2><i class="fas fa-coins"></i> Monedas Disponibles</h2>
                    <p>Estas son las monedas con las que puedo trabajar:</p>
                    <div class="currencies-grid">
                `

          // Agrupar por continentes/regiones para mejor visualización
          const regions = {
            América: ["USD", "CAD", "MXN", "BRL"],
            Europa: ["EUR", "GBP", "CHF"],
            Asia: ["JPY", "CNY"],
            Oceanía: ["AUD"],
          }

          // Crear secciones por región
          for (const [region, codes] of Object.entries(regions)) {
            currenciesHtml += `<div class="currency-region"><h3>${region}</h3><div class="currency-region-grid">`

            // Filtrar las monedas de esta región
            const regionCurrencies = data.currencies.filter((c) => codes.includes(c.code))

            for (const currency of regionCurrencies) {
              currenciesHtml += `
                            <div class="currency-card">
                                <div class="currency-code">${currency.code}</div>
                                <div class="currency-name">${currency.name}</div>
                                ${
                                  currency.aliases.length > 0
                                    ? `<div class="currency-aliases">También conocido como: ${currency.aliases.join(", ")}</div>`
                                    : ""
                                }
                            </div>
                        `
            }

            currenciesHtml += `</div></div>`
          }

          currenciesHtml += `
                    </div>
                    <p class="currency-note">Puedes usar cualquiera de estas monedas en tus consultas de conversión, gráficos, predicciones o comparaciones.</p>
                `
          botMessageDiv.innerHTML = currenciesHtml
        } else if (data.intent === "unknown") {
          // Mostrar mensaje para intenciones desconocidas
          botMessageDiv.innerHTML = `
                    <h2><i class="fas fa-question-circle"></i> No puedo procesar esa solicitud</h2>
                    <p>${data.message}</p>
                    <div style="background-color: var(--secondary-color); border-radius: 8px; padding: 16px; margin-top: 16px;">
                        <p>Puedes pedirme:</p>
                        <ul>
                            <li><i class="fas fa-exchange-alt"></i> <strong>Convertir cantidades entre monedas</strong> (ej: "100 euros a dólares")</li>
                            <li><i class="fas fa-chart-line"></i> <strong>Ver gráficos de tipos de cambio</strong> (ej: "Gráfico de USD/EUR")</li>
                            <li><i class="fas fa-chart-pie"></i> <strong>Obtener predicciones de divisas</strong> (ej: "Predicción del euro para la próxima semana")</li>
                            <li><i class="fas fa-history"></i> <strong>Consultar precios históricos</strong> (ej: "Precio del euro hace 1 mes")</li>
                            <li><i class="fas fa-balance-scale"></i> <strong>Comparar precios</strong> (ej: "Comparar precio del euro hace 1 mes y hace 1 semana")</li>
                            <li><i class="fas fa-coins"></i> <strong>Ver monedas disponibles</strong> (ej: "¿Qué monedas tienes disponibles?")</li>
                        </ul>
                    </div>
                `
        } else {
          botMessageDiv.innerHTML = "<p>Respuesta recibida pero en un formato no esperado.</p>"
        }
      } else {
        // Procesar respuesta de imagen (gráfico)
        botMessageDiv.innerHTML = "<h2><i class='fas fa-chart-line'></i> Gráfico de tipo de cambio</h2>"

        // Contenedor para el gráfico con estilo de Binance
        const graphContainer = document.createElement("div")
        graphContainer.style.backgroundColor = "var(--card-bg)"
        graphContainer.style.borderRadius = "8px"
        graphContainer.style.padding = "20px"
        graphContainer.style.marginTop = "16px"
        graphContainer.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.1)"

        // Crear la imagen
        const img = document.createElement("img")
        img.src = URL.createObjectURL(data)
        img.style.maxWidth = "100%"
        img.style.borderRadius = "4px"
        img.style.border = "1px solid var(--border-color)"

        // Añadir la imagen al contenedor
        graphContainer.appendChild(img)
        botMessageDiv.appendChild(graphContainer)

        // Añadir leyenda
        const legend = document.createElement("div")
        legend.style.marginTop = "16px"
        legend.style.fontSize = "14px"
        legend.style.color = "#94a3b8"
        legend.style.textAlign = "center"
        legend.innerHTML = "Fuente: Datos procesados por ForexAI"
        botMessageDiv.appendChild(legend)
      }

      // Agregar el mensaje del bot al contenedor de chat
      chatContainer.appendChild(botMessageDiv)

      // Desplazarse hacia abajo después de cargar el resultado
      chatContainer.scrollTop = chatContainer.scrollHeight
    })
    .catch((error) => {
      console.error("Error:", error)
      const botMessageDiv = document.createElement("div")
      botMessageDiv.className = "message bot-message"
      botMessageDiv.innerHTML = `<p style="color: var(--negative-color);"><i class="fas fa-exclamation-circle"></i> Error: ${error.message}</p>`
      chatContainer.appendChild(botMessageDiv)
      chatContainer.scrollTop = chatContainer.scrollHeight
    })
})

// Agregar estilos CSS para las monedas disponibles
document.head.insertAdjacentHTML(
  "beforeend",
  `
<style>
.currencies-grid {
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin-top: 16px;
}

.currency-region h3 {
    font-size: 16px;
    margin-bottom: 10px;
    color: var(--primary-color);
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 5px;
}

.currency-region-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
}

.currency-card {
    background-color: var(--secondary-color);
    border-radius: 8px;
    padding: 12px;
    border-left: 3px solid var(--primary-color);
}

.currency-code {
    font-weight: 600;
    font-size: 18px;
    margin-bottom: 4px;
}

.currency-name {
    font-size: 14px;
    color: #e2e8f0;
}

.currency-aliases {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 6px;
}

.currency-note {
    margin-top: 16px;
    font-style: italic;
    color: #94a3b8;
}

.news-link {
    display: inline-block;
    margin-top: 8px;
    color: var(--primary-color);
    font-size: 13px;
    text-decoration: none;
}

.news-link:hover {
    text-decoration: underline;
}

.loading-news, .news-error {
    padding: 20px;
    text-align: center;
    color: #94a3b8;
}
</style>
`,
)

// Ajustar automáticamente la altura del input
const inputElement = document.getElementById("user_input")
inputElement.addEventListener("input", function () {
  this.style.height = "auto"
  this.style.height = this.scrollHeight + "px"
})

// Cargar datos de divisas (simulado)
function loadCurrencyData() {
  // En un entorno real, estos datos vendrían de una API
  const currencyData = [
    { pair: "EUR/USD", value: 1.0804, change: 0.12 },
    { pair: "GBP/USD", value: 1.3245, change: 0.08 },
    { pair: "USD/JPY", value: 148.64, change: -0.21 },
    { pair: "USD/CHF", value: 0.8808, change: -0.05 },
    { pair: "AUD/USD", value: 0.6305, change: -0.15 },
    { pair: "USD/CAD", value: 1.4295, change: 0.03 },
  ]

  const currencyList = document.getElementById("currency-list")
  currencyList.innerHTML = ""

  currencyData.forEach((currency) => {
    const item = document.createElement("div")
    item.className = "currency-item"
    item.innerHTML = `
            <div class="currency-name">${currency.pair}</div>
            <div>
                <span class="currency-value">${currency.value.toFixed(4)}</span>
                <span class="currency-change ${currency.change >= 0 ? "positive" : "negative"}">
                    ${currency.change >= 0 ? "+" : ""}${currency.change.toFixed(2)}%
                </span>
            </div>
        `
    currencyList.appendChild(item)
  })
}

// Cargar noticias al iniciar
loadForexNews()

// Cargar datos al iniciar
loadCurrencyData()