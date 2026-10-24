@echo off
REM run_eval.bat — Runs Antigravity Agent Game_QA Evaluation on Godot game logs

echo ===================================================
echo  Game_QA: Antigravity AI Agent Evaluator
echo  Skill: game-qa (White-Box GDScript Auditing)
echo  Sampling: 1st line, then multiples of 4: 4, 8, 12
echo ===================================================
echo.

if "%~1"=="" goto default_run

echo Running evaluation on custom log: %~1 [stride 4]
python eval.py --log "%~1" --stride 4 --ignore-checks
goto done

:default_run
echo Running evaluation on default game_events.jsonl [stride 4]
python eval.py --stride 4 --ignore-checks

:done
echo.
echo ===================================================
echo  Evaluation finished!
echo  Results: results\eval_results.json
echo  Report : report.md
echo ===================================================
pause
