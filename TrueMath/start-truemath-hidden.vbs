' start-truemath-hidden.vbs
' TrueMath ko terminal chupa ke start karega

Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell.exe -ExecutionPolicy Bypass -File """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & "\start-truemath.ps1""", 0
