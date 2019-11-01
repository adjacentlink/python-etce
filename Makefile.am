ACLOCAL_AMFLAGS = -I m4

EXTRA_DIST= \
 autogen.sh \
 etce \
 etcewrappers \
 scripts \
 test \
 Copyright \
 README.md \
 debian \
 $(PACKAGE).spec.in \
 setup.py.in

all-local: setup.py
	$(PYTHON) setup.py build


clean-local: setup.py
	$(PYTHON) setup.py clean
	-rm -rf python*etce.egg-info
	-rm -rf build
	-rm -rf dist
	-rm -f python*tar.gz
	-rm -f setup.py
	-rm -f MANIFEST
	-rm -f stdeb.cfg
	-rm -f installed.txt
	-rm -rf `find . -name "*\.pyc"`
	-rm -rf `find . -name "*~"`
	-rm -rf .debbuild
	-rm -rf .rpmbuild
	-rm -rf $(PACKAGE).spec

install: setup.py
	$(PYTHON) setup.py install \
	    -O1 \
        --record .installedfiles \
	    --prefix=$(prefix) \
	    --exec-prefix=$(exec_prefix) \
	    $(if $(DESTDIR),--root=$(DESTDIR))

uninstall:
	if test -f .installedfiles; then xargs -a .installedfiles rm -f; fi

spec: setup.py
	$(PYTHON) setup.py bdist_rpm --spec-only


edit = sed \
        -e 's|@VERSION[@]|$(VERSION)|g' \
        -e 's|@DEBIAN_VERSION[@]|$(DEBIAN_VERSION)|g' \
        -e 's|@DATE_RFC2822[@]|$(DATE_RFC2822)|g'

if HAVE_RPMBUILD

RPMARCH=`arch`

if HAVE_PYTHON2
RPMBUILD_ARGS=--with python2
else
RPMBUILD_ARGS=
endif

rpm: $(PACKAGE).spec dist-gzip
	mkdir -p .rpmbuild/BUILD \
	.rpmbuild/SPECS \
	.rpmbuild/SOURCES \
	.rpmbuild/SRPMS \
	.rpmbuild/RPMS/noarch \
	.rpmbuild/tmp
	cp -f $(PACKAGE)-$(VERSION).tar.gz .rpmbuild/SOURCES
	rpmbuild --clean -ba $(top_srcdir)/$(PACKAGE).spec --target $(RPMARCH) \
    --define "_topdir $$PWD/.rpmbuild" \
    --define "_tmppath $$PWD/.rpmbuild/tmp" \
    $(RPMBUILD_ARGS)
	@echo "============================================================"
	@echo "RPMs located in .rpmbuild/RPMS and .rpmbuild/SRPMS"

endif

if HAVE_DEB

deb: dist-gzip
	rm -rf .debbuild
	mkdir -p .debbuild
	cp -f $(PACKAGE)-$(VERSION).tar.gz .debbuild
	cd .debbuild && tar xzf $(PACKAGE)-$(VERSION).tar.gz
	$(edit) .debbuild/$(PACKAGE)-$(VERSION)/debian/changelog.in > \
          .debbuild/$(PACKAGE)-$(VERSION)/debian/changelog
if HAVE_PYTHON2
	cp .debbuild/$(PACKAGE)-$(VERSION)/debian/control.with-python2 \
              .debbuild/$(PACKAGE)-$(VERSION)/debian/control
	cp .debbuild/$(PACKAGE)-$(VERSION)/debian/rules.with-python2 \
              .debbuild/$(PACKAGE)-$(VERSION)/debian/rules
endif
	cd .debbuild/$(PACKAGE)-$(VERSION) && dpkg-buildpackage -F -us -uc
	@echo "============================================================"
	@echo "debs located in .debbuild"
cleandeb:
	dh_clean
else

cleandeb:

endif

$(PACKAGE).spec: $(PACKAGE).spec.in
	if test -f $@; then chmod u+w $@; fi
	$(edit) $< > $@
	chmod g-w,u-w $@

setup.py: setup.py.in
	if test -f $@; then chmod u+w $@; fi
	$(edit) $< > $@
	chmod g-w,u-w $@
