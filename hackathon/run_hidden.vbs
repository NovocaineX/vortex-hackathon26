Set WshShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strPath = WScript.ScriptFullName
Set objFile = objFSO.GetFile(strPath)
strFolder = objFSO.GetParentFolderName(objFile) 

' Start Backend
WshShell.CurrentDirectory = strFolder & "\backend"
WshShell.Run "python main.py", 0, False

' Start Frontend 
WshShell.CurrentDirectory = strFolder
WshShell.Run "cmd /c python -m http.server 3000", 0, False
