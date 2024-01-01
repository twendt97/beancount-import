import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
from beancount.core import amount, data
from beancount.ingest.importer import ImporterProtocol


class BBVAImporter(ImporterProtocol):
    _expected_header = pd.Index(
        [
            "Unnamed: 0",
            "Fecha",
            "F.Valor",
            "Concepto",
            "Movimiento",
            "Importe",
            "Divisa",
            "Disponible",
            "Divisa.1",
            "Observaciones",
        ],
        dtype="object",
    )
    account: str
    account_number: str
    currency: str
    _txn_infos: dict = {}
    """Header line in Excel file"""
    _header_line: int = 4

    def __init__(
        self,
        account: str,
        account_number: str,
        account_mapping: Path = None,
        currency: str = "EUR",
    ) -> None:
        self.account = account
        self.account_number = account_number
        self.currency = currency
        if account_mapping is not None:
            f = open(account_mapping)
            self._txn_infos = json.load(f)
            f.close()

    def name(self) -> str:
        return "BBVA Checking"

    def identify(self, file) -> bool:
        """Return true if this importer matches the given file.

        Args:
          file: A cache.FileMemo instance.
        Returns:
          A boolean, true if this importer can handle this file.
        """
        if Path(file.name).suffix.lower() != ".xlsx":
            return False
        try:
            raw_content = pd.read_excel(file.name, header=self._header_line)
        except:
            return False
        return raw_content.columns.equals(self._expected_header)

    def file_account(self, file):
        return self.account

    def extract(self, file, existing_entries=None):
        raw_content = pd.read_excel(file.name, header=self._header_line)
        entries = []
        for ind, row in raw_content.iterrows():
            meta = data.new_metadata(filename=file.name, lineno=row.name)
            payee = row["Concepto"]
            units = amount.Amount(
                Decimal(str(round(row["Importe"], 2))), currency=self.currency
            )
            postings = [
                data.Posting(
                    self.account,
                    units=units,
                    cost=None,
                    price=None,
                    flag=None,
                    meta=meta,
                )
            ]
            txn_payee = payee
            narration = row["Movimiento"]

            if payee in self._txn_infos:
                postings.append(
                    data.Posting(
                        account=self._txn_infos[payee]["account"],
                        units=-units,
                        price=None,
                        flag=None,
                        meta=meta,
                        cost=None,
                    )
                )
                if "payee" in self._txn_infos[payee]:
                    txn_payee = self._txn_infos[payee]["payee"]
                if "narration" in self._txn_infos[payee]:
                    narration = self._txn_infos[payee]["narration"]

            txn = data.Transaction(
                meta=meta,
                date=row["Fecha"].date(),
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
        return f"BBVA_{self.account_number}.xlsx"

    def file_date(self, file):
        return max(map(lambda entry: entry.date, self.extract(file)))
