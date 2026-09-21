"""Gera a análise reproduzível de custos do chatbot e omnichannel."""
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

# Base observada no case: 24.093 tickets entre jan/2023 e dez/2024.
TICKETS_TOTAL = 24_093
MESES_BASE = 24
TICKETS_MES = TICKETS_TOTAL / MESES_BASE

# Referências consultadas em 20/09/2026.
CAMBIO = 5.1575  # PTAX venda de 18/09/2026
IA_INPUT_USD_MM = 0.40
IA_OUTPUT_USD_MM = 1.60
REPETICAO = 0.10

MANUTENCAO_HORAS_MES = 3
MANUTENCAO_HORA_BRL = 150
MANUTENCAO_MES = MANUTENCAO_HORAS_MES * MANUTENCAO_HORA_BRL


def brl(value: float) -> str:
    value = f"{value:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return f"R$ {value}"


def number(value: float, decimals: int = 0) -> str:
    value = f"{value:,.{decimals}f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return value


def token_cost(calls: int, output_average: int = 250, volume: float = TICKETS_MES) -> dict:
    inputs = [1_000, 1_500, 2_000, 2_500, 3_000][:calls]
    input_tokens = volume * sum(inputs) * (1 + REPETICAO)
    output_tokens = volume * calls * output_average * (1 + REPETICAO)
    usd = (input_tokens * IA_INPUT_USD_MM + output_tokens * IA_OUTPUT_USD_MM) / 1_000_000
    return {
        "calls": calls,
        "output_average": output_average,
        "input_tokens_month": input_tokens,
        "output_tokens_month": output_tokens,
        "cost_usd_month": usd,
        "cost_brl_month": usd * CAMBIO,
        "cost_brl_year": usd * CAMBIO * 12,
    }


AI_4 = token_cost(4)
AI_5 = token_cost(5)
AI_5_CEILING = token_cost(5, 420)
AI_5_DOUBLE = token_cost(5, 250, TICKETS_MES * 2)

# Infraestrutura conjunta. PostgreSQL e Redis ficam na VM inicial; Spaces guarda anexos.
SERVER = 48 * CAMBIO
DAILY_BACKUP = 48 * 0.30 * CAMBIO
OBJECT_STORAGE = 5 * CAMBIO
DOMAIN = 5
EMAIL_BASE = 0  # Até 3.000 e-mails/mês no plano gratuito de referência.
AI = AI_5["cost_brl_month"]

TECH_WITHOUT_MAINTENANCE = SERVER + DAILY_BACKUP + OBJECT_STORAGE + DOMAIN + EMAIL_BASE + AI
COMBINED_MONTH = TECH_WITHOUT_MAINTENANCE + MANUTENCAO_MES
CHANNEL_RESERVE = 200
COMBINED_WITH_RESERVE_MONTH = COMBINED_MONTH + CHANNEL_RESERVE

# Comparações isoladas. Não devem ser somadas ao orçamento conjunto.
CHATBOT_SERVER = 24 * CAMBIO
CHATBOT_BACKUP = 24 * 0.30 * CAMBIO
CHATBOT_ONLY_MONTH = CHATBOT_SERVER + CHATBOT_BACKUP + DOMAIN + AI + MANUTENCAO_MES
OMNI_ONLY_MONTH = SERVER + DAILY_BACKUP + OBJECT_STORAGE + DOMAIN + EMAIL_BASE + MANUTENCAO_MES

IMPLEMENTATION_RATE = 200
IMPLEMENTATION = [
    ("Requisitos, dados, canais e critérios de aceite", 16),
    ("Backend, banco PostgreSQL, mensagens, anexos e histórico", 32),
    ("Perfis, permissões, LGPD e trilha de auditoria", 20),
    ("Ranking 40/40/20, fila-2.0, P0 e explicabilidade", 24),
    ("Canal Vértice, e-mail e WhatsApp", 36),
    ("Chatbot, prompts, RAG e consulta de pedidos", 32),
    ("Logs, tokens, alertas, backup e restauração", 20),
    ("Testes ponta a ponta, segurança e correções", 28),
    ("Treinamento e entrada assistida", 16),
]
IMPLEMENTATION_HOURS = sum(hours for _, hours in IMPLEMENTATION)
IMPLEMENTATION_BASE = IMPLEMENTATION_HOURS * IMPLEMENTATION_RATE
IMPLEMENTATION_CONTINGENCY = IMPLEMENTATION_BASE * 0.20
RA_HOURS_MIN = 24
RA_HOURS_MAX = 48


