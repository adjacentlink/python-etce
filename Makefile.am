ACLOCAL_AMFLAGS = -I m4

EXTRA_DIST= \
 autogen.sh \
 etce \
 scripts \
 test \
 Copyright \
 README.md

all-local: setup.py
	$(PYTHON) setup.py build


clean-local: setup.py
	$(PYTHON) setup.py clean
	-rm -rf python*etce.egg-info
	-rm -rf build
	-rm -rf dist
	-rm -rf deb_dist
	-rm -f python*tar.gz
	-rm -f setup.py
	-rm -f MANIFEST
	-rm -f stdeb.cfg
	-rm -f installed.txt
	-rm -rf `find . -name "*\.pyc"`
	-rm -rf `find . -name "*~"`


install: setup.py
	$(PYTHON) setup.py install --record=installed.txt --prefix=@prefix@


uninstall:
	xargs --arg-file installed.txt rm


spec: setup.py
	$(PYTHON) setup.py bdist_rpm --spec-only


if HAVE_RPMBUILD
REQUIRES=@PYTHON_PACKAGE_PREFIX@-paramiko @PYTHON_PACKAGE_PREFIX@-lxml @PYTHON_PACKAGE_PREFIX@-mako lxc
rpm: setup.py
	$(PYTHON) setup.py bdist_rpm --python @PYTHON_PACKAGE_PREFIX@ --release $(RELEASE) --requires "$(REQUIRES)"
endif


if HAVE_DEB
deb:    setup.py stdeb.cfg
	export DEB_BUILD_OPTIONS=nocheck && $(PYTHON) setup.py --command-packages=stdeb.command bdist_deb
endif
