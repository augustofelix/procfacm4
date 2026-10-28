.PHONY: dev test

# Levanta la API y la UI juntas; Ctrl+C detiene las dos.
dev:
	trap 'kill 0' INT TERM EXIT; \
	uv run uvicorn procfac.api.app:app --host 127.0.0.1 --port 8000 & \
	uv run streamlit run src/procfac/ui/app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false & \
	wait

test:
	uv run pytest