def table(headers: list[str], rows: list[list[object]], css: str = "") -> str:
    head = "".join(f"<th>{item}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{item}</td>" for item in row) + "</tr>" for row in rows)
    return f'<table class="{css}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


pages: list[str] = []


def page(number_: str, eyebrow: str, title: str, body: str) -> None:
    pages.append(
        f'<section class="page"><header><div><p class="eyebrow">{eyebrow}</p><h1>{title}</h1></div>'
        f'<div class="brand">ELO<span>GROUP</span></div></header>{body}'
        f'<footer><span>Vértice Retail · análise de planejamento · 20/09/2026</span><b>{number_}</b></footer></section>'
    )


page("01 / 05", "Visão executiva", "Quanto custa manter a solução completa?", f"""
<p class="lead">Orçamento para a central omnichannel própria e o chatbot que analisa <b>todos os tickets</b>, responde quando possui dados confiáveis e transfere os demais com contexto.</p>
<div class="hero-grid">
  <article class="hero"><span>Operação recorrente</span><strong>{brl(COMBINED_MONTH)}<small>/mês</small></strong><p>{brl(COMBINED_MONTH * 12)} por ano</p></article>
  <article class="hero pale"><span>Com reserva de canais</span><strong>{brl(COMBINED_WITH_RESERVE_MONTH)}<small>/mês</small></strong><p>{brl(COMBINED_WITH_RESERVE_MONTH * 12)} por ano</p></article>
</div>
{table(["Componente recorrente", "Mensal", "Anual"], [
    ["IA — 5 chamadas em 100% dos tickets", brl(AI), brl(AI * 12)],
    ["Servidor 8 GB / 4 vCPU", brl(SERVER), brl(SERVER * 12)],
    ["Backup diário", brl(DAILY_BACKUP), brl(DAILY_BACKUP * 12)],
    ["Anexos em object storage", brl(OBJECT_STORAGE), brl(OBJECT_STORAGE * 12)],
    ["Domínio", brl(DOMAIN), brl(DOMAIN * 12)],
    ["Manutenção — 3h × R$ 150", brl(MANUTENCAO_MES), brl(MANUTENCAO_MES * 12)],
    ["TOTAL BASE", brl(COMBINED_MONTH), brl(COMBINED_MONTH * 12)],
])}
<div class="callout"><b>O total não inclui valores ainda sem tarifa pública:</b> contrato da RA API, mensagens pagas do WhatsApp fora da janela de atendimento, impostos e eventual criação de uma API de pedidos. A reserva opcional de R$ 200/mês serve para planejamento e deve ser substituída pelas faturas reais.</div>
<p class="caption">O custo de implementação aparece somente na página 4 e não integra os totais recorrentes.</p>
""")

