
install:
	python setup.py install

clean:
	find . -name "*.pyc" -print0 | xargs -0 rm -rf

.PHONY: install clean
