ACLOCAL_AMFLAGS = -I m4

EXTRA_DIST= \
 autogen.sh \
 etce \
 scripts \
 test \
 Copyright \
 README.md

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
	-rm -f installed.txt
	-rm -rf `find . -name "*\.pyc"`
	-rm -rf `find . -name "*~"`


install: setup.py
	python setup.py install --record=installed.txt --prefix=@prefix@


uninstall:
	xargs --arg-file installed.txt rm


spec: setup.py
	python setup.py bdist_rpm --spec-only


if HAVE_RPMBUILD
REQUIRES=python-paramiko python-lxml python-mako lxc

rpm: setup.py
	python setup.py bdist_rpm --release $(RELEASE) --requires "$(REQUIRES)"
endif


if HAVE_DEB
deb:    setup.py stdeb.cfg
	export DEB_BUILD_OPTIONS=nocheck && python setup.py --command-packages=stdeb.command bdist_deb
endif
