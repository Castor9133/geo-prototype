import unittest
from pathlib import Path

from app.web.tutorial_pages import SUITE_REDIRECT, router


class TutorialPagesTests(unittest.TestCase):
    def test_tutorial_router_only_redirects_to_suite(self):
        self.assertEqual(SUITE_REDIRECT, "/suite")
        paths = {getattr(route, "path", "") for route in router.routes}
        self.assertIn("/tutorial", paths)
        self.assertIn("/tutorial/{identifier:path}", paths)

    def test_static_tutorial_product_files_are_removed(self):
        repo_root = Path(__file__).resolve().parents[2]
        for relative in (
            "dist/tutorial.html",
            "dist/js/tutorial.js",
            "dist/css/tutorial.css",
            "dist/experts.html",
            "dist/js/experts.js",
            "dist/css/experts.css",
            "dist/admin/tutorials.html",
            "dist/admin/tutorials-edit.html",
            "dist/admin/experts.html",
        ):
            self.assertFalse(
                (repo_root / relative).exists(),
                f"expected removed product file: {relative}",
            )


if __name__ == "__main__":
    unittest.main()
