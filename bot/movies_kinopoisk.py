import requests

def get_random_movie(genre=None):
    api_key = "от-кинопоиска"  # замените, если есть
    url = "https://kinopoiskapiunofficial.tech/api/v2.2/films/random"
    headers = {"X-API-KEY": api_key}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            name = data.get("nameRu") or data.get("nameOriginal")
            year = data.get("year")
            rating = data.get("rating") or "—"
            genres = ", ".join(g["genre"] for g in data.get("genres", [])[:3])
            return f"🎬 <b>{name}</b> ({year})\nРейтинг: {rating}\nЖанры: {genres}"
    except:
        pass
    return "🎬 Не удалось найти фильм. Попробуйте позже."
