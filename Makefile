.PHONY: install app api ui e2e v2 run restore clean

install:
	pip install -r requirements.txt && playwright install chromium

app:        ## the system under test
	uvicorn app.main:app --port 8000 --reload

api:        ## layer 1 — the business rule, no browser, under a second
	pytest -m api

ui:         ## layer 2 — the same feature file, in a browser
	pytest -m ui --headed --slowmo 800

e2e:        ## layer 3 — act on screen, assert in the API
	pytest -m e2e --headed --slowmo 800

v2:         ## the UI team refactored; watch the suite heal
	UI_VARIANT=v2 pytest -m ui

run:        ## all three layers + the verdict
	./demo/run.sh

restore:    ## undo any demo breakage
	./demo/restore.sh

clean:
	rm -rf reports artifacts .pytest_cache changed.txt demo/.backup
