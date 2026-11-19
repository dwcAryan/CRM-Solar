import os
import sys
import subprocess
import yaml
import json

def run():
    print("=" * 60)
    print("Starting Solar CRM - Phase 17 UAT Runner")
    print("=" * 60)

    # 1. Sync scenarios.yaml to scenarios.json
    yaml_path = os.path.join("docs", "uat", "scenarios.yaml")
    json_path = os.path.join("docs", "uat", "scenarios.json")

    print(f"[1/3] Converting {yaml_path} to {json_path}...")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    scenarios = data.get("scenarios", [])
    print(f"       Loaded {len(scenarios)} scenarios.")

    # 2. Run Playwright Parallel Runner
    print(f"[2/3] Executing automated UAT scenarios with 4 workers...")
    cmd = ["node", "scripts/execute_uat.js"]
    res = subprocess.run(cmd, cwd="frontend", shell=True)
    if res.returncode != 0:
        print(f"[ERROR] Playwright UAT runner exited with code {res.returncode}")
        sys.exit(res.returncode)

    # 3. Generate Reports
    print(f"[3/3] Generating UAT_TRACKER.xlsx and UAT_REPORT.md...")
    gen_cmd = [sys.executable, os.path.join("scripts", "generate_uat_reports.py")]
    subprocess.run(gen_cmd, check=True)

    print("\n" + "=" * 60)
    print("UAT EXECUTION AND REPORTING COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    run()
