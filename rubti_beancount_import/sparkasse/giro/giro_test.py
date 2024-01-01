from os import path

from beancount.ingest import regression_pytest

from rubti_beancount_import.sparkasse.giro.giro import SpkGiroImporter

importer = SpkGiroImporter(
    iban="DE97269513110161869128", account="Assets:DE:SpkCGW:Checking"
)

directory = path.dirname(__file__)


@regression_pytest.with_importer(importer)
@regression_pytest.with_testdir(directory)
class TestImporter(regression_pytest.ImporterTestBase):
    pass
