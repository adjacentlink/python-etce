FROM fedora:33

#RUN dnf -y update

#RUN dnf clean all

RUN dnf -y install libtool make automake autoconf rpm-build python3-setuptools git python3-devel bash

WORKDIR /opt
RUN git clone https://github.com/eschreiber/python-etce -b develop

WORKDIR python-etce
RUN ./autogen.sh
RUN ./configure
RUN make rpm
RUN dnf -y install $(find .rpmbuild/RPMS -name "*\.rpm")

RUN echo 'fedora33 complete'

