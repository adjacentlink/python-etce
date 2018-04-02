#
# Copyright (c) 2014-2018 - Adjacent Link LLC, Bridgewater, New Jersey
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
# * Neither the name of Adjacent Link LLC nor the names of its
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#


from etce.argregistrar import ArgRegistrar


class WrapperContext(ArgRegistrar):
    """
    WrapperContext aims to help eliminate repetitive, boilerplate
    Wrapper code and standardize Wrapper workflow. Specifically, 
    WrapperContext:

    * Standardizes the way Wrapper arguments are specified, searched
      and presented to Wrappers.

    * Standardizes the way input and output files are searched and
      presented to Wrappers.

    * Provides helper methods for running/daemonizing and stopping wrapped 
      applications.

    * Provides a uniform way for Wrappers to store meta information.

    * Provides access to an ETCE Platform object that provides helper
      methods for performing low level operations.

    A WrapperContext object is passed to most Wrapper methods as their
    "ctx" argument.
    """

    def __init__(self, impl):
        self._impl = impl


    def register_argument(self, argname, defaultval, description):
        """
        Register an input argument used by the wrapper. Wrapper
        arguments are generally a subset of the wrapped application's
        command line arguments, especially arguments that are useful
        to change on a trial by trial basis. Log levels are a typical
        example.

        Argument values are passed to the wrapper as ctx.args.ARGNAME,
        with defaultval used if the argument is not set
        externally. Users set wrapper argument values in the Test
        Directory steps.xml file or in an optional configuration file
        passed into the etce-test run command.

        Besides user registered arguments, ETCE reserves a small
        set of arguments, also passed in through ctx.args, that
        cannot be overwritten by the user - 

           default_pidfilename: 
              Absolute (default) pidfile name. Many Wrappers write
              they PID of the wrapped application they launch to a
              file with this name. Pidfiles are placed in the `lock`
              subdirectory of the etce.conf WORK_DIRECTORY.

           logdirectory: 
              the absolute path to the output directory.  The
              logdirectory is a scoped path name that includes the
              name of the current test, a date time stamp and the name
              of the host where the Wrapper is running. Wrappers must
              use this path for any output files they produce that are
              to be collected with the test results.

           nodename: 
              the hostname where the current wrapper is executing

           nodeid: 
              if nodename contains an integer value, it is passed
              as an int in this member, otherwise None

           starttime: 
              the current test's T=0 scenario time in format 
              YYYY-MM-DDTHH:MM:SS

           stepname: 
              the current step name as defined in the steps.xml file

           testname: 
              the current test name as defined in the test.xml file

           wrappername: 
              this wrapper's name
        """
        self._impl.register_argument(argname, defaultval, description)


    def register_infile_name(self, name):
        """
        Register the input file name used by the wrapper. 

        When a Wrapper registers in input file name, the context
        searches for a matching file name in the hosts's configuration
        directory and, if found, passes the absolute name to the
        wrapper in the ctx.args.infile member. ctx.args.infile is set
        to None if no matching file is found.

        Most wrappers use the presence of their input file as a
        trigger to run their wrapped application.
        """
        self._impl.register_infile_name(name)


    def register_outfile_name(self, name):
        """
        Register the output file name used by the Wrapper. 

        Wrapper conventionally register a log file as thier output
        file. This method is a convenience method that passes back the
        absolute name of the output file the wrapper should use in the
        ctx.arg.outfile member.
        """
        self._impl.register_outfile_name(name)


    def store(self, namevaldict):
        """
        Store the name/value pairs passed in via the dictionary
        argument to the JSON format `etce.store` file for the
        current host. Values are automatically subdivided in the storage
        file by wrapper name to avoid collision.
        """
        self._impl.store(namevaldict)


    @property
    def platform(self):
        """
        An etce.platform.Platform object.
        """
        return self._impl.platform


    @property
    def args(self):
        """
        The *args* member contains the values of the Wrapper's
        registered arguments as args.ARGNAME, the registered
        input and output filenames as args.infile and args.outfile,
        and the reserved arguments listed above (args.logdirectory,
        for example).
        """
        return self._impl.args


    def daemonize(self,
                  commandstr,
                  stdout=None,
                  stderr=None,
                  pidfilename=None,
                  genpidfile=True,
                  pidincrement=0,
                  starttime=None):
        """
        Run a command as a daemon process.

        commandstr:
           The full command string to run.

        stdout:
           An optional file name to capture standard output.

        stderr:
           An optional file name to capture standard error.

        pidfilename:
           An alternative file name to use to write the daemonized
           processes' PID. default_pidfilename is used if not specified.
           Only used when genpidfile is True.

        genpidfile:
           Do generate a PID file (True: default) or not (False).
       
        pidincrement:
           Some commands fork and exec further subprocesses in a
           manner where the original parent process is not the long
           running process whose PID is useful to capture.  Sometimes
           the relationship between the long-running exec'd PID and
           the parent PID is a fixed increment. Specifying a value for
           pidincrement causes the context to store the parent PID +
           pidincrement in the PID file. Note, this mechanism has
           limited use though where tests are run over a long enough
           period to cause the range of exec'd PID numbers to wrap. In
           this case the difference between the parent PID and
           long-running exec'd PID will not reliably be fixed as the
           kernel skips PIDs when they are in use.

        starttime:
           An optional YYYY-MM-DDTHH:MM::SS string. After forking,
           daemonize will sleep until the provides time before
           exec'ing the command. The command is exec'd immediately
           if not specified.
        """
        self._impl.daemonize(commandstr,
                             stdout,
                             stderr,
                             pidfilename,
                             genpidfile,
                             pidincrement,
                             starttime)


    def run(self,
            commandstr,
            stdout=None,
            stderr=None,
            pidfilename=None,
            genpidfile=True,
            pidincrement=0):
        """
        Run a command.

        commandstr:
           The full command string to run.

        stdout:
           An optional file name to capture standard output.

        stderr:
           An optional file name to capture standard error.

        pidfilename:
           An alternative file name to use to write the commands
           PID. default_pidfilename is used if not specified.  Only
           used when genpidfile is True.

        genpidfile:
           Do generate a PID file (True: default) or not (False).
       
        pidincrement:
           Some commands fork and exec further subprocesses in a
           manner where the original parent process is not the long
           running process whose PID is useful to capture.  Sometimes
           the relationship between the long-running exec'd PID and
           the parent PID is a fixed increment. Specifying a value for
           pidincrement causes the context to store the parent PID +
           pidincrement in the PID file. Note, this mechanism has
           limited use though where tests are run over a long enough
           period to cause the range of exec'd PID numbers to wrap. In
           this case the difference between the parent PID and
           long-running exec'd PID will not reliably be fixed as the
           kernel skips PIDs when they are in use.

        starttime:
           An optional YYYY-MM-DDTHH:MM::SS string. The run call
           blocks and sleeps until the specified time before running
           the command.
        """
        self._impl.run(commandstr,
                       stdout,
                       stderr,
                       pidfilename,
                       genpidfile,
                       pidincrement)


    def stop(self, pidfilename=None):
        """
        Stop the process associated with the PID in the specified file.

        This function sends SIGQUIT to the process associated with the
        PID contained in pidfilename and then removes the file. If
        pidfilename is not specified, default_pidfilename is used.
        """
        self._impl.stop(pidfilename)
