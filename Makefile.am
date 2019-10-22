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
if HAVE_PYTHON2
REQUIRES=python2-paramiko python2-lxml python2-mako lxc
else
REQUIRES=python3-paramiko python3-lxml python3-mako lxc
endif

rpm: setup.py
	$(PYTHON) setup.py bdist_rpm --release $(RELEASE) --requires "$(REQUIRES)"
endif


if HAVE_DEB
deb:    setup.py stdeb.cfg
	export DEB_BUILD_OPTIONS=nocheck && $(PYTHON) setup.py --command-packages=stdeb.command bdist_deb
endif
