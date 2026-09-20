import json
import re
import unicodedata
from pathlib import Path
from .config import ROOT

DATA = ROOT / "app" / "data"

def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))

ACCESS = load("access.json")
ORDERS = load("orders.json")["orders"]
KNOWLEDGE = load("knowledge.json")["documents"]

def norm(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")

def customer(customer_id):
    return next((x for x in ACCESS["customers"] if x["id"] == customer_id), None)

def actor(actor_id):
    return next((x for x in ACCESS["actors"] if x["id"] == actor_id), None)

def can_access(user: dict, item: dict) -> bool:
    return bool(user and ("*" in user["teams"] or item["team"] in user["teams"]))

def find_order(text: str, customer_id: str):
    ids = re.findall(r"\bVERT-\d{4}\b", text.upper())
    if not ids:
        return None, "missing"
    order = next((x for x in ORDERS if x["id"] == ids[-1]), None)
    if not order:
        return None, "not_found"
    if order["customer_id"] != customer_id:
        return None, "forbidden"
    return order, "ok"

def sources(text: str) -> list[dict]:
    value = norm(text)
    matches = [d for d in KNOWLEDGE if any(norm(topic) in value for topic in d["topics"])]
    return matches[:3]

def classify(text: str) -> dict:
    value = norm(text)
    outside_terms = ["capital da", "copa do mundo", "futebol", "receita de", "programacao", "python", "previsao do tempo", "presidente", "matematica", "ignore as regras", "ignore o prompt"]
    if any(term in value for term in outside_terms):
        return {"category": "Fora do escopo", "route": "FORA_DE_ESCOPO", "team": "Atendimento", "score": 0, "priority": "P3"}
    rules = [
        ("Fraude ou cobrança", ["nao reconheco", "desconhecid", "fraude", "golpe", "cobranca duplicada", "duas vezes"], "HUMANO_ESPECIALIZADO", "Financeiro", 100),
        ("Defeito", ["defeito", "quebrad", "danific", "queimad", "risco", "superaqueceu"], "HUMANO", "Qualidade e pós-venda", 86),
        ("Troca de Tamanho", ["troca", "tamanho", "nao serviu"], "HUMANO", "Trocas e pós-venda", 78),
        ("Pagamento não aprovado", ["pagamento", "cartao recusado", "pix", "nao aprovado"], "HUMANO", "Financeiro", 72),
        ("Onde está meu pedido?", ["pedido", "entrega", "rastre", "chega", "atras"], "CHATBOT", "Atendimento", 22),
        ("Elogio", ["elogio", "parabens", "adorei", "excelente", "obrigad"], "CHATBOT", "Atendimento", 8),
        ("Dúvida Técnica", ["produto", "como usar", "funciona", "material", "manual"], "HUMANO", "Suporte de produto", 52),
    ]
    for category, terms, route, team, score in rules:
        if any(term in value for term in terms):
            priority = "P0" if score >= 95 else "P1" if score >= 70 else "P2" if score >= 40 else "P3"
            return {"category": category, "route": route, "team": team, "score": score, "priority": priority}
    scope_terms = ["vertice", "pedido", "produto", "loja", "compra", "atendimento", "cliente"]
    if not any(term in value for term in scope_terms):
        return {"category": "Fora do escopo", "route": "FORA_DE_ESCOPO", "team": "Atendimento", "score": 0, "priority": "P3"}
    return {"category": "Não identificado", "route": "HUMANO", "team": "Atendimento", "score": 45, "priority": "P2"}
