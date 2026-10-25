import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import server

def run_tests():
    print("Testing api_overview()...")
    ov = server.api_overview()
    print("Total bugs detected:", ov["stats"]["total_bugs_detected"])
    print("Critical bugs:", ov["stats"]["critical_bugs"])
    print("Benchmark bugs total:", ov["stats"]["benchmark_bugs_total"])
    print("Covered:", ov["stats"]["benchmark_bugs_covered"])
    assert ov["stats"]["total_bugs_detected"] > 0
    assert len(ov["findings"]) > 0

    print("\nTesting api_maps()...")
    maps = server.api_maps()
    print("Maps count:", len(maps["maps"]))
    assert len(maps["maps"]) == 5, f"Expected 5 maps, got {len(maps['maps'])}"
    for m in maps["maps"]:
        print(" - Map " + str(m["id"]) + ": " + m["title"] + " (" + str(len(m["benchmark_bugs"])) + " bugs)")

    print("\nTesting api_paths()...")
    paths = server.api_paths()
    print("Paths count:", len(paths["paths"]))
    assert len(paths["paths"]) > 0

    print("\nTesting api_process_status()...")
    st = server.api_process_status()
    print("Status:", st["status"])
    assert st["status"] == "idle"

    print("\nTesting api_telemetry_events()...")
    events = server.api_telemetry_events(limit=5)
    print("Events count:", len(events["events"]))

    print("\nTesting static files exist...")
    assert (server.STATIC_DIR / "index.html").exists()
    assert (server.STATIC_DIR / "css" / "dashboard.css").exists()
    assert (server.STATIC_DIR / "js" / "dashboard.js").exists()
    assert (server.STATIC_DIR / "js" / "terminal.js").exists()
    print("All static assets verified on disk.")

    print("\nTesting find_antigravity_cli()...")
    cli = server.find_antigravity_cli()
    print("Found Antigravity CLI:", cli)
    assert cli is not None, "Antigravity CLI must be found"

    print("\nTesting static elements for AI Agent...")
    html_text = (server.STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert 'id="sidebar-btn-ai-agent"' in html_text, "Sidebar AI Agent button must exist"
    assert 'id="btn-large-start-ai"' in html_text, "Large Start Button must exist"
    assert 'id="ai-agent-modal"' in html_text, "AI Agent Modal must exist"
    assert 'Gemini model through Antigravity' in html_text, "Gemini default model notice must exist"
    assert 'Run game QA using game-qa skill' in html_text, "Prompt text must be present"
    assert 'id="btn-force-refresh-qa"' in html_text, "Force refresh button must exist"
    assert 'Auto-Refreshed' in html_text, "Auto-refreshed badge must exist"
    print("All AI Agent & Auto-Refresh UI components verified in index.html.")

    print("\nTesting api_refresh_overview()...")
    refresh_res = server.api_refresh_overview()
    assert refresh_res["status"] == "success"
    assert "sync" in refresh_res
    assert refresh_res["overview"]["stats"]["total_bugs_detected"] >= 21
    print("Auto-refresh endpoint test passed successfully.")

    print("\n[ALL SERVER CORE INTEGRATION TESTS PASSED!]")

if __name__ == "__main__":
    run_tests()
