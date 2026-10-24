import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import server

def test_workflow_execution():
    print("==================================================", flush=True)
    print("  TESTING DASHBOARD WORKFLOW DISPATCHERS", flush=True)
    print("==================================================", flush=True)

    # 1. Test Explorer Workflow with mode='tests'
    print("\n[TEST 1] Testing Normal Explorer dispatcher with mode='tests'...", flush=True)
    req_exp = server.RunExplorerRequest(
        mode="tests"
    )
    res = server.api_execute_run_explorer(req_exp)
    assert res["success"] is True
    pid = res["process"]["pid"]
    print(f" -> Started Explorer test suite. PID: {pid}", flush=True)

    # Let tests run and capture logs
    time.sleep(2.0)
    logs = server.api_process_logs(offset=0)
    print(f" -> Captured {logs['total']} log lines in buffer.", flush=True)
    assert logs['total'] > 5

    # Stop process cleanly
    server.api_process_stop()
    time.sleep(1.0)
    st = server.api_process_status()
    print(f" -> Process stopped: status={st['status']}", flush=True)

    # 2. Test Agent Explorer dispatcher
    print("\n[TEST 2] Testing Agent Explorer dispatcher...", flush=True)
    req_agent = server.AgentExplorerRequest(
        budget=1,
        strategy="coverage",
        mode="adaptive",
        max_steps_per_target=10,
        tolerance=70.0,
        launch=False,
        verbose=False
    )
    res_agent = server.api_execute_agent_explorer(req_agent)
    assert res_agent["success"] is True
    pid_agent = res_agent["process"]["pid"]
    print(f" -> Agent Explorer started. PID: {pid_agent}", flush=True)

    time.sleep(2.0)
    logs_agent = server.api_process_logs(offset=0)
    print(f" -> Captured {logs_agent['total']} log lines.", flush=True)
    assert logs_agent['total'] > 0

    # Stop process
    stop_res = server.api_process_stop()
    time.sleep(1.0)
    print(f" -> Stop process signal sent. Status: {stop_res['status']}", flush=True)

    # 3. Test Run Game dispatcher
    print("\n[TEST 3] Testing Run Game dispatcher (Map 1)...", flush=True)
    req_game = server.RunGameRequest(
        map_num=1,
        mode="headless",
        frames=60,
        with_bot=False
    )
    res_game = server.api_execute_run_game(req_game)
    assert res_game["success"] is True
    pid_game = res_game["process"]["pid"]
    print(f" -> Run Game started on Map 1. PID: {pid_game}", flush=True)

    time.sleep(2.0)
    logs_game = server.api_process_logs(offset=0)
    print(f" -> Captured {logs_game['total']} log lines.", flush=True)

    server.api_process_stop()
    time.sleep(1.0)
    print(" -> Run Game stopped cleanly.", flush=True)

    print("\n==================================================", flush=True)
    print("  ALL THREE WORKFLOW DISPATCHERS VERIFIED!", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    test_workflow_execution()

