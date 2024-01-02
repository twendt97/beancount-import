import csv
import json
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from beancount.core import amount, data
from beancount.ingest.importer import ImporterProtocol

import rubti_beancount_import.utils as utils

DEFAULT_FIELDS = (
    "Umsatz getätigt von",
    "Belegdatum",
    "Buchungsdatum",
    "Originalbetrag",
    "Originalwährung",
    "Umrechnungskurs",
    "Buchungsbetrag",
    "Buchungswährung",
    "Transaktionsbeschreibung",
    "Transaktionsbeschreibung Zusatz",
    "Buchungsreferenz",
    "Gebührenschlüssel",
    "Länderkennzeichen",
    "BAR-Entgelt+Buchungsreferenz",
    "AEE+Buchungsreferenz",
    "Abrechnungskennzeichen",
)


class SpkMasterCardImporter(ImporterProtocol):
    last_four_digits: str
    account: str
    currency: str
    date_format: str
    file_encoding: str
    _fields: Sequence[str]
    _txn_infos: dict = {}
    account_mapper: utils.AccountMapper = None

    def __init__(
        self,
        account: str,
        last_four_digits: str,
        account_mapping: Path = None,
        currency: str = "EUR",
        date_format: str = "%d.%m.%y",
        file_encoding: str = "ISO-8859-1",
    ) -> None:
        self.account = account
        self.last_four_digits = last_four_digits
        self.currency = currency
        self.date_format = date_format
        self.file_encoding = file_encoding
        self._fields = DEFAULT_FIELDS
        if account_mapping is not None:
            f = open(account_mapping)
            self._txn_infos = json.load(f)
            f.close()

    def name(self) -> str:
        return "Sparkasse MasterCard"

    def identify(self, file) -> bool:
        """Return true if this importer matches the given file.

        Args:
          file: A cache.FileMemo instance.
        Returns:
          A boolean, true if this importer can handle this file.
        """
        if Path(file.name).suffix.lower() != ".csv":
            return False

        with open(file.name, encoding=self.file_encoding) as f:
            header = f.readline().strip()
            csv_row = f.readline().strip()

        expected_header = ";".join([f'"{field}"' for field in self._fields])

        header_match = header == expected_header
        card_number_match = (
            csv_row.split(";")[0].replace('"', "")[-4:] == self.last_four_digits
        )
        return header_match and card_number_match

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries=None):
        entries = []
        index = 0
        with open(file.name, encoding=self.file_encoding) as f:
            for index, row in enumerate(
                csv.DictReader(f, delimiter=";", quotechar='"')
            ):
                meta = data.new_metadata(filename=file.name, lineno=index)
                date: datetime = datetime.strptime(
                    row["Buchungsdatum"], self.date_format
                ).date()
                payee = row["Transaktionsbeschreibung"]
                units = amount.Amount(
                    utils.format_amount(row["Buchungsbetrag"]), currency=self.currency
                )
                postings = [
                    data.Posting(
                        self.account,
                        units=units,
                        cost=None,
                        price=None,
                        flag=None,
                        meta=None,
                    )
                ]
                txn_payee = payee
                narration = ""
                if payee in self._txn_infos:
                    postings.append(
                        data.Posting(
                            account=self._txn_infos[payee]["account"],
                            units=-units,
                            price=None,
                            flag=None,
                            meta=None,
                            cost=None,
                        )
                    )
                    if "payee" in self._txn_infos[payee]:
                        txn_payee = self._txn_infos[payee]["payee"]
                    if "narration" in self._txn_infos[payee]:
                        narration = self._txn_infos[payee]["narration"]

                txn = data.Transaction(
                    meta=meta,
                    date=date,
                    flag=self.FLAG,
                    payee=txn_payee,
                    narration=narration,
                    tags=data.EMPTY_SET,
                    links=data.EMPTY_SET,
                    postings=postings,
                )
                entries.append(txn)
        return entries

    def file_name(self, file):
        return f"MasterCard_{self.last_four_digits}.csv"

    def file_date(self, file):
        return max(map(lambda entry: entry.date, self.extract(file)))
