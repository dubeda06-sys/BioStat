Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\dubed\source\repos\BioStat"
WshShell.Run "python main.py", 0, False
