import copy
import json
import unittest
from pathlib import Path
from routing_arena.engine import (ConfigError, eligible, estimate_cost, estimated_quality,
                                  compare_policies, run_model, simulate, uniform, validate_config)
from routing_arena.report import render

CFG = json.loads((Path(__file__).resolve().parents[1] / "fixtures/workload.json").read_text())


class ArenaTests(unittest.TestCase):
    def test_workload_valid(self): validate_config(CFG["models"], CFG["tasks"])
    def test_three_policies(self): self.assertEqual(len(compare_policies(**CFG)), 3)
    def test_reproducible(self): self.assertEqual(compare_policies(**CFG), compare_policies(**CFG))
    def test_seed_changes_draw(self): self.assertNotEqual(uniform(1,"one","a","quality"), uniform(2,"one","a","quality"))
    def test_model_counts_sum(self):
        for r in compare_policies(**CFG): self.assertEqual(sum(r["model_counts"].values()), len(CFG["tasks"]))
    def test_all_high_risk_models_approved(self):
        approvals = {m["name"]: m["high_risk_approved"] for m in CFG["models"]}
        for r in compare_policies(**CFG):
            for out in r["outcomes"]:
                if out["risk"] == "high": self.assertTrue(approvals[out["model"]])
    def test_eligible_empty_for_no_high_risk(self):
        self.assertFalse(eligible([CFG["models"][0]], {"kind":"chat", "risk":"high"}))
    def test_cost_nonnegative(self): self.assertGreaterEqual(estimate_cost(CFG["models"][0],CFG["tasks"][0]), 0)
    def test_quality_range(self): self.assertLessEqual(estimated_quality(CFG["models"][0],CFG["tasks"][0]), 1)
    def test_different_model_outcome(self):
        task=CFG["tasks"][0]
        a,b=CFG["models"][:2]
        self.assertNotEqual(run_model(a,task,41).model,run_model(b,task,41).model)
    def test_hindsight_regret_nonnegative(self):
        for r in compare_policies(**CFG): self.assertGreaterEqual(r["hindsight_regret"],0)
    def test_cost_is_rounded(self):
        r=simulate(**CFG,policy="cheapest");self.assertEqual(r["total_cost_usd"],round(r["total_cost_usd"],6))
    def test_policy_rejected(self):
        with self.assertRaises(ConfigError): simulate(**CFG,policy="nonexistent")
    def test_duplicate_task_id(self):
        tasks=copy.deepcopy(CFG["tasks"]);tasks.append(tasks[0]);
        with self.assertRaises(ConfigError):validate_config(CFG["models"],tasks)
    def test_missing_models(self):
        with self.assertRaises(ConfigError):validate_config([],CFG["tasks"])
    def test_bad_difficulty(self):
        tasks=copy.deepcopy(CFG["tasks"]);tasks[0]["difficulty"]=2
        with self.assertRaises(ConfigError):validate_config(CFG["models"],tasks)
    def test_bad_token_count(self):
        tasks=copy.deepcopy(CFG["tasks"]);tasks[0]["input_tokens"]=-1
        with self.assertRaises(ConfigError):validate_config(CFG["models"],tasks)
    def test_high_risk_with_no_model(self):
        models=copy.deepcopy(CFG["models"])
        for m in models:m["high_risk_approved"]=False
        with self.assertRaises(ConfigError):validate_config(models,CFG["tasks"])
    def test_missing_quality(self):
        models=copy.deepcopy(CFG["models"]);del models[0]["quality"]["chat"]
        with self.assertRaises(ConfigError):validate_config(models,CFG["tasks"])
    def test_nan_cost(self):
        models=copy.deepcopy(CFG["models"]);models[0]["cost_input_per_m"]=float("nan")
        with self.assertRaises(ConfigError):validate_config(models,CFG["tasks"])
    def test_html_report(self):
        html=render(compare_policies(**CFG));self.assertIn("<!doctype html>",html);self.assertIn("Hindsight regret",html)
    def test_html_escape(self):
        a=compare_policies(**CFG);a[0]["outcomes"][0]["task_id"]="<script>alert(1)</script>"
        html=render(a);self.assertNotIn("<script>",html);self.assertIn("&lt;script&gt;",html)
    def test_no_tasks(self):
        with self.assertRaises(ConfigError):validate_config(CFG["models"],[])
    def test_seed_type(self):
        with self.assertRaises(ConfigError): simulate(**CFG,policy="cheapest",seed="bad")

if __name__ == "__main__": unittest.main()
