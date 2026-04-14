import unittest
import subprocess
import os
import shutil
import tempfile
import sys
from pathlib import Path

class TestBinaryE2E(unittest.TestCase):
    """End-to-end tests for the compiled BankTamer binary."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build the binary once for all tests in this class."""
        cls.workspace_root = Path(__file__).parent.parent.parent.absolute()
        cls.dist_dir = cls.workspace_root / "dist"
        
        # Determine binary name based on OS
        suffix = ".exe" if sys.platform == "win32" else ""
        cls.binary_path = cls.dist_dir / f"banktamer{suffix}"

        # Build binary using the project's Makefile if it doesn't exist
        if cls.binary_path.exists():
            print(f"Binary found at {cls.binary_path}, skipping Nuitka build.")
        else:
            print(f"Building binary with Nuitka in {cls.workspace_root}... (this may take a few minutes)")
            
            # Find uv path
            uv_path = "/opt/homebrew/bin/uv"
            if not os.path.exists(uv_path):
                uv_path = shutil.which("uv") or "uv"

            result = subprocess.run(
                [uv_path, "run", "make", "dist-exe"],
                cwd=str(cls.workspace_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Build failed!\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
                raise RuntimeError("Failed to build the binary for E2E tests.")
        
        if not cls.binary_path.exists():
            raise FileNotFoundError(f"Binary not found at {cls.binary_path} after build.")

    def setUp(self) -> None:
        """Create a temporary directory for each test run."""
        self.test_dir = Path(tempfile.mkdtemp())
        # We don't want the binary to pick up any local config from the workspace
        # unless explicitly told to. Running from a temp dir ensures we test the bundled config.

    def tearDown(self) -> None:
        """Clean up the test directory."""
        shutil.rmtree(self.test_dir)

    def test_revolut_standalone_processing(self) -> None:
        """Verify the binary processes Revolut data using its bundled configuration."""
        # 1. Prepare data
        import pandas as pd
        excel_path = self.test_dir / "revolut_data.xlsx"
        data = {
            "Started Date": ["2024-01-01 10:00:00", "2024-01-05 15:30:00"],
            "Description": ["MERCADONA SUPERMERCADO", "AMAZON LUXEMBOURG"],
            "Amount": [-45.50, -120.00]
        }
        pd.DataFrame(data).to_excel(excel_path, index=False)

        # 2. Run the binary
        result = subprocess.run(
            [str(self.binary_path), "--bank", "revolut", "--category", "example", "--files", str(excel_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True
        )

        # 3. Verify success and output content
        self.assertEqual(result.returncode, 0, f"Binary failed with: {result.stderr}")
        output = result.stdout
        
        # Check for reports and categories
        self.assertIn("REPORT FOR 2024-01", output)
        self.assertIn("Grocery shopping", output)
        self.assertIn("Online shopping", output)
        self.assertIn("-165.50", output)  # Total expense
        self.assertIn("45.50", output)
        self.assertIn("120.00", output)

    def test_help_command(self) -> None:
        """Verify the binary help command works."""
        result = subprocess.run(
            [str(self.binary_path), "--help"],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("BankTamer CLI", result.stdout)
        self.assertIn("--bank", result.stdout)

    def test_invalid_bank_error(self) -> None:
        """Verify binary handles unknown banks with an error message."""
        result = subprocess.run(
            [str(self.binary_path), "--bank", "unknown-bank", "--files", "dummy.xlsx"],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True
        )
        # Should exit with error
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Configuration or Data Error", result.stderr)
        self.assertIn("unknown-bank", result.stderr)

if __name__ == "__main__":
    unittest.main()
