files = find ./ -type f -name "*.py"

install-dev:
	pip install nose autopep8 flake8 hacking pylint

pep8:
	$(files) | xargs pep8

autopep8:
	$(files) | xargs autopep8 -i

flake8:
	$(files) | xargs flake8

pyflakes:
	$(files) | xargs pyflakes

pylint:
	$(files) | xargs pylint
