from datetime import datetime
from typing import Union, Sequence, Type

import pandas as pd

from qf_lib.backtesting.events.time_event.market_close_event import MarketCloseEvent
from qf_lib.backtesting.events.time_event.market_open_event import MarketOpenEvent
from qf_lib.backtesting.events.time_event.regular_time_event import RegularTimeEvent
from qf_lib.common.enums.price_field import PriceField
from qf_lib.common.tickers.tickers import Ticker
from qf_lib.common.utils.dateutils.relative_delta import RelativeDelta
from qf_lib.common.utils.dateutils.timer import Timer
from qf_lib.common.utils.miscellaneous.to_list_conversion import convert_to_list
from qf_lib.containers.dataframe.prices_dataframe import PricesDataFrame
from qf_lib.containers.dataframe.qf_dataframe import QFDataFrame
from qf_lib.containers.series.cast_series import cast_series
from qf_lib.containers.series.prices_series import PricesSeries
from qf_lib.containers.series.qf_series import QFSeries
from qf_lib.data_providers.price_data_provider import DataProvider


class DataHandler(DataProvider):
    """
    DataHandler is a wrapper which can be used with any AbstractPriceDataProvider in both live and backtest
    environment. It makes sure that data "from the future" is not passed into components in the backtest environment.

    DataHandler should be used by all the Backtester's components (even in the live trading setup).

    The goal of a DataHandler is to provide backtester's components with financial data. It also makes sure that
    no data from the future (relative to a "current" time of a backtester) is being accessed, that is: that there
    is no look-ahead bias.
    """
    def __init__(self, price_data_provider: DataProvider, timer: Timer):
        self.price_data_provider = price_data_provider
        self.timer = timer
        self.time_helper = _DataHandlerTimeHelper(timer)

        # attributes to handle optimisation
        self.is_optimised = False
        self._data_bundle = None
        self._tickers = None
        self._fields = None

    def use_data_bundle(self, tickers: Union[Ticker, Sequence[Ticker]], fields: Union[PriceField, Sequence[PriceField]],
                        start_date: datetime, end_date: datetime):
        """
        Optimises running of the backtest. All the data will be downloaded before the backtest.
        Note that requesting during the backtest any other ticker or price field than the ones in the params
        of this function will result in an Exception.
        """
        self._data_bundle = self.price_data_provider.get_price(tickers, fields, start_date, end_date)
        self._tickers = tickers
        self._fields = fields
        self.is_optimised = True

    def historical_price(self, tickers: Union[Ticker, Sequence[Ticker]],
                         fields: Union[PriceField, Sequence[PriceField]], nr_of_bars: int) \
            -> Union[PricesSeries, PricesDataFrame, pd.Panel]:
        """
        Returns the latest available data samples corresponding to the nr_of_bars.

        tickers:
            ticker or sequence of tickers of the securities
        fields:
            PriceField or sequence of PriceFields of the securities
        nr_of_bars:
            number of data samples (bars) to be returned.
            Note: while requesting more than one ticker, some tickers may have fewer than n_of_bars data points
        """

        nr_of_days_to_go_back = int(nr_of_bars * (365 / 252) + 10)

        latest_available_market_close = self.time_helper.datetime_of_latest_market_event(MarketCloseEvent)
        start_date = latest_available_market_close - RelativeDelta(days=nr_of_days_to_go_back)

        if self.is_optimised:
            container = self._get_from_data_bundle(tickers, fields, start_date, latest_available_market_close)
        else:
            container = self.price_data_provider.get_price(tickers, fields, start_date, latest_available_market_close)

        if container.shape[0] < nr_of_bars:
            if isinstance(tickers, Ticker):
                tickers_as_strings = tickers.as_string()
            else:
                tickers_as_strings = ", ".join(x.as_string() for x in tickers)
            raise ValueError("Not enough data points for \ntickers: {} \ndate: {}."
                             "\n{} Data points requested, \n[] Data points available."
                             .format(tickers_as_strings, latest_available_market_close, nr_of_bars, container.shape[0]))

        return container.tail(nr_of_bars)

    def get_price(self, tickers: Union[Ticker, Sequence[Ticker]], fields: Union[PriceField, Sequence[PriceField]],
                  start_date: datetime, end_date: datetime = None):
        """
        Runs DataProvider.get_price(...) but before makes sure that the query doesn't concern data from
        the future.

        It accesses the latest fully available bar as of "today",
        that is: if a bar wasn't closed for today yet,
        then all the PriceFields (e.g. OPEN) will concern data from yesterday.

        See: DataProvider.get_price(...)
        """
        end_date_without_look_ahead = self._get_end_date_without_look_ahead(end_date)
        if self.is_optimised:
            return self._get_from_data_bundle(tickers, fields, start_date, end_date_without_look_ahead)
        else:
            return self.price_data_provider.get_price(tickers, fields, start_date, end_date_without_look_ahead)

    def get_history(self, tickers: Union[Ticker, Sequence[Ticker]], fields: Union[str, Sequence[str]],
                    start_date: datetime, end_date: datetime = None, **kwargs) \
            -> Union[QFSeries, QFDataFrame, pd.Panel]:
        """
        Runs DataProvider.get_history(...) but before makes sure that the query doesn't concern data from
        the future.

        See: DataProvider.get_history(...)
        """
        end_date_without_look_ahead = self._get_end_date_without_look_ahead(end_date)
        if self.is_optimised:
            return self._get_from_data_bundle(tickers, fields, start_date, end_date_without_look_ahead)
        else:
            return self.price_data_provider.get_history(tickers, fields, start_date, end_date_without_look_ahead)

    def get_last_available_price(self, tickers: Union[Ticker, Sequence[Ticker]]) -> Union[float, pd.Series]:
        """
        Gets the latest available price for given assets (even if the full bar is not yet available for that day).

        If "now" is at or after the market OPEN already, then the OPEN price will be returned.
        If "now" is after the market CLOSE, the close price will be returned.
        Always the latest available data will be returned (thus None or a Series of pd.nans will never be returned).

        Returns
        -------
        last_prices
            Series where:
            - last_prices.name contains a date of current prices,
            - last_prices.index contains tickers
            - last_prices.data contains latest available prices for given tickers
        """
        return self._get_single_date_price(tickers, nans_allowed=False)

    def get_current_price(self, tickers: Union[Ticker, Sequence[Ticker]]) -> Union[float, pd.Series]:
        """
        Works just like get_last_available_price() but it can return NaNs if data is not available at the current
        moment (on a non-trading day or when current time is different than the time of MarketOpen or MarketClose).

        If "now" is at the market OPEN and the price is available (trading day) the OPEN price will be returned.
        If "now" is at the market CLOSE and the price is available (trading day) the CLOSE price will be returned.
        In other cases (e.g. someone tries to get current price on a non-trading day or current time is different
        than MarketOpen or MarketClose) None will be returned (or the Series of pd.nan if multiple
        tickers were supplied).

        Returns
        -------
        current_prices
            Series where:
            - current_prices.name contains a date of current prices,
            - current_prices.index contains tickers
            - current_prices.data contains latest available prices for given tickers
        """
        return self._get_single_date_price(tickers, nans_allowed=True)

    def _get_from_data_bundle(self, tickers: Union[Ticker, Sequence[Ticker]],
                              fields: Union[PriceField, Sequence[PriceField]], start_date: datetime, end_date: datetime
                              ) -> Union[PricesSeries, PricesDataFrame, pd.Panel]:

        if isinstance(self._tickers, Ticker):
            if not isinstance(tickers, Ticker):
                tickers = tickers[0]  # sometimes single ticker is passed in a list
            # we have single ticker in the bundle so the type is Series or DataFrame
            if tickers != self._tickers:
                raise ValueError("Ticker {} not available in the Data Bundle".format(tickers))

            if isinstance(self._fields, PriceField):
                return self._data_bundle.loc[start_date: end_date]
            else:
                return self._data_bundle.loc[start_date:end_date, fields]
        else:
            if isinstance(self._fields, PriceField):
                return self._data_bundle.loc[start_date:end_date, tickers]
            else:
                return self._data_bundle.loc[start_date:end_date, tickers, fields]

    def _get_end_date_without_look_ahead(self, end_date):
        latest_available_market_close = self.time_helper.datetime_of_latest_market_event(MarketCloseEvent)
        if end_date is not None:
            end_date_without_look_ahead = min(latest_available_market_close, end_date)
        else:
            end_date_without_look_ahead = latest_available_market_close
        return end_date_without_look_ahead

    def _get_single_date_price(self, tickers: Union[Ticker, Sequence[Ticker]], nans_allowed: bool)\
            -> Union[float, pd.Series]:
        tickers, was_single_ticker_provided = convert_to_list(tickers, Ticker)

        # if an empty tickers list was supplied then return an empty result
        if not tickers:
            return pd.Series()

        current_datetime = self.timer.now()

        # below the time component is zeroed-out because the most of data providers expect it to be so
        current_date = datetime(current_datetime.year, current_datetime.month, current_datetime.day)
        start_date = current_date - RelativeDelta(days=7)

        price_fields = [PriceField.Open, PriceField.Close]

        if self.is_optimised:
            prices_panel = self._get_from_data_bundle(tickers, price_fields, start_date, current_date)
            # TODO: clean this section
            # it might happen that we have single ticker in the backtest and the Data frame is
            # returned form optimised function.
            if isinstance(prices_panel, QFDataFrame):
                prices_panel = pd.Panel.from_dict(data={tickers[0]: prices_panel})
                prices_panel = prices_panel.transpose(1, 0, 2)
        else:
            prices_panel = self.price_data_provider.get_price(tickers, price_fields, start_date, current_date)

        prices_df = self._panel_to_dataframe(prices_panel)
        prices_df = prices_df.loc[:current_datetime]

        try:
            prices_series = prices_df.loc[current_datetime, :]  # axes: date, ticker
        except KeyError:
            prices_series = pd.Series(index=tickers)

        prices_series.name = "Current asset prices"

        if not nans_allowed:
            # fill NaNs with latest available prices
            last_available_close_prices = prices_df.apply(func=lambda series: series.asof(current_datetime))

            if not last_available_close_prices.empty:
                unavailable_prices_tickers = prices_series.isnull()
                prices_series.loc[unavailable_prices_tickers] = last_available_close_prices.loc[unavailable_prices_tickers]

            prices_series.name = "Last available asset prices"

        prices_series = cast_series(prices_series, pd.Series)
        if was_single_ticker_provided:
            return prices_series[0]
        else:
            return prices_series

    def _panel_to_dataframe(self, prices_panel: pd.Panel):
        """
        Converts a Panel into a DataFrame by removing the "Price Field" axis.

        In order to remove it open and close prices get different time component in their corresponding datetimes
        (open prices will get the time of `MarketOpenEvent` and close prices will get the time of `MarketCloseEvent`).
        """
        market_open_datetimes = [
            price_datetime + MarketOpenEvent.trigger_time() for price_datetime in prices_panel.items
        ]
        market_close_datetimes = [
            price_datetime + MarketCloseEvent.trigger_time() for price_datetime in prices_panel.items
        ]
        dates = market_open_datetimes + market_close_datetimes

        prices_df = PricesDataFrame(index=dates, columns=prices_panel.major_axis)
        prices_df.loc[market_open_datetimes, :] = prices_panel.loc[:, :, PriceField.Open].T.values
        prices_df.loc[market_close_datetimes, :] = prices_panel.loc[:, :, PriceField.Close].T.values

        prices_df.sort_index(inplace=True)

        return prices_df

    def supported_ticker_types(self):
        return self.price_data_provider.supported_ticker_types()


class _DataHandlerTimeHelper(object):
    """
    Helper class extracting from DataHandler all the logic connected with time,
    that is logic which makes sure that no data from the future is accessed in the backtest.
    """

    def __init__(self, timer: Timer):
        self.timer = timer

    def datetime_of_latest_market_event(self, event_class: Type[RegularTimeEvent]):
        time_of_event = event_class.trigger_time()

        now = self.timer.now()

        today_market_event = now + time_of_event
        yesterday_market_event = today_market_event - RelativeDelta(days=1)

        if now < today_market_event:  # event hasn't occurred today yet
            latest_available_market_event = yesterday_market_event
        else:  # event occurred today already
            latest_available_market_event = today_market_event

        return latest_available_market_event