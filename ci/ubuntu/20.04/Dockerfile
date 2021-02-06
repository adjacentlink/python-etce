FROM ubuntu:20.04

# prevent failures due to interactive apt transactions
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update

RUN apt-get -y --no-install-recommends install libtool make autoconf automake debhelper build-essential dh-python python3-setuptools python3-stdeb python3-dev git

WORKDIR /opt
RUN git clone https://github.com/eschreiber/python-etce -b develop

WORKDIR python-etce
RUN ./autogen.sh
RUN ./configure
RUN make deb

RUN echo 'ubuntu20.04 complete'

