from . import database as db
from . import domain
from .ai import analyze, configured

ALLOWED_CATEGORIES = {"Onde está meu pedido?", "Elogio", "Troca de Tamanho", "Defeito", "Pagamento não aprovado", "Fraude ou cobrança", "Dúvida Técnica", "Não identificado", "Fora do escopo"}
ALLOWED_ROUTES = {"CHATBOT", "HUMANO", "HUMANO_ESPECIALIZADO", "FORA_DE_ESCOPO"}

def public_config():
    return {"ai_configured": configured(), "ai_model": "configurado" if configured() else "fallback local", "data_mode": "mock"}

def bootstrap():
    return {"access": domain.ACCESS, "config": public_config()}

def _bot_message(ticket_id, text):
    db.add_message(ticket_id, "bot", "bot", "Assistente Vértice", text)

def process_customer_message(ticket_id: str, text: str):
    ticket = db.conversation(ticket_id)
    client = domain.customer(ticket["customer_id"])
    ticket["customer_name"] = client["name"] if client else "Cliente"
    rule = domain.classify(text)
    order, order_state = domain.find_order(text, ticket["customer_id"])
    docs = domain.sources(text)
    model, model_error = analyze(ticket, text, order, docs)
    db.add_event(ticket_id, "llm_analyzed" if model else "local_fallback", model_error or "Mensagem analisada pela API configurada")

    category, route, team = rule["category"], rule["route"], rule["team"]
    response, status = "", "bot_active"
    if route == "FORA_DE_ESCOPO":
        response = "Posso ajudar somente com pedidos, entregas, produtos, trocas, defeitos e pagamentos da Vértice. Qual desses assuntos você precisa resolver?"
        status = "bot_active"
    elif category == "Fraude ou cobrança":
        response = "Vou encaminhar seu caso ao Financeiro especializado com prioridade. Não envie senha, CVV ou o número completo do cartão."
        status, route = "waiting_human", "HUMANO_ESPECIALIZADO"
    elif category in {"Defeito", "Troca de Tamanho", "Pagamento não aprovado"}:
        response = {
            "Defeito": "Registrei o relato e vou encaminhar para Qualidade e pós-venda avaliar com segurança.",
            "Troca de Tamanho": "Vou encaminhar seu pedido para Trocas e pós-venda continuar a solicitação.",
            "Pagamento não aprovado": "Vou encaminhar seu caso ao Financeiro para verificar o pagamento."
        }[category]
        status, route = "waiting_human", "HUMANO"
    elif category == "Onde está meu pedido?":
        if order_state == "missing":
            response = "Informe o número do pedido no formato VERT-1001 para eu consultar o registro autorizado."
        elif order_state == "forbidden":
            response = "Não consegui validar esse pedido para o perfil selecionado. Vou encaminhar o caso para o Atendimento confirmar com segurança."
            status, route, team = "waiting_human", "HUMANO", "Atendimento"
        elif order_state == "not_found":
            response = "Não localizei esse código nos registros disponíveis. Vou encaminhar ao Atendimento para conferência."
            status, route, team = "waiting_human", "HUMANO", "Atendimento"
        elif order["status"] == "Atrasado":
            response = f'O pedido {order["id"]} está marcado como atrasado. Vou encaminhar para Logística acompanhar a exceção.'
            status, route, team = "waiting_human", "HUMANO", "Logística"
        else:
            response = f'O pedido {order["id"]} está: {order["status"]}. {order["detail"]} Acompanhe em {order["tracking_url"]}'
            status = "awaiting_confirmation"
    elif category == "Elogio":
        response = "Muito obrigado pelo elogio! Registrei seu comentário para a equipe Vértice."
        status = "awaiting_confirmation"
    elif model:
        candidate_category = model.get("categoria")
        candidate_route = model.get("rota")
        if candidate_category in ALLOWED_CATEGORIES:
            category = candidate_category
        if candidate_route in ALLOWED_ROUTES:
            route = candidate_route
        if route in {"HUMANO", "HUMANO_ESPECIALIZADO"}:
            status = "waiting_human"
            team = model.get("equipe") if model.get("equipe") in {"Atendimento", "Logística", "Financeiro", "Qualidade e pós-venda", "Trocas e pós-venda", "Suporte de produto"} else team
        response = str(model.get("resposta_cliente") or "Vou encaminhar seu caso para a equipe confirmar as informações.")[:900]
    else:
        response = "Não encontrei informação aprovada suficiente para responder. Vou encaminhar seu caso para o Atendimento continuar."
        status, route, team = "waiting_human", "HUMANO", "Atendimento"

    score = rule["score"]
    priority = rule["priority"]
    if route == "HUMANO_ESPECIALIZADO":
        score, priority = 100, "P0"
    db.update_conversation(ticket_id, subject=category, category=category, team=team, priority=priority,
                           score=score, status=status, route=route)
    _bot_message(ticket_id, response)
    if status == "waiting_human":
        db.add_event(ticket_id, "handoff", f"Encaminhado para {team} · {priority}")
    return db.conversation(ticket_id)

