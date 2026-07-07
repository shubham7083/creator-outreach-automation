@echo off
cd /d "%~dp0.."
"C:\Users\sw040\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m streamlit run app/streamlit_app.py --server.headless=true --server.port=8501 --browser.gatherUsageStats=false >> outputs\streamlit.cmd.out.log 2>> outputs\streamlit.cmd.err.log
