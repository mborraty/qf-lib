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

import pandas as pd

from demo_scripts.demo_configuration.demo_ioc import container
from qf_lib.analysis.leverage_analysis.leverage_analysis_sheet import LeverageAnalysisSheet
from qf_lib.common.utils.dateutils.string_to_date import str_to_date
from qf_lib.documents_utils.document_exporting.pdf_exporter import PDFExporter
from qf_lib.containers.series.qf_series import QFSeries
from qf_lib.settings import Settings


def get_data():
    start_date = str_to_date('2018-01-01')
    end_date = str_to_date('2018-03-31')

    leverage = [0.0, 35.44156135032152, 20.4064189938669, 29.30503471622806, 36.105775125679685, 36.105775125679685,
                36.105775125679685, 20.26809975833707, 25.039988498714965, 26.8882793797991, 26.79647501908233,
                24.720522010076884, 24.720522010076884, 24.720522010076884, 24.720522010076884, 41.53432721514686,
                19.471776345750072, 21.627846067916252, 23.564542323835582, 23.564542323835582, 23.564542323835582,
                24.232134393838255, 19.886986245311718, 30.977583321882726, 32.34181678642239, 15.428701203767291,
                15.428701203767291, 15.428701203767291, 15.313485599632601, 13.323073236835736, 14.47123718514658,
                16.246839190416612, 9.926760276030553, 9.926760276030553, 9.926760276030553, 10.647281458491173,
                17.58068766652164, 6.792324857595933, 6.252156037566934, 6.912657634585271, 6.912657634585271,
                6.912657634585271, 9.619769121896342, 7.003146770954902, 10.296039636914275, 12.59809755635282,
                8.264945308668239, 8.264945308668239, 8.264945308668239, 8.264945308668239, 10.51186588364227,
                14.397976622953122, 11.939113220670876, 12.023141297493325, 12.023141297493325, 12.023141297493325,
                13.45990304898729, 17.70343285023362, 18.11733523158772, 26.39815717612179, 15.091639763829537,
                15.091639763829537, 15.091639763829537, 12.912916203070063, 14.092103725350205, 16.015347740714667,
                12.348463002074837, 15.128151064651837, 15.128151064651837, 15.128151064651837, 17.472507867108213,
                29.062772339754254, 22.189994279725827, 18.178726111346286, 19.51053652188, 19.51053652188,
                19.51053652188, 29.29270275027655, 17.973386952423613, 38.41192209325428, 22.17712045497897,
                11.432618654412881, 11.432618654412881, 11.432618654412881, 33.75150034123088, 9.06506675336917,
                9.06506675336917, 9.06506675336917, 9.06506675336917, 9.06506675336917]

    index = pd.date_range(start_date, end_date)
    leverage_tms = QFSeries(data=leverage, index=index)

    return leverage_tms


def main():
    settings = container.resolve(Settings)  # type: Settings
    pdf_exporter = container.resolve(PDFExporter)  # type: PDFExporter
    leverage_tms = get_data()
    leverage_analysis_sheet = LeverageAnalysisSheet(settings, pdf_exporter, leverage_tms,
                                                    title="Sample leverage analysis")
    leverage_analysis_sheet.build_document()
    file_path = leverage_analysis_sheet.save()
    print("Saved file at {}".format(file_path))


if __name__ == "__main__":
    main()
