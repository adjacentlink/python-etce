FROM ubuntu:18.04

# prevent failures due to interactive apt transactions
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get -y -f install

RUN apt-get -y install libtool make autoconf automake debhelper python3-setuptools \
                       python3-stdeb python3-dev git


WORKDIR /opt
RUN git clone https://github.com/adjacentlink/python-etce -b develop

WORKDIR python-etce
RUN ./autogen.sh
RUN ./configure
RUN make deb
RUN dpkg -i $(find .debbuild -name "*\.deb")
RUN apt-get -y -f install

RUN echo 'ubuntu18.04 complete'

