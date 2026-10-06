"""Integration test for bank profile download and transaction processing pipeline."""

import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

import pandas as pd

from banktamer.cli import main
from banktamer.scraper import BankProfile


class TestProfileIntegration(unittest.TestCase):
    """End-to-end integration test for profile-driven download and report generation."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create dummy Santander Excel file with skiprows=7
        self.sample_excel_path = os.path.join(self.test_dir, "santander_sample.xlsx")
        header_padding = [["Banco Santander Statement"]] + [[""]] * 6
        data = [
            ["04/10/2026", "NOMINA EMPRESA", 2500.0],
            ["05/10/2026", "COMPRA MERCADONA", -85.50],
        ]
        df_padding = pd.DataFrame(header_padding)
        df_content = pd.DataFrame(data, columns=["FECHA OPERACIÓN", "CONCEPTO", "IMPORTE EUR"])
        with pd.ExcelWriter(self.sample_excel_path) as writer:
            df_padding.to_excel(writer, index=False, header=False)
            df_content.to_excel(writer, startrow=7, index=False)

        # Set Santander credentials in environment
        os.environ["SANTANDER_USERNAME"] = "12345678Z"
        os.environ["SANTANDER_PASSWORD"] = "my_secret_pass"

    def tearDown(self) -> None:
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)
        os.environ.pop("SANTANDER_USERNAME", None)
        os.environ.pop("SANTANDER_PASSWORD", None)

    def test_profile_santander_end_to_end(self) -> None:
        """Verify that --profile santander downloads the export and completes full analytics pipeline."""
        download_dir = os.path.join(self.test_dir, "downloads")

        # Create mock scraper that copies the sample file to download_dir
        class MockScraper:
            def download(
                self,
                profile: BankProfile,
                download_dir: str,
                headless: bool | None = None,
            ) -> str:
                self.recorded_profile = profile
                self.recorded_headless = headless
                os.makedirs(download_dir, exist_ok=True)
                target = os.path.join(download_dir, "transactions_2026-10-04.xlsx")
                shutil.copy(self_ref.sample_excel_path, target)
                return target

        self_ref = self
        mock_scraper_instance = MockScraper()

        out = StringIO()
        cli_args = [
            "banktamer",
            "--profile",
            "santander",
            "--download-dir",
            download_dir,
        ]

        from unittest.mock import patch

        with patch("sys.argv", cli_args), patch("banktamer.cli.BankScraper", return_value=mock_scraper_instance):
            with redirect_stdout(out):
                main()

        output = out.getvalue()
        self.assertEqual(mock_scraper_instance.recorded_profile.bank, "santander-es")
        self.assertIn("NOMINA EMPRESA", output)
        self.assertIn("2500.00", output)
        self.assertIn("85.50", output)


if __name__ == "__main__":
    unittest.main()
