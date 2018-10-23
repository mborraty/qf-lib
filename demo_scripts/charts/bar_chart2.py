import datetime
import random

from matplotlib import pyplot as plt

from qf_common.config.ioc import container
from qf_lib.common.enums.price_field import PriceField
from qf_lib.common.tickers.tickers import QuandlTicker
from qf_lib.common.utils.dateutils.string_to_date import str_to_date
from qf_lib.containers.series.qf_series import QFSeries
from qf_lib.data_providers.general_price_provider import GeneralPriceProvider
from qf_lib.plotting.helpers.create_bar_chart import create_bar_chart

MAX_RECESSION_LENGTH = 6
MAX_NON_RECESSION_LENGTH = 20


def rand_recession(series):
    length_limit = len(series)
    current_length = 0
    recession_data = []

    is_recession = False
    while current_length < length_limit:
        period_length_limit = MAX_RECESSION_LENGTH if is_recession else MAX_NON_RECESSION_LENGTH
        remaining_elements = length_limit - current_length
        period_length_limit = min(period_length_limit, remaining_elements)
        period_length = random.randint(1, period_length_limit)

        period = [int(is_recession)]*period_length
        recession_data += period

        current_length += period_length
        is_recession = not is_recession

    recession_tms = QFSeries(data=recession_data, index=series.index.copy())
    return recession_tms


plt.style.use(['seaborn-poster', 'macrostyle'])

data = container.resolve(GeneralPriceProvider)

start_date = str_to_date('2016-01-01')
end_date = str_to_date('2016-11-20')

spx_tms = data.get_price(QuandlTicker('AAPL', 'WIKI'), PriceField.Close, start_date, end_date)
spx_tms = spx_tms.pct_change()

recession = rand_recession(spx_tms)
names = ["Quarter on quarter annualised,  (SA, Chained 2009, %)",
         "Year on year  (SA, Chained 2009, %)", None]

chart = create_bar_chart([spx_tms], names,
                         "US Real Gross Domestic Product Growth (%)", [spx_tms], recession, quarterly=False,
                         start_x=datetime.datetime.strptime("2015", "%Y"))
chart.plot()


plt.show(block=True)