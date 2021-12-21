
version=$(shell grep version setup.cfg  | cut -d '=' -f 2 | xargs )

.PHONY: clean
clean:
	find . -d -type d -name __pycache__ -exec rm -rf {} \;
	rm -rf build dist MANIFEST friends2feeds.egg-info .venv

.PHONY: tidy
tidy: venv
	$(VENV)/black *.py

.PHONY: lint
lint: venv
	PYTHONPATH=$(VENV) $(VENV)/pylint --output-format=colorized \
	  friends2feeds.py

build: clean venv
	$(VENV)/python -m build

.PHONY: upload
upload: build
	git tag friends2feeds-$(version)
	git push
	git push --tags origin
	$(VENV)/python -m twine upload dist/*


include Makefile.venv
