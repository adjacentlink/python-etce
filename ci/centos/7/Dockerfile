FROM centos:7

RUN yum -y update
RUN yum clean all

RUN yum -y install epel-release
RUN yum -y install libtool make automake autotools rpm-build python-setuptools git python-devel



WORKDIR /opt
RUN git clone https://github.com/adjacentlink/python-etce -b develop

WORKDIR python-etce
RUN ./autogen.sh
RUN ./configure --with-python2
RUN make rpm
RUN yum -y install $(find .rpmbuild/RPMS -name "*\.rpm")

RUN echo 'centos7 complete'

