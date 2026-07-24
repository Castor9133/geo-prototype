import unittest
from pathlib import Path

from app.web.company_pages import SUITE_REDIRECT, router


class CompanyPagesTests(unittest.TestCase):
    def test_company_router_only_redirects_to_suite(self):
        self.assertEqual(SUITE_REDIRECT, "/suite")
        paths = {getattr(route, "path", "") for route in router.routes}
        self.assertIn("/companies", paths)
        self.assertIn("/companies/{identifier:path}", paths)
        self.assertIn("/company", paths)
        self.assertIn("/c/{identifier:path}", paths)
        self.assertIn("/submit-company", paths)

    def test_static_company_product_files_are_removed(self):
        repo_root = Path(__file__).resolve().parents[2]
        for relative in (
            "dist/company.html",
            "dist/company-submit.html",
            "dist/js/company.js",
            "dist/js/submit-company.js",
            "dist/js/company-submit-page.js",
            "dist/css/company.css",
            "dist/admin/companies.html",
        ):
            self.assertFalse(
                (repo_root / relative).exists(),
                f"expected removed product file: {relative}",
            )


if __name__ == "__main__":
    unittest.main()
