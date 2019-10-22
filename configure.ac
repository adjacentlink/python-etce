AC_COPYRIGHT([
 
  Copyright (c) 2013-2019 - Adjacent Link LLC, Bridgewater, New Jersey
  All rights reserved.
 
  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions
  are met:
 
  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
  * Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in
    the documentation and/or other materials provided with the
    distribution.
  * Neither the name of Adjacent Link LLC nor the names of its
    contributors may be used to endorse or promote products derived
    from this software without specific prior written permission.
 
  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
  ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
  POSSIBILITY OF SUCH DAMAGE.
 
])

AC_INIT([python-etce],1.2.1,[labs at adjacentlink dot com])

AM_INIT_AUTOMAKE([1.9.6])

LT_INIT

AC_CONFIG_MACRO_DIR([m4])

AC_ARG_WITH(python2,
           [  --with-python2          use python2 instead of python3 (off)])

AM_CONDITIONAL([HAVE_PYTHON2], [test x$with_python2 = xtrue])

AC_SUBST(RELEASE, 1)

# Python 2 or 3
if test "$with_python2" = yes; then
AM_PATH_PYTHON([2.7])
AC_SUBST(PYTHON_PACKAGE_PREFIX, python2)
else
AM_PATH_PYTHON([3])
AC_SUBST(PYTHON_PACKAGE_PREFIX, python3)
fi

# check for rpmbuild
AC_CHECK_PROG(HAVE_RPMBUILD, rpmbuild, true, false)
AM_CONDITIONAL(HAVE_RPMBUILD,$HAVE_RPMBUILD)

# check for deb
AC_CHECK_PROG(HAVE_DEB, dh_clean, true, false)
AM_CONDITIONAL(HAVE_DEB,$HAVE_DEB)

AC_OUTPUT(
 Makefile
 stdeb.cfg
 setup.py
)
