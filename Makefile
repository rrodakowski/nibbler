# Python make file
VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
# TODO: If I wanted absolute paths of output files 
# this looks like a way to do it
# DELIVERABLE=$(abspath $(OUT_FILE))

# Run the app
run: test
	. $(VENV)/bin/activate; $(PYTHON) -m nibbler to@mailinator.com from@mailinator.com  nibbler/tests/integration_tests/test_data

# Install all the libs locally and activate virtualenv
$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	. $(VENV)/bin/activate; $(PIP) install --upgrade pip; $(PIP) install -r requirements.txt 

# Run all the tests
test: $(VENV)/bin/activate
	. $(VENV)/bin/activate; $(PYTHON) -m unittest

# Run the linter
lint: test
	. $(VENV)/bin/activate; $(PIP) install pylint; pylint nibbler; 

# Build a wheel
wheel: test
	. $(VENV)/bin/activate; $(PIP) install build; $(PYTHON) -m build --wheel

# Deploy to test version of pypi
deploy: wheel
	. $(VENV)/bin/activate; $(PIP) install twine; twine upload dist/nibbler*.whl --verbose --repository testpypi

# Destroy/uninstall the virtualenv and pycache
uninstall:
# rm -rf __pycache__ try the below command to go through the project and remove them
	find . -type d -name  "__pycache__" -exec rm -r {} +
	rm -rf $(VENV)

# Clean the workspace
clean:
	rm -f *.log
	rm -f *.eml
	rm -f nibbler.db
	rm -rf dist
	rm -rf nibbler_rss.egg-info
	rm -rf build