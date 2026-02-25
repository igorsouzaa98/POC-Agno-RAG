.PHONY: dev build docker-build docker-run railway-login railway-init railway-deploy railway-url frontend-setup frontend-dev frontend-deploy

# ── Desenvolvimento local ─────────────────────────────────────────
dev:
	uvicorn src.agent_os_server:app --reload --port 7777

reindex:
	python scripts/build_knowledge.py --recreate

# ── Docker local (para testar antes do deploy) ───────────────────
docker-build:
	docker build -t aco-cearense-api .

docker-run:
	docker run --rm -p 8080:8080 \
	  -e ANTHROPIC_API_KEY=$(ANTHROPIC_API_KEY) \
	  -e GOOGLE_API_KEY=$(GOOGLE_API_KEY) \
	  -e MODEL_ID=$(MODEL_ID) \
	  aco-cearense-api

# ── Railway (backend) ─────────────────────────────────────────────
# Pré-requisito: npm install -g @railway/cli
railway-login:
	railway login

railway-init:
	railway init

railway-deploy:
	railway up

railway-url:
	railway status

# ── Frontend (Agent UI → Vercel) ──────────────────────────────────
# Pré-requisito: npm install -g vercel
frontend-setup:
	@if [ -d "frontend" ]; then \
	  echo "frontend/ já existe — pulando criação"; \
	else \
	  npx create-agent-ui@latest frontend; \
	fi
	@echo ""
	@echo "➡️  Próximo passo: configure a URL da API no frontend"
	@echo "   Adicione em frontend/.env.local:"
	@echo "   NEXT_PUBLIC_AGNO_API_URL=\$$(railway status --json | python3 -m json.tool | grep url | head -1)"

frontend-dev:
	cd frontend && npm run dev

frontend-deploy:
	@if [ ! -d "frontend" ]; then echo "❌ Rode 'make frontend-setup' primeiro"; exit 1; fi
	cd frontend && vercel --prod
