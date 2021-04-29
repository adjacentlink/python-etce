#
# Copyright (c) 2021 - Adjacent Link LLC, Bridgewater, New Jersey
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

import matplotlib.pyplot as plt

"""
Bare bones scatterplot substitute for seaborn versions
prior to 0.11.
"""

try:
    from seaborn import scatterplot
except:
    def scatterplot(x=None,
                    y=None,
                    hue=None,
                    style=None,
                    size=None,
                    data=None,
                    palette=None,
                    hue_order=None,
                    hue_norm=None,
                    sizes=None,
                    size_order=None,
                    size_norm=None,
                    markers=True,
                    style_order=None,
                    x_bins=None,
                    y_bins=None,
                    units=None,
                    estimator=None,
                    ci=95,
                    n_boot=1000,
                    alpha='auto',
                    x_jitter=None,
                    y_jitter=None,
                    legend='brief',
                    ax=None,
                    **kwargs):
        if ax is None:
            ax = plt.gca()

        data.plot(x, y, kind='scatter', ax=ax, **kwargs)
