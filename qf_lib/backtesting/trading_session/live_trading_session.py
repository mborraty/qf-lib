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

from dic.container import Container

from qf_lib.backtesting.contract.contract_to_ticker_conversion.vol_strategy_mapper import \
    VolStrategyContractTickerMapper
from qf_lib.backtesting.data_handler.data_handler import DataHandler
from qf_lib.backtesting.events.notifiers import Notifiers
from qf_lib.backtesting.events.time_flow_controller import LiveSessionTimeFlowController
from qf_lib.backtesting.monitoring.live_trading_monitor import LiveTradingMonitor
from qf_lib.backtesting.monitoring.settings_for_live_trading import LiveTradingSettings
from qf_lib.backtesting.order.order_factory import OrderFactory
from qf_lib.backtesting.position_sizer.initial_risk_position_sizer import InitialRiskPositionSizer
from qf_lib.backtesting.trading_session.trading_session import TradingSession
from qf_lib.common.utils.dateutils.timer import RealTimer
from qf_lib.common.utils.logging.qf_parent_logger import qf_logger
from qf_lib.data_providers.bloomberg import BloombergDataProvider
from qf_lib.documents_utils.document_exporting.pdf_exporter import PDFExporter
from qf_lib.documents_utils.email_publishing.email_publisher import EmailPublisher
from qf_lib.documents_utils.excel.excel_exporter import ExcelExporter
from qf_lib.interactive_brokers.ib_broker import IBBroker
from qf_lib.settings import Settings


class LiveTradingSession(TradingSession):
    """
    Encapsulates the settings and components for Live Trading
    """

    def __init__(self, trading_session_name: str, container: Container, live_trading_settings: LiveTradingSettings):
        """
        Set up the configuration of all elements.
        """
        super().__init__()
        self.logger = qf_logger.getChild(self.__class__.__name__)
        self.trading_session_name = trading_session_name

        self.settings = container.resolve(Settings)  # type: Settings
        self.data_provider = container.resolve(BloombergDataProvider)  # type: BloombergDataProvider
        self.pdf_exporter = container.resolve(PDFExporter)  # type: PDFExporter
        self.excel_exporter = container.resolve(ExcelExporter)  # type: ExcelExporter
        self.email_publisher = container.resolve(EmailPublisher)  # type: EmailPublisher

        self.timer = RealTimer()
        self.notifiers = Notifiers(self.timer)
        self.event_manager = self._create_event_manager(self.timer, self.notifiers)
        self.time_flow_controller = LiveSessionTimeFlowController(
            self.notifiers.scheduler, self.event_manager, self.timer, self.notifiers.empty_queue_event_notifier)

        self.data_handler = DataHandler(self.data_provider, self.timer)

        self.monitor = LiveTradingMonitor(self.notifiers, container, live_trading_settings)
        self.broker = IBBroker()

        self.contract_ticker_mapper = VolStrategyContractTickerMapper()
        self.order_factory = OrderFactory(self.broker, self.data_handler, self.contract_ticker_mapper)
        self.position_sizer = InitialRiskPositionSizer(
            self.broker, self.data_handler, self.order_factory, self.contract_ticker_mapper,
            live_trading_settings.initial_risk)

        self.logger.info(
            "\n".join([
                "Creating Backtest Trading Session: ",
                "\tTrading Session Name: {}".format(trading_session_name),
                "\tSettings: {}".format(self.settings.__class__.__name__),
                "\tData Provider: {}".format(self.data_provider.__class__.__name__),
                "\tPDF Exporter: {}".format(self.pdf_exporter.__class__.__name__),
                "\tExcel Exporter: {}".format(self.excel_exporter.__class__.__name__),
                "\tTimer: {}".format(self.timer.__class__.__name__),
                "\tNotifiers: {}".format(self.notifiers.__class__.__name__),
                "\tEvent Manager: {}".format(self.event_manager.__class__.__name__),
                "\tTime Flow Controller: {}".format(self.time_flow_controller.__class__.__name__),
                "\tData Handler: {}".format(self.data_handler.__class__.__name__),
                "\tMonitor: {}".format(self.monitor.__class__.__name__),
                "\tBroker: {}".format(self.broker.__class__.__name__),
                "\tContract-Ticker Mapper: {}".format(self.contract_ticker_mapper.__class__.__name__),
                "\tOrder Factory: {}".format(self.order_factory.__class__.__name__),
                "\tPosition Sizer: {}".format(self.position_sizer.__class__.__name__),
                "\tSettings Live Trading: {}".format(str(live_trading_settings))
            ])
        )
