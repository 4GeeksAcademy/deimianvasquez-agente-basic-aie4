import json
import os
from dotenv import load_dotenv
from datetime import datetime
import requests


load_dotenv()


max_iterations = 5

API_KEY = os.getenv("WEATHER_API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")
LITE_LLM = os.getenv("LITE_LLM")


# https://api.openweathermap.org/data/2.5/weathe


SYSTEM_PROMPT = """
Eres un agente del clima. Tienes dos herramientas:
- get_weather: devuelve el clima actual de una ciudad.
- get_forecast: devuelve el pronóstico de los próximos días de una ciudad.

Responde solo con JSON, en uno de estos formatos:
{"type": "tool_call", "tool": "get_weather", "args": {"city": "caracas"}}
{"type": "tool_call", "tool": "get_forecast", "args": {"city": "caracas"}}
{"type": "final_answer", "content": "tu respuesta"}

Si preguntan por el clima de ahora, llama a get_weather.
Si preguntan por mañana o los próximos días, llama a get_forecast.
Si el nombre de la ciudad tiene un error evidente, corrígelo antes de llamar a la herramienta. Por ejemplo, "karacas venezuela" es "Caracas".
Si la memoria ya trae el resultado, responde con final_answer.
"""


def get_weather(city):
    if not API_KEY:
        return "Falta WEATHER_API_KEY en el archivo .env."

    url = "https://api.openweathermap.org/data/2.5/weather"
    try:
        response = requests.get(
            url,
            params={
                "q": city,
                "units": "metric",
                "lang": "es",
                "appid": API_KEY,
            },
            timeout=10,
        )
        if response.status_code != 200:
            return f"No tengo el clima de {city}."

        data = response.json()
        temp = round(data["main"]["temp"])
        description = data["weather"][0]["description"]
        name = data["name"]
        country = data.get("sys", {}).get("country")
    except requests.RequestException, KeyError, IndexError, TypeError:
        return f"No pude leer el clima de {city}."

    place = f"{name} ({country})" if country else name
    return f"El clima en {place} es {temp}°C, {description}."


def get_forecast(city):
    if not API_KEY:
        return "Falta WEATHER_API_KEY en el archivo .env."

    url = "https://api.openweathermap.org/data/2.5/forecast"
    try:
        response = requests.get(
            url,
            params={
                "q": city,
                "units": "metric",
                "lang": "es",
                "appid": API_KEY,
            },
            timeout=10,
        )
        if response.status_code != 200:
            return f"No tengo el pronóstico de {city}."

        data = response.json()
        name = data["city"]["name"]
        country = data["city"].get("country")
        days = []
        seen = set()
        for item in data["list"]:
            day = item["dt_txt"][:10]
            if day in seen:
                continue
            seen.add(day)
            temp = round(item["main"]["temp"])
            description = item["weather"][0]["description"]
            days.append(f"{day}: {temp}°C, {description}")
            if len(days) == 3:
                break
    except requests.RequestException, KeyError, IndexError, TypeError:
        return f"No pude leer el pronóstico de {city}."

    summary = "; ".join(days)
    place = f"{name} ({country})" if country else name
    return f"Pronóstico en {place}: {summary}."


tools = {
    "get_weather": get_weather,
    "get_forecast": get_forecast,
}

def parse_decision(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)



def call_llm(memory):
    if not LITE_LLM or not MODEL or not BASE_URL:
        return {"type": "final_answer", "content": "Falta la configuración del modelo en el archivo .env."}, {}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": memory[0]})
    for result in memory[1:]:
        messages.append({"role": "user", "content": f"Resultado de la herramienta: {result}"})

    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {LITE_LLM}"},
        json={"model": MODEL, "messages": messages},
        timeout=30,
    )
    if response.status_code != 200:
        return {"type": "final_answer", "content": "No pude consultar el modelo."}, {}

    body = response.json()
    text = body["choices"][0]["message"]["content"]
    usage = body.get("usage") or {}
    return parse_decision(text), usage

def write_log(text):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs.txt", "a", encoding="utf-8") as file:
        file.write(f"[{stamp}] {text}\n")



def run_agent(user_input):
    memory = [user_input]
    tokens_total = 0
    write_log(f"Pregunta: {user_input}")

    for i in range(max_iterations):
        try:
            response, usage = call_llm(memory)
            response_type = response["type"]
        except (requests.RequestException, json.JSONDecodeError, KeyError, TypeError):
            answer = "El modelo no respondió con un JSON válido."
            write_log(f"Respuesta: {answer}")
            return answer

        if usage:
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            total = usage.get("total_tokens", prompt + completion)
            tokens_total += total
            write_log(f"Tokens: {prompt} de entrada, {completion} de salida, {total} en total")

        print(f"[Iteración {i}] Decisión: {response_type}")

        if response_type == "final_answer":
            answer = response.get("content", "")
            write_log(f"Respuesta: {answer}")
            write_log(f"Tokens de la consulta: {tokens_total}")
            return answer

        tool_name = response.get("tool")
        if response_type != "tool_call" or tool_name not in tools:
            answer = "El modelo no respondió con una acción válida."
            write_log(f"Respuesta: {answer}")
            write_log(f"Tokens de la consulta: {tokens_total}")
            return answer

        city = (response.get("args") or {}).get("city", "")
        result = tools[tool_name](city)
        print(f"[Iteración {i}] {tool_name}({city}) -> {result}")
        write_log(f"{tool_name}({city}) -> {result}")
        memory.append(result)

    answer = "Se alcanzó el máximo de iteraciones."
    write_log(f"Respuesta: {answer}")
    write_log(f"Tokens de la consulta: {tokens_total}")
    return answer


if __name__ == "__main__":
    question = input("¿Qué clima quieres consultar? ").strip()
    print(run_agent(question))
