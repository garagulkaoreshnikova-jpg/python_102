from datetime import datetime, timedelta
from difflib import SequenceMatcher
import json
import os
import re
import ssl
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

WEATHER = {
    0: ("Ясно", "clear", "Небо сегодня особенно щедро на свет."),
    1: ("Преимущественно ясно", "clear", "Мягкое солнце и лёгкая дымка над горизонтом."),
    2: ("Переменная облачность", "clouds", "Облака неспешно плывут над городом."),
    3: ("Облачно", "clouds", "Небо укрылось спокойной облачной вуалью."),
    45: ("Туман", "fog", "Город растворяется в серебристой дымке."),
    48: ("Изморозь и туман", "fog", "Туман оставил на воздухе тонкий морозный узор."),
    51: ("Лёгкая морось", "rain", "Едва заметные капли мерцают в воздухе."),
    53: ("Морось", "rain", "Неспешный дождь наполняет улицы свежестью."),
    55: ("Сильная морось", "rain", "Мелкий дождь укрывает город прохладной вуалью."),
    56: ("Ледяная морось", "snow", "Воздух холоден, а капли превращаются в лёд."),
    57: ("Сильная ледяная морось", "snow", "Осторожно: на улицах может быть скользко."),
    61: ("Небольшой дождь", "rain", "Тёплые капли рисуют круги на воде."),
    63: ("Дождь", "rain", "Дождливый день — повод замедлиться и выдохнуть."),
    65: ("Сильный дождь", "rain", "За окном разыгралась настоящая стихия."),
    66: ("Ледяной дождь", "snow", "На дорогах возможен гололёд."),
    67: ("Сильный ледяной дождь", "snow", "Будьте осторожны: очень скользко."),
    71: ("Небольшой снег", "snow", "Первый снег ложится на землю тихими мазками."),
    73: ("Снег", "snow", "Снежный пейзаж будто сошёл со старого полотна."),
    75: ("Сильный снег", "snow", "За окном рождается белая зимняя сказка."),
    77: ("Снежные зёрна", "snow", "Мелкие льдинки сверкают в холодном воздухе."),
    80: ("Кратковременный дождь", "rain", "Солнце и дождь сменяют друг друга."),
    81: ("Ливень", "rain", "Небо щедро делится дождём."),
    82: ("Сильный ливень", "rain", "Сильный дождь ненадолго меняет все планы."),
    85: ("Снежный заряд", "snow", "Снежные облака укрывают окрестности."),
    86: ("Сильный снегопад", "snow", "Снегопад превратил город в зимнюю картину."),
    95: ("Гроза", "storm", "Вдалеке гремит гром и сверкают молнии."),
    96: ("Гроза с градом", "storm", "Гроза может сопровождаться градом."),
    99: ("Сильная гроза с градом", "storm", "Переждите грозу в безопасном месте."),
}

WEEKDAYS = ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье")
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")


def fetch_json(url):
    req = Request(url, headers={"User-Agent": "WeatherCanvas/1.0"})
    with urlopen(req, timeout=12, context=ssl.create_default_context(cafile=certifi.where())) as response:
        return json.loads(response.read().decode("utf-8"))


CITY_ALIASES = {
    "маями": ("Miami", "Майами"),
    "майами": ("Miami", "Майами"),
}

CYRILLIC_TO_LATIN = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})


def normalize_city(value):
    return re.sub(r"[^a-zа-я0-9]+", "", value.casefold().replace("ё", "е"))