page("02 / 05", "Chatbot e tokens", "100% dos tickets passam pela primeira análise", f"""
<p class="lead">A primeira chamada identifica assunto, risco e rota. As seguintes coletam dados, consultam registros e respondem. Quando a solução não consegue concluir, gera o resumo e encaminha ao humano.</p>
{table(["Chamada", "Entrada estimada", "Saída média"], [
    ["1 · triagem e primeira resposta", "1.000 tokens", "250 tokens"],
    ["2 · coleta de informação", "1.500 tokens", "250 tokens"],
    ["3 · resposta após consulta", "2.000 tokens", "250 tokens"],
    ["4 · confirmação ou handoff", "2.500 tokens", "250 tokens"],
    ["5 · interação adicional", "3.000 tokens", "250 tokens"],
])}
<div class="formula">Custo = [(tokens de entrada × US$ 0,40) + (tokens de saída × US$ 1,60)] ÷ 1 milhão × R$ 5,1575</div>
{table(["Cenário", "Entrada/mês", "Saída/mês", "Mensal", "Anual"], [
    ["4 chamadas médias", number(AI_4["input_tokens_month"]), number(AI_4["output_tokens_month"]), brl(AI_4["cost_brl_month"]), brl(AI_4["cost_brl_year"])],
    ["5 chamadas médias · adotado", number(AI_5["input_tokens_month"]), number(AI_5["output_tokens_month"]), brl(AI_5["cost_brl_month"]), brl(AI_5["cost_brl_year"])],
    ["5 chamadas no teto de 420 tokens", number(AI_5_CEILING["input_tokens_month"]), number(AI_5_CEILING["output_tokens_month"]), brl(AI_5_CEILING["cost_brl_month"]), brl(AI_5_CEILING["cost_brl_year"])],
    ["5 chamadas e volume dobrado", number(AI_5_DOUBLE["input_tokens_month"]), number(AI_5_DOUBLE["output_tokens_month"]), brl(AI_5_DOUBLE["cost_brl_month"]), brl(AI_5_DOUBLE["cost_brl_year"])],
])}
<div class="two-cols"><div><h2>Premissas</h2><ul><li>1.003,875 tickets/mês.</li><li>100% passam pela IA.</li><li>10% de repetição/reenvio.</li><li>Sem desconto de cache.</li><li>250 tokens médios; o protótipo permite até 420.</li></ul></div><div><h2>Controles necessários</h2><ul><li>Registrar tokens reais por chamada.</li><li>Limitar chamadas e custo por ticket.</li><li>Resumir histórico crescente.</li><li>Não chamar a IA após handoff.</li><li>Usar regras para ações críticas.</li></ul></div></div>
<p class="caption">Fontes: <a href="https://developers.openai.com/api/docs/models/gpt-4.1-mini">OpenAI · GPT‑4.1 mini</a> e <a href="https://ptax.bcb.gov.br/ptax_internet/consultarUltimaCotacaoDolar.do">Banco Central · PTAX</a>. O provedor EloGroup/Astra não publicou preço na documentação entregue; substituir a tarifa quando houver contrato.</p>
""")

page("03 / 05", "Omnichannel próprio", "O que precisa estar contratado ou disponível", f"""
{table(["Bloco", "Requisito para funcionar", "Tratamento no orçamento"], [
    ["Aplicação e banco", "VM Linux, PostgreSQL, Redis/worker, HTTPS e gestão de segredos.", f"{brl(SERVER)}/mês"],
    ["Continuidade", "Backup diário com restauração testada, logs e alertas.", f"{brl(DAILY_BACKUP)}/mês"],
    ["Anexos", "Object storage para imagens e documentos.", f"{brl(OBJECT_STORAGE)}/mês"],
    ["Canal Vértice", "Widget/formulário integrado ao backend.", "Incluído na infraestrutura"],
    ["E-mail", "Caixa corporativa, threading e envio transacional.", "R$ 0 se reutilizar a conta; plano Pro opcional"],
    ["WhatsApp", "Conta Meta, número habilitado, webhook e templates aprovados.", "Atendimento iniciado pelo cliente: R$ 0 na janela; demais mensagens variáveis"],
    ["Reclame Aqui", "Contrato RA API, credenciais, leitura, resposta e conciliação.", "Sob consulta; fora do total"],
    ["Pedidos/rastreio", "API autorizada ou serviço interno com identidade do cliente.", "Pressupõe API existente"],
])}
<h2>Orçamentos que não devem ser somados</h2>
{table(["Forma de implantação", "Mensal", "Anual", "Uso"], [
    ["Chatbot isolado", brl(CHATBOT_ONLY_MONTH), brl(CHATBOT_ONLY_MONTH * 12), "Pressupõe central já existente"],
    ["Omnichannel isolado", brl(OMNI_ONLY_MONTH), brl(OMNI_ONLY_MONTH * 12), "Sem consumo de IA"],
    ["Solução conjunta recomendada", brl(COMBINED_MONTH), brl(COMBINED_MONTH * 12), "Compartilha servidor, domínio e manutenção"],
])}
<div class="callout"><b>WhatsApp:</b> mensagens de serviço dentro da janela de 24 horas aberta pelo cliente são gratuitas. Templates iniciados pela empresa e mensagens fora das condições gratuitas dependem da categoria e do mercado. <b>Reclame Aqui:</b> a API permite ler e responder no sistema próprio, mas a contratação é comercial e não possui preço público encontrado.</div>
<p class="caption">Fontes: <a href="https://www.digitalocean.com/pricing/droplets">DigitalOcean · servidor</a>, <a href="https://www.digitalocean.com/pricing/backups">backup</a>, <a href="https://www.digitalocean.com/pricing">storage</a>, <a href="https://whatsappbusiness.com/products/platform-pricing/">WhatsApp</a>, <a href="https://blog.reclameaqui.com.br/api-do-reclame-aqui/">RA API</a> e <a href="https://resend.com/pricing">Resend</a>. Alta disponibilidade, plantão 24×7, telefonia e migração histórica extensa exigem outro dimensionamento.</p>
""")

