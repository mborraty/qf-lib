#     Copyright 2016-present CERN – European Organization for Nuclear Research
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

import unittest
from unittest import TestCase

import pandas as pd

from qf_lib.containers.helpers import rolling_window_slices
from qf_lib_tests.helpers.testing_tools.containers_comparison import assert_lists_equal


class TestSeries(TestCase):
    def setUp(self):
        self.index = pd.date_range(start='2017-01-01', end='2017-12-31', freq='BMS')

    def test_rolling_window_slices(self):
        actual_slices = rolling_window_slices(self.index, size=pd.DateOffset(months=6), step=1)
        expected_slices = [
            slice(pd.Timestamp('2017-01-02'), pd.Timestamp('2017-07-02')),
            slice(pd.Timestamp('2017-02-01'), pd.Timestamp('2017-08-01')),
            slice(pd.Timestamp('2017-03-01'), pd.Timestamp('2017-09-01')),
            slice(pd.Timestamp('2017-04-03'), pd.Timestamp('2017-10-03')),
            slice(pd.Timestamp('2017-05-01'), pd.Timestamp('2017-11-01')),
            slice(pd.Timestamp('2017-06-01'), pd.Timestamp('2017-12-01'))
        ]
        assert_lists_equal(expected_slices, actual_slices)


if __name__ == '__main__':
    unittest.main()
