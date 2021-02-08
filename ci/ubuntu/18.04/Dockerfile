FROM ubuntu:18.04

RUN apt-get -y update
#RUN apt-get -y upgrade
#RUN apg-get -f -y install

RUN apt-get -y install libtool make autoconf automake debhelper python3-setuptools python3-stdeb python3-dev git

WORKDIR /opt
RUN git clone https://github.com/eschreiber/python-etce -b develop

WORKDIR python-etce
RUN ./autogen.sh
RUN ./configure
RUN make deb
RUN dpkg -i $(find .debbuild -name "*\.deb")
RUN apt-get install -f

RUN echo 'ubuntu18.04 complete'

