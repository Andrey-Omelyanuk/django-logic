PROJECT_NAME = django-logic
info:
	echo "Usage: make <target>"
	echo "Targets:"
	echo "  build - Build the Docker image"
	echo "  test  - Run the tests"
	echo "  sh    - Run a django shell"

build:
	docker build -t $(PROJECT_NAME) .
test:
	docker run -p 8000:8000 -v $(PWD):/app $(PROJECT_NAME) python tests/manage.py test
sh:
	docker run -p 8000:8000 -v $(PWD):/app $(PROJECT_NAME) python tests/manage.py shell
sss:
	docker run -p 8000:8000 -v $(PWD):/app $(PROJECT_NAME) \
	python tests/manage.py  test tests.test_transition.ActionCallbacksTestCase.test_failure_during_callbacks
