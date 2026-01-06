.PHONY: dashboard dashboard-frontend dashboard-backend dashboard-init

dashboard:
	@bash -c 'trap "kill 0" INT TERM; \
	echo "Starting API on http://localhost:8000"; \
	python3 -m backend.main & \
	echo "Starting dashboard on http://localhost:5173"; \
	cd frontend && npm run dev'

dashboard-frontend:
	@cd frontend && npm run dev

dashboard-backend:
	@python3 -m backend.main

dashboard-init:
	@python3 scripts/init_db.py