implementation_rows = [[name, hours, brl(hours * IMPLEMENTATION_RATE)] for name, hours in IMPLEMENTATION]
implementation_rows += [
    ["TOTAL BASE", IMPLEMENTATION_HOURS, brl(IMPLEMENTATION_BASE)],
    ["Contingência de planejamento · 20%", number(IMPLEMENTATION_HOURS * .20, 1), brl(IMPLEMENTATION_CONTINGENCY)],
    ["RESERVA TOTAL", number(IMPLEMENTATION_HOURS * 1.20, 1), brl(IMPLEMENTATION_BASE + IMPLEMENTATION_CONTINGENCY)],
]
page("04 / 05", "Investimento separado", "Implementação não entra no custo mensal", f"""
<p class="lead">Estimativa para transformar o protótipo local em um MVP operacional. A manutenção recorrente permanece em 3 horas/mês a R$ 150/h; a implantação usa a premissa de equipe técnica a R$ 200/h.</p>
{table(["Entrega", "Horas", "Custo"], implementation_rows, "compact")}
<div class="callout"><b>Integração Reclame Aqui:</b> após contratação e acesso técnico, reservar mais 24–48 horas, ou {brl(RA_HOURS_MIN * IMPLEMENTATION_RATE)}–{brl(RA_HOURS_MAX * IMPLEMENTATION_RATE)}, antes da contingência. O contrato RA API continua fora desse valor.</div>
<p>O orçamento pressupõe API de pedidos já existente, um ambiente de produção, integrações sem migração histórica massiva e entrada assistida em horário comercial.</p>
""")

page("05 / 05", "Auditoria do protótipo", "Os dois rankings ainda não estão ativos", """
<div class="audit bad"><b>Resultado da verificação</b><span>O protótipo final não calcula 40/40/20 nem fila‑2.0.</span></div>
{table(["Regra esperada", "Fórmula", "Situação encontrada"], [
    ["Ranking por assunto · 40/40/20", "40% retenção + 40% necessidade humana + 20% insatisfação", "Ausente; há scores fixos por categoria"],
    ["Fila individual · fila‑2.0", "30% prazo + 25% impacto + 25% retenção + 10% recontato + 10% espera", "Ausente; a fila ordena o score fixo"],
    ["Exceção crítica", "P0 prevalece sobre o score", "Presente para fraude/cobrança"],
])}
<h2>Evidência no código</h2>
<ul><li><code>app/domain.py</code> atribui valores fixos como 100, 86, 78, 72, 22 e 8.</li><li><code>app/service.py</code> grava diretamente <code>rule["score"]</code> e <code>rule["priority"]</code>.</li><li><code>app/database.py</code> ordena P0–P3 e depois o campo <code>score</code>, sem guardar componentes ou versão da fórmula.</li><li>O prompt diz que o servidor calcula o score, mas isso não implementa as duas fórmulas.</li></ul>
<h2>Correção necessária antes do piloto</h2>
<ol><li>Calcular 40/40/20 por assunto com métricas aprovadas e versionadas.</li><li>Calcular fila‑2.0 por ticket com prazo, impacto, retenção, recontato e espera.</li><li>Preservar P0 para sinais críticos.</li><li>Salvar os cinco componentes, score, regra e data para explicar a posição.</li><li>Usar a IA apenas para extrair sinais; o servidor valida e calcula.</li></ol>
<div class="callout"><b>Consequência:</b> os custos desta análise continuam válidos, mas a proposta de priorização ainda precisa ser implementada no protótipo final para que a demonstração corresponda à solução documentada.</div>
""")

