.PHONY: clean
clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -f .coverage

.PHONY: destroy
destroy:
	docker-compose down

.PHONY: lint
lint:
	poetry run ruff check .
	poetry run ruff format --check .
	poetry run mypy olive_events_bus/

.PHONY: lint-fix
lint-fix:
	poetry run ruff check --fix .
	poetry run ruff format .

.PHONY: format
format:
	poetry run ruff format .

.PHONY: format-check
format-check:
	poetry run ruff format --check .

.PHONY: type-check
type-check:
	poetry run mypy olive_rules_engine/

.PHONY: refreeze
refreeze:
	bash bin/refreeze.sh
