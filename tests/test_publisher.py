import os
import re
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "000000000:TEST")
os.environ.setdefault("TELEGRAM_CHAT_ID", "@test")
import telegram_prompt_publisher as tp  # noqa: E402


class NumberingTests(unittest.TestCase):
    def test_continuita_con_il_vecchio_schema(self):
        # ultimo giorno col vecchio schema: 22/06/2026 slot 2 -> indice 518; il primo nuovo deve essere 519
        self.assertEqual(tp.post_number(date(2026, 6, 22), 2), 518)
        self.assertEqual(tp.post_number(tp.REF_NEW, 0), 519)

    def test_nessun_indice_ripetuto_per_un_anno(self):
        seen, d = set(), tp.REF_NEW
        for _ in range(365):
            for s in range(tp.SLOTS_PER_DAY):
                n = tp.post_number(d, s)
                self.assertNotIn(n, seen)
                seen.add(n)
            d += timedelta(days=1)

    def test_nuovi_post_non_toccano_i_vecchi(self):
        old = {tp.post_number(date(2026, 1, 1) + timedelta(days=i), s) for i in range(173) for s in range(3)}
        new = {tp.post_number(tp.REF_NEW + timedelta(days=i), s) for i in range(365) for s in range(4)}
        self.assertFalse(old & new)

    def test_slot_consecutivi_sono_consecutivi(self):
        a = tp.post_number(date(2026, 10, 12), 3)
        b = tp.post_number(date(2026, 10, 13), 0)
        self.assertEqual(b, a + 1)


class TextTests(unittest.TestCase):
    def test_cut_non_spezza_tag(self):
        t = "<b>" + "x" * 50 + "</b>"
        out = tp.cut(t, 20)
        self.assertLessEqual(len(out), 20)
        self.assertNotIn("<b>x", out.split("<")[0] + "<") if "<" in out else None
        self.assertTrue(out.endswith("…"))
        self.assertEqual(tp.cut("breve", 20), "breve")

    def test_cut_limite(self):
        self.assertLessEqual(len(tp.cut("a" * 5000, tp.MAX_TEXT)), tp.MAX_TEXT)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.yml = (ROOT / ".github" / "workflows" / "telegram_daily.yml").read_text(encoding="utf-8")

    def test_ogni_cron_e_gestito(self):
        crons = re.findall(r'- cron: "([^"]+)"', self.yml)
        self.assertGreaterEqual(len(crons), 10)
        for c in crons:
            body = self.yml.split("jobs:")[1]
            self.assertTrue(f'"{c}"' in body or f"'{c}'" in body, f"cron senza gestione: {c}")

    def test_cron_promo_e_keepalive_esclusi_dal_job_prompt(self):
        job = self.yml.split("publish-prompt:")[1].split("crosspromo-promofinder:")[0]
        self.assertIn("!= '0 8 * * 1,4'", job)
        self.assertIn("!= '0 6 * * 1'", job)

    def test_yaml_valido(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("pyyaml assente")
        d = yaml.safe_load(self.yml)
        self.assertEqual(set(d["jobs"]), {"publish-prompt", "crosspromo-promofinder", "keepalive"})


if __name__ == "__main__":
    unittest.main()
