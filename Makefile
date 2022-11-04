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
	. $(VENV)/bin/activate; python3 -m unittest

# Destroy/uninstall the virtualenv and pycache
uninstall:
# rm -rf __pycache__ try the below command to go through the project and remove them
	find . -type d -name  "__pycache__" -exec rm -r {} +
	rm -rf $(VENV)

# Clean the workspace
clean:
	rm *.log
	rm *.eml
	rm nibbler.db