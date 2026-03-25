"""
Экспорт всех сессий из Supabase в JSONL формат для обучения.
Запускается GitHub Actions ежедневно.
"""

import requests
import json
import os
from datetime import datetime, timezone

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def fetch_all_sessions():
    """Загружает все сессии из Supabase (с пагинацией)."""
    all_sessions = []
    offset = 0
    limit = 1000  # Supabase максимум за один запрос

    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/sessions"
            f"?select=*&order=created_at.asc"
            f"&offset={offset}&limit={limit}"
        )
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        batch = response.json()

        if not batch:
            break

        all_sessions.extend(batch)
        offset += len(batch)

        if len(batch) < limit:
            break

    return all_sessions


def export_to_jsonl(sessions, output_path="data/training_data.jsonl"):
    """Записывает сессии в JSONL файл."""
    os.makedirs("data", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for session in sessions:
            # Формируем обучающую запись
            record = {
                "session_id":     session.get("id"),
                "created_at":     session.get("created_at"),
                "object_address": session.get("object_address"),
                "region":         session.get("region"),
                "files_uploaded": session.get("files_uploaded"),
                "ai_extracted":   session.get("ai_extracted"),
                "ai_verdict":     session.get("ai_verdict"),
                "corrections":    session.get("corrections"),   # <-- главное для обучения
                "chat_full":      session.get("chat_full"),
                "kp_initial":     session.get("kp_initial"),
                "kp_final":       session.get("kp_final"),
                "delta_kp_pct":   session.get("delta_kp_pct"),
                "rating":         session.get("rating"),
                "issues_flagged": session.get("issues_flagged"),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return output_path


def write_meta(sessions, output_path="data/export_meta.json"):
    """Пишет метаданные экспорта для мониторинга."""
    corrections_count = sum(
        len(s.get("corrections") or []) for s in sessions
    )
    ratings = [s.get("rating") for s in sessions if s.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    meta = {
        "exported_at":       datetime.now(timezone.utc).isoformat(),
        "total_sessions":    len(sessions),
        "total_corrections": corrections_count,
        "avg_rating":        avg_rating,
        "latest_session":    sessions[-1].get("created_at") if sessions else None,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return meta


if __name__ == "__main__":
    print("Загружаю сессии из Supabase...")
    sessions = fetch_all_sessions()
    print(f"Найдено: {len(sessions)} сессий")

    if sessions:
        path = export_to_jsonl(sessions)
        meta = write_meta(sessions)
        print(f"Экспортировано в {path}")
        print(f"Всего правок оценщика: {meta['total_corrections']}")
        print(f"Средняя оценка: {meta['avg_rating']}")
    else:
        print("Нет данных для экспорта.")
        # Создаём пустой файл чтобы репо не сломался
        os.makedirs("data", exist_ok=True)
        open("data/training_data.jsonl", "w").close()
