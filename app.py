max_iterations = 5

weather = [
    {"country": "Colombia", "city": "Bogotá", "weather": "22°C, nublado"},
    {"country": "Colombia", "city": "Medellín", "weather": "20°C, nublado"},
    {"country": "Colombia", "city": "Cali", "weather": "25°C, soleado"},
    {"country": "Colombia", "city": "Barranquilla", "weather": "23°C, nublado"},
    {"country": "Colombia", "city": "Cartagena", "weather": "24°C, nublado"},
    {"country": "Colombia", "city": "Santa Marta", "weather": "26°C, soleado"},
    {"country": "Colombia", "city": "Cúcuta", "weather": "21°C, nublado"},
    {"country": "Colombia", "city": "Bucaramanga", "weather": "22°C, nublado"},
    {"country": "Venezuela", "city": "Caracas", "weather": "-2°C, soleado"},
    {"country": "Venezuela", "city": "Maracaibo", "weather": "25°C, nublado"},
    {"country": "Venezuela", "city": "Valencia", "weather": "23°C, nublado"},
    {"country": "Venezuela", "city": "Maracay", "weather": "24°C, nublado"},
    {"country": "Venezuela", "city": "Barquisimeto", "weather": "26°C, soleado"},
    {"country": "Venezuela", "city": "Mérida", "weather": "21°C, nublado"},
]


def get_weather(city):
    
    for entry in weather:
        if (
            entry["city"].lower() == city.lower()
        ):
            return entry["weather"]
    return "Weather information not found."


def fake_llm(memory):
    # aqui configuramos el llm ["Bogotá"]
    if len(memory) > 1:
        return {"type": "final_answer", "content": memory[-1]}

    city = memory[0].strip()
    return {
        "type": "tool_call",
        "tool": "get_weather",
        "args": {"city": city},
    }


def run_agent(user_input):
    memory = [user_input]  # user input stored in memory

    for i in range(max_iterations):
        response = fake_llm(memory)

        if response["type"] == "final_answer":
            return response["content"]

        city = response["args"]["city"]
        result = get_weather(city)
        memory.append(result)
    return "Max iterations reached without final answer."

print(__name__)

if __name__ == "__main__":
    city = input("¿De qué ciudad quieres saber el clima? ").strip()
    print(run_agent(city))
