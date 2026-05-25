# App Vida — Wellington
> Plano do projeto | Atualizado: 25/05/2026

---

## Objetivo principal
**Controlar ansiedade** — entender o que aumenta e o que diminui, e metrificar isso ao longo do tempo junto com humor e hábitos.

---

## Os 3 check-ins diários

### 🌅 Manhã — 7h30
*Intenção do dia. Menos de 40 segundos.*

| # | Pergunta | Tipo |
|---|---|---|
| 1 | Tomou Bupropiona? | ✅ Sim / ❌ Não |
| 2 | Ansiedade agora? | 1–3 / 4–5 / 6–7 / 8–10 |
| 3 | Como acordou? | 😴 Mal · 😐 Ok · ⚡ Ótimo |
| 4 | MIT do dia (1 prioridade) | Texto livre (pode pular) |
| 5 | Hoje é dia de treino? | Sim / Não (bot sugere baseado no histórico) |

### ☀️ Tarde — 13h
*Pulso rápido. 3 cliques.*

| # | Pergunta | Tipo |
|---|---|---|
| 1 | Ansiedade agora? | 1–3 / 4–5 / 6–7 / 8–10 |
| 2 | Como tá o trabalho? | 🔥 Fluindo · 😐 Normal · 🤯 Pesado |
| 3 | Almoçou / seguiu a dieta? | Sim / Parcialmente / Não |

### 🌙 Noite — 21h
*Fechamento do dia. ~1 minuto.*

| # | Pergunta | Tipo |
|---|---|---|
| 1 | Ansiedade agora? | 1–3 / 4–5 / 6–7 / 8–10 |
| 2 | Fumou cigarro? | Não / Sim (+ quantos) |
| 3 | Bebeu álcool? | Não / Sim |
| 4 | Treinou? | Não · Academia · Corrida · Ciclismo · Outro |
| 5 | Como foi a dieta hoje? | Bot mostra as 5 refeições, você marca quais fez |
| 6 | Completou a MIT? | ✅ Sim · 〰️ Parcial · ❌ Não |
| 7 | Emoções do dia | Chips (marca quantas quiser) |
| 8 | Pensamento do dia | Texto livre (pode pular) |
| 9 | Algum gasto? | Foto ou texto (pode pular) |

> Terças 13h: bot pula o check-in da tarde (você tem terapia)

---

## Metodologias usadas

### 🧠 Ansiedade — SUDS + Correlação automática
**SUDS** (Subjective Units of Distress Scale): escala 0–10 self-report, usada em TCC e psicologia clínica. Simples, validada, e a sua psicóloga já trabalha com esse conceito.

3 leituras por dia permitem ver o arco: acordou ansioso, melhorou no trabalho, piorou à noite? Ou o oposto?

Após 14 dias o sistema calcula automaticamente:
> "Nos dias que você treinou, sua ansiedade média foi **3.2**.  
> Nos dias sem treino, foi **6.8**."
> 
> "Após beber, sua ansiedade no dia seguinte sobe em média **+3.1 pontos**."

Isso transforma dado em decisão: você vê com números o que faz diferença.

### 🎯 Meta do dia — MIT (Most Important Task)
Uma única prioridade por dia. Pesquisa de produtividade mostra taxa de conclusão 89% maior do que listas de tarefas.

Manhã: "Qual a SUA 1 coisa de hoje?"  
Noite: "Conseguiu?" → rastreia taxa de sucesso ao longo do tempo.

Sem pressão — é pra ajudar a clareza, não virar mais uma cobrança.

### 🥗 Dieta — Checklist por refeição
5 refeições fixas por dia. Cada uma é um checkbox simples (fez / não fez).  
% de aderência diária. Pesquisa mostra que registrar refeições (mesmo imperfeitamente) melhora adesão em 40–50%.

### 💪 Treino — Weekly Habit Tracker
Visão semanal Seg–Dom. Meta: 4 treinos/semana.  
Mostra quantos fez, quanto falta, e streak de semanas consecutivas batendo a meta.

---

## Dieta — Plano base Wellington

> Objetivo: reduzir ~5% de gordura (19% → 14–15%)  
> Perfil: treino noturno 4x/semana (musculação), trabalho das 8h às 18h  
> Estimativa: ~1.900 kcal nos dias de treino · ~1.650 kcal nos dias de descanso

| # | Horário | Refeição | O que comer |
|---|---|---|---|
| 1 | 7h – 7h30 | ☀️ Café da manhã | 3 ovos mexidos + 2 fatias pão integral + 1 fruta (banana ou maçã) |
| 2 | 10h | 🍎 Lanche manhã | 1 pote iogurte grego (170g) + punhado castanhas/amêndoas |
| 3 | 12h – 12h30 | 🍽️ Almoço | 4 col arroz integral + feijão + 150g frango/carne + salada à vontade |
| 4 | 17h30 | ⚡ Pré-treino | 1 banana + 1 col pasta de amendoim (só nos dias de treino) |
| 5 | 21h+ | 🌙 Pós-treino / Jantar | 150g proteína (frango/atum/ovos) + legumes refogados ou salada |

**Regra simples:** proteína em todas as refeições, carboidrato reduz à tarde/noite.  
**Dias de descanso:** pula o pré-treino (#4), jantar mais leve.  
**Não precisa ser perfeito** — 3/5 refeições seguidas já é boa aderência.

> ⚠️ Este é um plano base estimado. Ideal ajustar com nutricionista futuramente — mas serve perfeitamente pra começar e criar o hábito de acompanhar.

---

## Dashboard — Seções

| Seção | O que mostra |
|---|---|
| Hoje | Hábitos (bup, cigarro, álcool, treino) + 3 leituras de ansiedade |
| Pensamento do dia | Texto livre do check-in da noite |
| MIT | Prioridade do dia + se completou |
| Dieta | 5 refeições com checklist de aderência |
| Streaks | Dias sem fumar · Dias sem beber |
| Semana de treino | Seg–Dom, meta 4x, % da semana |
| Ansiedade 14 dias | Gráfico com 3 leituras/dia |
| Correlações | Padrões automáticos (disponível após 14 dias) |
| Gastos | Lista recente + total do mês |

---

## Fases de desenvolvimento

### Fase 1 — Layout (agora)
- [x] Plano do projeto
- [x] Dashboard visual com mock data
- [ ] Ajustes finais de layout (aprovação)

### Fase 2 — Backend
- [ ] `db.py` — banco de dados
- [ ] `bot.py` — 3 check-ins + dieta + MIT
- [ ] `scheduler.py` — lembretes 7h30 / 13h / 21h
- [ ] `ocr.py` — OCR de comprovantes
- [ ] `main.py` — Flask + inicia serviços
- [ ] Deploy no Railway

### Fase 3 — Melhorias
- [ ] Correlação automática ansiedade × hábitos
- [ ] Resumo semanal automático (domingo 9h)
- [ ] Exportar relatório mensal PDF
- [ ] Integrar extrato Itaú

---

*"A última das liberdades humanas é a escolha da atitude perante qualquer situação." — Viktor Frankl*
