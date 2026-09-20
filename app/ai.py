from urllib import request, error
import json
import re

from .config import ROOT, settings

SYSTEM = (ROOT / "app" / "prompts" / "system_prompt.txt").read_text(encoding="utf-8")
TEMPLATE = json.loads((ROOT / "app" / "prompts" / "user_prompt_template.json").read_text(encoding="utf-8"))

def configured() -> bool:
    return bool(settings.api_key and settings.api_model)

def _user_payload(ticket: dict, message: str, order, docs: list[dict]) -> str:
    payload = json.loads(json.dumps(TEMPLATE, ensure_ascii=False))
    history = " | ".join(f'{m["author_type"]}: {m["text"]}' for m in ticket.get("messages", [])[-6:])
    values = {
        "{{ticket_id}}": ticket["id"], "{{channel}}": ticket["channel"],
        "{{customer_name}}": ticket.get("customer_name", "Cliente"), "{{message}}": message,
        "{{history}}": history, "{{order_context}}": json.dumps(order, ensure_ascii=False) if order else "Nenhum pedido autorizado localizado",
        "{{knowledge_context}}": json.dumps(docs, ensure_ascii=False)
    }
    raw = json.dumps(payload, ensure_ascii=False)
    for key, value in values.items():
        raw = raw.replace(key, str(value))
    return raw

def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Modelo não retornou JSON")
    return json.loads(text[start:end + 1])

def analyze(ticket: dict, message: str, order, docs: list[dict]):
    if not configured():
        return None, "fallback_sem_api"
    body = json.dumps({
        "model": settings.api_model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": _user_payload(ticket, message, order, docs)}
        ],
        "temperature": 0.2, "max_tokens": settings.api_max_tokens, "stream": False
    }).encode("utf-8")
    req = request.Request(settings.api_base_url + "/api/chat/completions", data=body, method="POST", headers={
        "Authorization": "Bearer " + settings.api_key,
        "Content-Type": "application/json", "Accept": "application/json"
    })
    try:
        with request.urlopen(req, timeout=settings.api_timeout) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
        return _extract_json(content), None
    except (error.URLError, error.HTTPError, TimeoutError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        return None, f"fallback_api:{type(exc).__name__}"

