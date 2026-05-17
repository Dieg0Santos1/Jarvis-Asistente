Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """D:\CODE\Jarvis\.venv\Scripts\python.exe"" ""D:\CODE\Jarvis\main.py"" --auto", 0, False
Set WshShell = Nothing
