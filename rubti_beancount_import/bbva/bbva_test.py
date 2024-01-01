from os import path

from beancount.ingest import regression_pytest

from rubti_beancount_import.bbva.bbva import BBVAImporter

directory = path.dirname(__file__)
importer = BBVAImporter(
    "Assets:ES:BBVA:Checking", "ES4701825322250205327489", "test_mapping.json"
)


@regression_pytest.with_importer(importer)
@regression_pytest.with_testdir(directory)
class TestImporter(regression_pytest.ImporterTestBase):
    pass
