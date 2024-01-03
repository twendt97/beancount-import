from pathlib import Path
from decimal import Decimal
from identify import identify
import json
import yaml
from dataclasses import dataclass

from beancount.core import amount, data, flags
from datetime import datetime


def format_amount(amount: str) -> Decimal:
    """Removes German thousands separator and converts decimal point to US."""
    return Decimal(amount.replace(".", "").replace(",", "."))


def create_posting(account: str, units: amount, meta: dict) -> data.Posting:
    return data.Posting(
        account=account,
        units=units,
        cost=None,
        price=None,
        flag=None,
        meta=meta,
    )


def create_transaction(
    postings: list[data.Posting], date: datetime, meta: dict, payee: str, narration: str
) -> data.Transaction:
    return data.Transaction(
        meta=meta,
        date=date,
        flag=flags.FLAG_OKAY,
        payee=payee,
        narration=narration,
        tags=data.EMPTY_SET,
        links=data.EMPTY_SET,
        postings=postings,
    )


class AccountMapper:
    _mappings = {}

    def __init__(self, mapping_file: str = None):
        if mapping_file is None:
            return
        file_path = Path(mapping_file)
        if not file_path.is_file():
            raise FileNotFoundError(f"File {mapping_file} does not exist")
        file_tags = identify.tags_from_path(mapping_file)
        with open(file_path) as f:
            if "yaml" in file_tags:
                self._mappings = yaml.safe_load(f)
            elif "json" in file_tags:
                self._mappings = json.load(f)
            else:
                raise ValueError(
                    f"Format of file {mapping_file} has not been recognized. Make sure it is YAML or JSON"
                )

    def new_payee(self, payee: str) -> str:
        if not self._payee_known(payee) or "payee" not in self._mappings[payee]:
            return payee
        else:
            return self._mappings[payee]["payee"]

    def account(self, payee: str) -> str | None:
        if self._payee_known(payee):
            return self._mappings[payee]["account"]
        else:
            return None

    def narration(self, payee: str) -> str:
        if not self._payee_known(payee) or "narration" not in self._mappings[payee]:
            return ""
        else:
            return self._mappings[payee]["narration"]

    def _payee_known(self, payee: str) -> bool:
        if payee in self._mappings:
            return True
        return False