const glyphs = {
  clear: '<svg viewBox="0 0 48 48"><circle cx="24" cy="24" r="8"/><path d="M24 4v6m0 28v6M4 24h6m28 0h6M9.9 9.9l4.2 4.2m19.8 19.8 4.2 4.2m0-28.2-4.2 4.2m-19.8 19.8-4.2 4.2"/></svg>',
  night: '<svg viewBox="0 0 48 48"><path d="M34.8 29.8A17 17 0 0 1 18.2 13.2 16.5 16.5 0 1 0 34.8 29.8Z"/><path d="m34 8 .8 2.2L37 11l-2.2.8L34 14l-.8-2.2L31 11l2.2-.8L34 8Z"/></svg>',
  clouds: '<svg viewBox="0 0 48 48"><path d="M13 34h21a8 8 0 0 0 .7-16 12 12 0 0 0-22.8 3.2A6.5 6.5 0 0 0 13 34Z"/></svg>',
  fog: '<svg viewBox="0 0 48 48"><path d="M12 27h23a7 7 0 0 0 .6-14 10 10 0 0 0-19 2.7A5.5 5.5 0 0 0 12 27Z"/><path d="M9 34h27m-23 5h19"/></svg>',
  rain: '<svg viewBox="0 0 48 48"><path d="M12 28h23a7 7 0 0 0 .6-14 10 10 0 0 0-19 2.7A5.5 5.5 0 0 0 12 28Z"/><path d="m18 33-2 5m11-5-2 5m11-5-2 5"/></svg>',
  snow: '<svg viewBox="0 0 48 48"><path d="M12 27h23a7 7 0 0 0 .6-14 10 10 0 0 0-19 2.7A5.5 5.5 0 0 0 12 27Z"/><path d="M18 33v8m-3-2 6-4m-6 0 6 4m8-6v8m-3-2 6-4m-6 0 6 4"/></svg>',
  storm: '<svg viewBox="0 0 48 48"><path d="M12 26h23a7 7 0 0 0 .6-14 10 10 0 0 0-19 2.7A5.5 5.5 0 0 0 12 26Z"/><path d="m25 27-6 10h6l-2 7 9-12h-6l3-5"/></svg>',
};

let weatherNow = null;
let fahrenheit = false;
let activeCity = "Москва";
let toastTimer;

function temperature(value) {
  const converted = fahrenheit ? Math.round(value * 9 / 5 + 32) : Math.round(value);
  return `${converted}°`;
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 3600);
}

async function loadWeather(city) {
  document.body.classList.add("loading");
  try {
    const response = await fetch(`/api/weather?city=${encodeURIComponent(city)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Не удалось загрузить прогноз.");
    weatherNow = data;
    activeCity = city;
    renderWeather(data);
    document.getElementById("city-input").value = "";
  } catch (error) {
    showToast(error.message || "Не удалось подключиться к прогнозу.");
  } finally {
    document.body.classList.remove("loading");
  }
}

function renderWeather(data) {
  document.getElementById("city-name").textContent = data.city;
  document.getElementById("region-name").textContent = data.subtitle || "";
  document.getElementById("date-label").textContent = data.date;
  document.getElementById("temperature").innerHTML = `${temperature(data.temperature).slice(0,-1)}<sup>°</sup>`;
  document.getElementById("description").textContent = data.description;
  document.getElementById("range").textContent = `от ${temperature(data.low)} до ${temperature(data.high)}`;
  document.getElementById("feels-like").textContent = temperature(data.feels_like);
  document.getElementById("wind").textContent = `${data.wind} км/ч`;
  document.getElementById("humidity").textContent = `${data.humidity}%`;
  document.getElementById("updated").textContent = `Местное время · ${data.updated}`;
  document.getElementById("weather-glyph").innerHTML = glyphs[data.scene] || glyphs.clear;

  document.body.dataset.scene = data.scene;
  document.body.dataset.time = data.daypart || (data.is_day ? "day" : "night");
  document.getElementById("hours").innerHTML = data.hourly.map((hour) => {
    const scene = weatherScene(hour.code);
    const icon = glyphs[scene] || glyphs.clear;
    const chance = hour.precipitation > 0 ? `<span class="hour-rain">${hour.precipitation}% осадки</span>` : "";
    return `<div class="hour"><span class="hour-time">${hour.time}</span><span class="hour-icon">${icon}</span><span class="hour-temp">${temperature(hour.temperature)}</span>${chance}</div>`;
  }).join("");
}

function weatherScene(code) {
  if ([0, 1].includes(code)) return "clear";
  if ([2, 3].includes(code)) return "clouds";
  if ([45, 48].includes(code)) return "fog";
  if ([56, 57, 71, 73, 75, 77, 85, 86].includes(code)) return "snow";
  if (code >= 95) return "storm";
  if (code >= 51) return "rain";
  return "clouds";
}

document.getElementById("search-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const city = document.getElementById("city-input").value.trim();
  if (city) loadWeather(city);
});

document.querySelectorAll("[data-city]").forEach((button) => {
  button.addEventListener("click", () => loadWeather(button.dataset.city));
});

document.getElementById("unit-toggle").addEventListener("click", (event) => {
  if (!weatherNow) return;
  fahrenheit = !fahrenheit;
  event.currentTarget.setAttribute("aria-pressed", String(fahrenheit));
  renderWeather(weatherNow);
});

loadWeather("Москва");
setInterval(() => loadWeather(activeCity), 30 * 60 * 1000);
