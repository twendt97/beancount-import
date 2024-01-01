import csv
import json
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from beancount.core import amount, data
from beancount.ingest import importer

DEFAULT_FIELDS = (
    "Auftragskonto",
    "Buchungstag",
    "Valutadatum",
    "Buchungstext",
    "Verwendungszweck",
    "Glaeubiger ID",
    "Mandatsreferenz",
    "Kundenreferenz (End-to-End)",
    "Sammlerreferenz",
    "Lastschrift Ursprungsbetrag",
    "Auslagenersatz Ruecklastschrift",
    "Beguenstigter/Zahlungspflichtiger",
    "Kontonummer/IBAN",
    "BIC (SWIFT-Code)",
    "Betrag",
    "Waehrung",
    "Info",
)


class SpkGiroImporter(importer.ImporterProtocol):
    _txn_infos: dict = {}
    _fields: Sequence[str]
    iban: str
    account: str
    currency: str
    date_format: str
    file_encoding: str

    def __init__(
        self,
        iban: str,
        account: str,
        currency: str = "EUR",
        date_format: str = "%d.%m.%y",
        file_encoding: str = "ISO-8859-1",
        account_mapping: Path = None,
    ):
        self.iban = iban
        self.account = account
        self.currency = currency
        self.date_format = date_format
        self.file_encoding = file_encoding
        self._fields = DEFAULT_FIELDS
        if account_mapping is not None:
            f = open(account_mapping)
            self._txn_infos = json.load(f)
            f.close()

    def _fmt_amount(self, amount: str) -> Decimal:
        """Removes German thousands separator and converts decimal point to US."""
        return Decimal(amount.replace(".", "").replace(",", "."))

    def identify(self, file):
        if Path(file.name).suffix.lower() != ".csv":
            return False
        with open(file.name, encoding=self.file_encoding) as f:
            header = f.readline().strip()
            csv_row = f.readline().strip()

        expected_header = ";".join([f'"{field}"' for field in self._fields])

        header_match = header == expected_header
        iban_match = csv_row.split(";")[0].replace('"', "") == self.iban
        return header_match and iban_match

    def extract(self, file, existing_entries=None):
        entries = []
        index = 0
        with open(file.name, encoding=self.file_encoding) as f:
            for index, row in enumerate(
                csv.DictReader(f, delimiter=";", quotechar='"')
            ):
                meta = data.new_metadata(filename=file.name, lineno=index)
                date: datetime = datetime.strptime(
                    row["Buchungstag"], self.date_format
                ).date()
                payee = row["Beguenstigter/Zahlungspflichtiger"]
                units = amount.Amount(
                    self._fmt_amount(row["Betrag"]), currency=self.currency
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
                narration = row["Verwendungszweck"]
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

    def file_account(self, file):
        return self.account

    def file_name(self, file):
        return f"{self.iban}.csv"

    def file_date(self, file):
        return max(map(lambda entry: entry.date, self.extract(file)))
