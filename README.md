# Vértice Care — protótipo integrado

Aplicação local com duas visões no mesmo histórico:

- **Cliente:** conversa com o chatbot por canal, consulta pedido fictício, recebe resposta ou transferência.
- **Central omnichannel:** fila única, prioridade, equipe, conversa completa e resposta humana.
- **Acessos mockados:** gestor, atendimento geral, financeiro e pós-venda definidos em `app/data/access.json`. O servidor filtra leitura e resposta pela equipe.
- **IA configurável:** usa a API de chat da EloGroup quando chave e modelo estão configurados; sem eles, mantém a demonstração com fallback local seguro.

## Executar

No PowerShell:

```powershell
cd 'C:\Users\abner\Desktop\BOOTCAMP\Protótipo final'
Copy-Item .env.example .env.local
notepad .env.local
python -m app.server
```

Abra `http://127.0.0.1:8080`. Também é possível executar `run.ps1`.

No `.env.local`, informe:

```dotenv
ELOGROUP_API_KEY=sua-chave
ELOGROUP_API_MODEL=id-exato-retornado-por-api-models
```

A URL padrão é `https://chat.eloagents.click/api/v1/sandbox`. A aplicação chama `POST /api/chat/completions`. A chave fica somente no servidor e nunca é enviada ao navegador. Não versionar `.env.local`.

## Demonstração

1. Em **Visão do cliente**, selecione Ana e envie `Quero saber onde está o pedido VERT-1001.`
2. Teste `Existe uma cobrança no meu cartão que não reconheço.`: o chamado vira P0 e segue ao Financeiro.
3. Teste `Quem ganhou a Copa do Mundo?`: o assistente recusa por estar fora do escopo.
4. Em **Central omnichannel**, altere o perfil. O atendente geral não enxerga Financeiro; o especialista financeiro enxerga e responde o P0.
5. Responda na central e retorne à visão do cliente: o mesmo histórico é exibido.

Os pedidos, perfis, canais e conversas iniciais são fictícios. Use `POST /api/reset` com `{"actor_id":"gestor-01"}` para restaurar os exemplos, ou apague `app/data/prototipo.db` com o servidor desligado.

## Guardrails

- Todo chamado é analisado pela IA quando a API está configurada.
- O servidor aplica regras críticas depois da resposta do modelo: cobrança/fraude nunca é encerrada pelo bot.
- Pedido só é exibido quando pertence ao cliente fictício selecionado.
- Perguntas gerais são recusadas; a IA só recebe fontes aprovadas e pedido autorizado.
- Ausência de fonte gera transferência, não uma resposta inventada.
- System prompt e modelo de user prompt ficam em `app/prompts/`.

## Estrutura

- `app/server.py`: servidor HTTP e API.
- `app/service.py`: fluxo chatbot, handoff e autorização.
- `app/database.py`: SQLite com tickets, mensagens e eventos.
- `app/domain.py`: classificação, pedidos, conhecimento e perfis.
- `app/ai.py`: cliente da API e validação básica do JSON.
- `app/web/`: interface alinhada à referência visual.
- `app/data/`: mocks em JSON; o banco gerado não é versionado.
- `tests/`: testes de domínio, acesso e conversas.

## Análise de custos e ranking

- `documentacao/ANALISE_CUSTOS_CHATBOT_OMNICHANNEL.html`: estimativa mensal e anual, canais, tokens e implantação separada.
- `documentacao/ANALISE_CUSTOS_CHATBOT_OMNICHANNEL.pdf`: versão pronta para apresentação.
- `documentacao/premissas_custos.json` e `documentacao/custos_recorrentes.csv`: memória dos cálculos.
- `documentacao/AUDITORIA_RANKINGS.md`: verificação do 40/40/20 e da fila-2.0 no protótipo final.
- `documentacao/gerar_analise_custos.py`: regenera os documentos e cálculos quando volume, câmbio ou tarifas mudarem.