def create(customer_id: str, channel: str, text: str):
    client = domain.customer(customer_id)
    if not client:
        raise ValueError("Cliente inválido")
    if channel not in {"Canal Vértice", "WhatsApp", "E-mail", "Reclame Aqui"}:
        raise ValueError("Canal inválido")
    ticket_id = db.create_conversation(customer_id, channel, text.strip(), client["name"])
    return process_customer_message(ticket_id, text)

def client_message(customer_id: str, ticket_id: str, text: str):
    ticket = db.conversation(ticket_id)
    if not ticket or ticket["customer_id"] != customer_id:
        raise PermissionError("Conversa indisponível")
    client = domain.customer(customer_id)
    db.add_message(ticket_id, "customer", customer_id, client["name"], text.strip())
    if ticket["status"] in {"waiting_human", "in_progress"} and ticket["route"] in {"HUMANO", "HUMANO_ESPECIALIZADO"}:
        db.add_event(ticket_id, "customer_followup", "Nova mensagem preservada na fila humana")
        return db.conversation(ticket_id)
    return process_customer_message(ticket_id, text)

def operator_message(actor_id: str, ticket_id: str, text: str):
    user, ticket = domain.actor(actor_id), db.conversation(ticket_id)
    if not ticket or not domain.can_access(user, ticket):
        raise PermissionError("Seu perfil não pode responder esta equipe")
    db.add_message(ticket_id, "agent", actor_id, user["name"], text.strip())
    db.update_conversation(ticket_id, status="in_progress", assigned_to=actor_id, route="HUMANO")
    db.add_event(ticket_id, "agent_reply", f"Resposta de {user['name']}")
    return db.conversation(ticket_id)

def change_status(actor_id: str, ticket_id: str, status: str):
    user, ticket = domain.actor(actor_id), db.conversation(ticket_id)
    if not ticket or not domain.can_access(user, ticket):
        raise PermissionError("Ação não autorizada")
    if status not in {"waiting_human", "in_progress", "resolved"}:
        raise ValueError("Status inválido")
    db.update_conversation(ticket_id, status=status, assigned_to=actor_id if status == "in_progress" else ticket["assigned_to"])
    db.add_event(ticket_id, "status_changed", f"{user['name']} alterou para {status}")
    return db.conversation(ticket_id)

def list_for_customer(customer_id):
    return [x for x in db.conversations() if x["customer_id"] == customer_id]

def list_for_actor(actor_id):
    user = domain.actor(actor_id)
    if not user:
        raise PermissionError("Perfil inválido")
    return [x for x in db.conversations() if domain.can_access(user, x)]

def get_for_customer(customer_id, ticket_id):
    item = db.conversation(ticket_id)
    if not item or item["customer_id"] != customer_id:
        raise PermissionError("Conversa indisponível")
    return item

def get_for_actor(actor_id, ticket_id):
    item, user = db.conversation(ticket_id), domain.actor(actor_id)
    if not item or not domain.can_access(user, item):
        raise PermissionError("Conversa indisponível para este perfil")
    return item
