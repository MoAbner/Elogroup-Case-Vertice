# Auditoria dos rankings no protótipo final

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