def find_place(city):
    normalized = normalize_city(city)
    alias = CITY_ALIASES.get(normalized)
    if alias:
        queries = [(alias[0], "en")]
    elif re.search(r"[а-яё]", city, re.IGNORECASE):
        queries = [(city, "ru"), (city.casefold().translate(CYRILLIC_TO_LATIN), "en")]
    else:
        queries = [(city, "en"), (city, "ru")]

    candidates = []
    for query, language in queries:
        data = fetch_json("https://geocoding-api.open-meteo.com/v1/search?" + urlencode({
            "name": query, "count": 10, "language": language, "format": "json"
        }))
        for place in data.get("results", []):
            place_name = place.get("name", "")
            name_norm = normalize_city(place_name)
            query_norm = normalize_city(query)
            name_latin = normalize_city(place_name.casefold().translate(CYRILLIC_TO_LATIN))
            query_latin = normalize_city(query.casefold().translate(CYRILLIC_TO_LATIN))
            similarity = max(
                SequenceMatcher(None, query_norm, name_norm).ratio(),
                SequenceMatcher(None, query_latin, name_latin).ratio(),
            )
            exact = query_norm == name_norm or query_latin == name_latin
            feature = place.get("feature_code", "")
            population = place.get("population", 0) or 0
            score = (1000 if exact else similarity * 100) + (8 if feature in {"PPLC", "PPLA", "PPLA2", "PPL"} else 0) + min(population / 1_000_000, 5)
            candidates.append((score, place))

        # An exact city name wins immediately; later transliterated results
        # should not replace a correctly localized match.
        exact_places = [item for item in candidates if item[0] >= 1000]
        if exact_places:
            break

    if not candidates:
        return None, alias[1] if alias else None
    score, place = max(candidates, key=lambda item: item[0])
    if score < 78:
        return None, alias[1] if alias else None
    if alias:
        return place, alias[1]
    if language == "en" and re.search(r"[а-яё]", city, re.IGNORECASE):
        return place, city.strip().title()
    return place, None


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/weather")
def get_weather():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify(error="Введите название города."), 400

    try:
        place, display_name = find_place(city)
        if not place:
            return jsonify(error=f"Не удалось найти город «{city}». Проверьте название."), 404

        forecast = fetch_json("https://api.open-meteo.com/v1/forecast?" + urlencode({
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
            "hourly": "temperature_2m,precipitation_probability,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset",
            "forecast_days": 1,
            "timezone": "auto",
        }))

        current = forecast["current"]
        code = current["weather_code"]
        description, scene, mood = WEATHER.get(code, ("Переменная погода", "clouds", "Пейзаж дня меняется каждый час."))
        parsed_time = datetime.fromisoformat(current["time"])
        hourly = forecast.get("hourly", {})
        slots = []
        for index, hour in enumerate(hourly.get("time", [])):
            parsed_hour = datetime.fromisoformat(hour)
            if parsed_hour < parsed_time.replace(minute=0, second=0, microsecond=0):
                continue
            slots.append({
                "time": "Сейчас" if parsed_hour.hour == parsed_time.hour else f"{parsed_hour.hour:02d}:00",
                "temperature": round(hourly["temperature_2m"][index]),
                "precipitation": hourly["precipitation_probability"][index],
                "code": hourly["weather_code"][index],
            })
            if len(slots) == 6:
                break

        daily = forecast.get("daily", {})
        day_index = 0
        city_label = display_name or place["name"]
        subtitle = ", ".join(filter(None, [place.get("admin1"), place.get("country")] ))
        sunrise = datetime.fromisoformat(daily["sunrise"][day_index])
        sunset = datetime.fromisoformat(daily["sunset"][day_index])
        if sunrise - timedelta(hours=1) <= parsed_time < sunrise + timedelta(hours=2):
            daypart = "dawn"
        elif sunset - timedelta(hours=2) <= parsed_time < sunset + timedelta(hours=1):
            daypart = "dusk"
        elif current["is_day"] != 1:
            daypart = "night"
        else:
            daypart = "day"
        return jsonify({
            "city": city_label,
            "subtitle": subtitle,
            "temperature": round(current["temperature_2m"]),
            "feels_like": round(current["apparent_temperature"]),
            "description": description,
            "mood": mood,
            "humidity": current["relative_humidity_2m"],
            "wind": round(current["wind_speed_10m"]),
            "precipitation": current["precipitation"],
            "high": round(daily["temperature_2m_max"][day_index]),
            "low": round(daily["temperature_2m_min"][day_index]),
            "sunrise": daily["sunrise"][day_index][-5:],
            "sunset": daily["sunset"][day_index][-5:],
            "date": f"{WEEKDAYS[parsed_time.weekday()]}, {parsed_time.day} {MONTHS[parsed_time.month - 1]}",
            "updated": parsed_time.strftime("%H:%M"),
            "scene": scene,
            "daypart": daypart,
            "is_day": current["is_day"] == 1,
            "hourly": slots,
        })
    except (TimeoutError, OSError, KeyError, ValueError, IndexError) as error:
        app.logger.warning("Weather request failed: %s", error)
        return jsonify(error="Не удалось получить прогноз. Проверьте подключение и попробуйте ещё раз."), 502


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5050")),
        debug=False,
    )