CSS = """
:root{--purple:#4b1d8f;--violet:#6731bd;--ink:#272333;--muted:#6d6877;--line:#ddd9e5;--soft:#f5f2f9;--green:#007f6d;--orange:#e98924;--red:#a51f35}*{box-sizing:border-box}body{margin:0;background:#eeedf2;color:var(--ink);font:15px/1.45 "Segoe UI",Arial,sans-serif}.page{width:min(1050px,calc(100% - 32px));min-height:760px;margin:24px auto;background:#fff;padding:36px 42px;box-shadow:0 3px 16px #21143815;position:relative;border-top:5px solid var(--purple)}header{display:flex;justify-content:space-between;gap:24px;border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:22px}.eyebrow{color:var(--purple);font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;margin:0 0 8px}.brand{font-size:14px;font-weight:700;letter-spacing:.08em;color:#777}.brand span{color:var(--purple)}h1{font:700 34px/1.08 Georgia,serif;color:#32136b;margin:0;max-width:760px}h2{font-size:18px;color:#38146f;margin:20px 0 8px}.lead{font-size:18px;color:#4e4958;max-width:900px}.hero-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:20px 0}.hero{background:var(--purple);color:#fff;padding:20px 22px;border-radius:3px}.hero.pale{background:#ede7f6;color:#32136b}.hero span{font-size:12px;text-transform:uppercase;letter-spacing:.08em}.hero strong{display:block;font:700 32px/1.1 Georgia,serif;margin-top:8px}.hero small{font:14px "Segoe UI",sans-serif}.hero p{margin:5px 0 0}table{width:100%;border-collapse:collapse;margin:16px 0;font-size:13px}th{background:var(--purple);color:#fff;padding:9px 10px;text-align:left}td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}tr:nth-child(even) td{background:var(--soft)}table.compact td,table.compact th{padding:6px 8px;font-size:11.5px}.callout,.formula{background:#f3eef9;border-left:4px solid var(--violet);padding:13px 15px;margin:16px 0}.formula{background:#e8f5f2;border-color:var(--green);font-family:Consolas,monospace}.two-cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}.two-cols>div{background:var(--soft);padding:2px 16px 8px}ul,ol{padding-left:20px}.caption{font-size:11px;color:var(--muted)}code{background:#eeeaf4;padding:2px 4px}.audit{display:flex;flex-direction:column;gap:3px;padding:16px 18px;color:#fff;margin-bottom:18px}.audit.bad{background:var(--red)}.audit b{font-size:12px;text-transform:uppercase;letter-spacing:.08em}.audit span{font-size:20px;font-weight:700}footer{position:absolute;left:42px;right:42px;bottom:18px;border-top:1px solid var(--line);padding-top:8px;color:var(--muted);font-size:10px}footer b{float:right}@media(max-width:760px){.page{width:100%;margin:0;padding:24px 18px;min-height:0}.hero-grid,.two-cols{grid-template-columns:1fr}header{align-items:start}h1{font-size:28px}table{display:block;overflow:auto}footer{position:static;margin-top:22px}}@page{size:A4 landscape;margin:8mm}@media print{body{background:#fff;font-size:11px;line-height:1.3}.page{width:100%;height:194mm;min-height:194mm;margin:0;padding:10mm 11mm;box-shadow:none;break-after:page;overflow:hidden}.page:last-child{break-after:auto}header{padding-bottom:8px;margin-bottom:10px}h1{font-size:27px}.lead{font-size:14px;margin:8px 0}.hero-grid{margin:10px 0}.hero{padding:11px 14px}.hero strong{font-size:25px}table{font-size:10px;margin:8px 0}td,th{padding:5px 6px}table.compact td,table.compact th{font-size:9.5px;padding:4px 6px}h2{font-size:14px;margin:10px 0 4px}.callout,.formula{padding:8px 10px;margin:8px 0}.caption{font-size:9px}.two-cols{gap:10px}.two-cols ul{margin:4px 0}.audit{padding:10px 12px;margin-bottom:8px}.audit span{font-size:16px}footer{left:11mm;right:11mm;bottom:5mm}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
"""

html = (
    '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Custos — chatbot e omnichannel próprio</title><style>' + CSS + '</style></head><body>'
    + "".join(pages) + '</body></html>'
)
(ROOT / "ANALISE_CUSTOS_CHATBOT_OMNICHANNEL.html").write_text(html, encoding="utf-8")

