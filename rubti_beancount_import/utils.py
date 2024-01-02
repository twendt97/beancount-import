from pathlib import Path
from decimal import Decimal
from identify import identify
import json
import yaml
from dataclasses import dataclass
from beancount.core import amount, data
from beancount.core import flags


@dataclass
class PayeeInfo:
    """User supplied information for specific payees"""

    account: str = None
    new_payee: str = None
    narration: str = None


def format_amount(amount: str) -> Decimal:
    """Removes German thousands separator and converts decimal point to US."""
    return Decimal(amount.replace(".", "").replace(",", "."))


class AccountMapper:
    mappings = {}

    def __init__(self, mapping_file: str):
        file_path = Path(mapping_file)
        if not file_path.is_file():
            raise FileNotFoundError(f"File {mapping_file} does not exist")
        file_tags = identify.tags_from_path(mapping_file)
        with open(file_path) as f:
            if "yaml" in file_tags:
                self.mappings = yaml.safe_load(f)
            elif "json" in file_tags:
                self.mappings = json.load(f)
            else:
                raise ValueError(
                    f"Format of file {mapping_file} has not been recognized. Make sure it is YAML or JSON"
                )

    def get_payee_details(self, payee: str):
        payee_info = PayeeInfo()
        if self._payee_known(payee):
            payee_info.account = self.mappings[payee]["account"]
            if "payee" in self.mappings[payee]:
                payee_info.new_payee = self.mappings[payee]["payee"]
            if "narration" in self.mappings[payee]:
                payee_info.narration = self.mappings[payee]["narration"]
            return payee_info
        else:
            return None

    def _payee_known(self, payee: str) -> bool:
        if payee in self.mappings:
            return True
        return False
