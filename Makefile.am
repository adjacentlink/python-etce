all-local: setup.py
	python setup.py build


clean-local: setup.py
	python setup.py clean
	-rm -rf python_etce.egg-info
	-rm -rf build
	-rm -rf dist
	-rm -rf deb_dist
	-rm -f @PACKAGE@-@VERSION@.tar.gz
	-rm -f setup.py
	-rm -f MANIFEST
	-rm -f stdeb.cfg
	-rm -rf `find . -name "*\.pyc"`
	-rm -rf `find . -name "*~"`


install: setup.py
	python setup.py install --prefix=@prefix@


spec: setup.py
	python setup.py bdist_rpm --spec-only


sdist:
	python setup.py sdist


if HAVE_RPMBUILD
REQUIRES=python-paramiko python-lxml python-mako lxc

rpm: setup.py
	python setup.py bdist_rpm --release $(RELEASE) --requires "$(REQUIRES)"
endif


if HAVE_DEB
deb:    setup.py stdeb.cfg
	python setup.py --command-packages=stdeb.command bdist_deb
endif
