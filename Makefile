PACKAGE=etce

VERSION=0.1.1
RELEASE=1
PYTHONVERSION=$(shell python --version 2>&1 | awk '{print $$2}' | awk -F. '{print $$1"."$$2}')
REQUIRES=python-paramiko python-lxml python-mako lxc

edit = sed                                    \
       -e 's|@VERSION[@]|$(VERSION)|g'        \
       -e 's|@PYTHONVERSION[@]|$(PYTHONVERSION)|g' \
       -e 's|@RELEASE[@]|$(RELEASE)|g'

all-local:	setup.py
	python setup.py build

clean:	setup.py
	python setup.py clean
	-rm -rf build
	-rm -rf dist
	-rm -rf deb_dist
	-rm -f $(PACKAGE).$(VERSION).tar.gz
	-rm -f setup.py
	-rm -f MANIFEST
	-rm -f stdeb.cfg
	-rm -rf `find . -name "*\.pyc"`
	-rm -rf `find . -name "*~"`

install:	setup.py
	python setup.py install

dist:	setup.py
	python setup.py sdist

spec: setup.py
	python setup.py bdist_rpm --spec-only

rpm: setup.py
	python setup.py bdist_rpm --release $(RELEASE) --requires "$(REQUIRES)"

deb:    setup.py stdeb.cfg
	python setup.py --command-packages=stdeb.command bdist_deb

setup.py:	setup.py.in
	if test -f $@; then chmod u+w $@; fi
	$(edit) $< > $@
	chmod g-w,u-w $@

stdeb.cfg: stdeb.cfg.in
	if test -f $@; then chmod u+w $@; fi
	$(edit) $< > $@
	chmod g-w,u-w $@
