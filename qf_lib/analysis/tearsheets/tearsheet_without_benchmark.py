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

from datetime import datetime

from qf_lib.analysis.tearsheets.abstract_tearsheet import AbstractTearsheet
from qf_lib.common.enums.frequency import Frequency
from qf_lib.common.enums.plotting_mode import PlottingMode
from qf_lib.common.utils.volatility.get_volatility import get_volatility
from qf_lib.containers.series.prices_series import PricesSeries
from qf_lib.containers.series.qf_series import QFSeries
from qf_lib.documents_utils.document_exporting.element.chart import ChartElement
from qf_lib.documents_utils.document_exporting.element.grid import GridElement
from qf_lib.documents_utils.document_exporting.element.new_page import NewPageElement
from qf_lib.documents_utils.document_exporting.element.paragraph import ParagraphElement
from qf_lib.plotting.charts.line_chart import LineChart
from qf_lib.plotting.decorators.axes_formatter_decorator import PercentageFormatter, AxesFormatterDecorator
from qf_lib.plotting.decorators.axes_position_decorator import AxesPositionDecorator
from qf_lib.plotting.decorators.data_element_decorator import DataElementDecorator
from qf_lib.plotting.decorators.legend_decorator import LegendDecorator
from qf_lib.plotting.decorators.line_decorators import HorizontalLineDecorator
from qf_lib.plotting.decorators.title_decorator import TitleDecorator
from qf_lib.plotting.helpers.create_qq_chart import create_qq_chart
from qf_lib.plotting.helpers.create_returns_distribution import create_returns_distribution
from qf_lib.settings import Settings


class TearsheetWithoutBenchmark(AbstractTearsheet):

    def __init__(self, settings: Settings, pdf_exporter, strategy_series: QFSeries, live_date: datetime = None,
                 title: str = "Strategy Analysis"):
        super().__init__(settings, pdf_exporter, strategy_series, live_date, title)

    def build_document(self):
        series_list = [self.strategy_series]

        self._add_header()
        self.document.add_element(ParagraphElement("\n"))

        self._add_perf_chart(series_list)
        self.document.add_element(ParagraphElement("\n"))

        self._add_returns_statistics_charts()
        self._add_ret_distribution_and_qq()

        self.document.add_element(ParagraphElement("\n"))

        self._add_rolling_chart()

        # Next Page
        self.document.add_element(NewPageElement())
        self.document.add_element(ParagraphElement("\n"))

        self._add_cone_and_quantiles()
        self._add_underwater_and_skewness()

        self._add_statistics_table(series_list)

    def _add_ret_distribution_and_qq(self):
        grid = GridElement(mode=PlottingMode.PDF, figsize=self.half_image_size, dpi=self.dpi)

        # Distribution of Monthly Returns
        chart = create_returns_distribution(self.strategy_series)
        grid.add_chart(chart)

        # QQ chart
        chart = create_qq_chart(self.strategy_series)
        grid.add_chart(chart)

        self.document.add_element(grid)

    def _add_rolling_chart(self):
        days_rolling = int(252 / 2)  # 6M rolling
        step = round(days_rolling / 5)

        strategy = self.strategy_series.to_prices(1)
        chart = LineChart(start_x=strategy.index[0], end_x=strategy.index[-1])
        line_decorator = HorizontalLineDecorator(0, key="h_line", linewidth=1)
        chart.add_decorator(line_decorator)

        legend = LegendDecorator()

        def tot_return(window):
            return PricesSeries(window).total_cumulative_return()

        def volatility(window):
            return get_volatility(PricesSeries(window), Frequency.DAILY)

        functions = [tot_return, volatility]
        names = ['Rolling Return', 'Rolling Volatility']
        for func, name in zip(functions, names):
            rolling = strategy.rolling_window(days_rolling, func, step=step)
            rolling_element = DataElementDecorator(rolling)
            chart.add_decorator(rolling_element)
            legend.add_entry(rolling_element, name)

        chart.add_decorator(legend)

        chart.add_decorator(AxesFormatterDecorator(y_major=PercentageFormatter(".0f")))

        left, bottom, width, height = self.full_image_axis_position
        position_decorator = AxesPositionDecorator(left, bottom, width, height)
        chart.add_decorator(position_decorator)

        title_decorator = TitleDecorator("Rolling Statistics [6 Months]".format(days_rolling), key="title")
        chart.add_decorator(title_decorator)

        self.document.add_element(ChartElement(chart, figsize=self.full_image_size, dpi=self.dpi))