premises = {
    "base": {"tickets_total": TICKETS_TOTAL, "months": MESES_BASE, "tickets_month": TICKETS_MES},
    "exchange_brl_usd": CAMBIO,
    "ai_price_usd_per_million": {"input": IA_INPUT_USD_MM, "output": IA_OUTPUT_USD_MM},
    "retry_rate": REPETICAO,
    "maintenance": {"hours_month": MANUTENCAO_HORAS_MES, "brl_hour": MANUTENCAO_HORA_BRL},
    "tokens": {"four_calls": AI_4, "five_calls": AI_5, "five_calls_420_output": AI_5_CEILING, "double_volume": AI_5_DOUBLE},
    "recurring": {
        "technology_without_maintenance_month": TECH_WITHOUT_MAINTENANCE,
        "combined_month": COMBINED_MONTH,
        "combined_year": COMBINED_MONTH * 12,
        "combined_with_channel_reserve_month": COMBINED_WITH_RESERVE_MONTH,
        "combined_with_channel_reserve_year": COMBINED_WITH_RESERVE_MONTH * 12,
    },
    "implementation": {
        "rate_brl_hour": IMPLEMENTATION_RATE,
        "hours": IMPLEMENTATION_HOURS,
        "base_brl": IMPLEMENTATION_BASE,
        "contingency_brl": IMPLEMENTATION_CONTINGENCY,
        "with_contingency_brl": IMPLEMENTATION_BASE + IMPLEMENTATION_CONTINGENCY,
        "items": [{"name": name, "hours": hours} for name, hours in IMPLEMENTATION],
    },
}
(ROOT / "premissas_custos.json").write_text(json.dumps(premises, ensure_ascii=False, indent=2), encoding="utf-8")

rows = [
    ("IA — cinco chamadas em todos os tickets", AI, AI * 12, "Tarifa de referência"),
    ("Servidor 8 GB / 4 vCPU", SERVER, SERVER * 12, "DigitalOcean"),
    ("Backup diário", DAILY_BACKUP, DAILY_BACKUP * 12, "30% do servidor"),
    ("Object storage", OBJECT_STORAGE, OBJECT_STORAGE * 12, "US$ 5/mês"),
    ("Domínio", DOMAIN, DOMAIN * 12, "Reserva de R$ 60/ano"),
    ("Manutenção — 3h × R$ 150", MANUTENCAO_MES, MANUTENCAO_MES * 12, "Não inclui evolução"),
]
with (ROOT / "custos_recorrentes.csv").open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.writer(file, delimiter=";")
    writer.writerow(["item", "mensal_brl", "anual_brl", "observacao"])
    writer.writerows(rows)

audit = """# Auditoria dos rankings no protótipo final

## Resultado

O protótipo final ainda não utiliza as duas fórmulas de ranking propostas.

1. **40/40/20 por assunto:** deveria combinar 40% de atenção à retenção, 40% de necessidade humana e 20% de insatisfação.
2. **fila-2.0 por ticket:** deveria combinar 30% de prazo, 25% de impacto, 25% de retenção, 10% de recontato e 10% de espera, com P0 prevalecendo.

## Evidências

- `app/domain.py` usa scores fixos por categoria: fraude 100, defeito 86, troca 78, pagamento 72, status 22 e elogio 8.
- `app/service.py` grava diretamente `rule["score"]` e `rule["priority"]`.
- `app/database.py` ordena P0–P3 e depois o campo `score`, sem armazenar os componentes ou a versão da fórmula.
- O system prompt afirma que o servidor calcula o score, mas a afirmação no prompt não implementa as fórmulas.

## Ajuste recomendado

- Calcular e versionar o 40/40/20 por assunto.
- Extrair os sinais do ticket e calcular fila-2.0 no servidor.
- Preservar a exceção P0 para fraude, cobrança e risco de segurança.
- Persistir cada componente, o score final, a versão da regra e a explicação.
- Usar a LLM para extrair sinais quando necessário; validar faixas e calcular matematicamente no servidor.
"""
(ROOT / "AUDITORIA_RANKINGS.md").write_text(audit, encoding="utf-8")

print(json.dumps({
    "monthly": round(COMBINED_MONTH, 2),
    "annual": round(COMBINED_MONTH * 12, 2),
    "with_channel_reserve_monthly": round(COMBINED_WITH_RESERVE_MONTH, 2),
    "implementation": IMPLEMENTATION_BASE,
    "implementation_with_contingency": IMPLEMENTATION_BASE + IMPLEMENTATION_CONTINGENCY,
}, ensure_ascii=False, indent=2))
