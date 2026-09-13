Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
command = "cmd /c """ & appDir & "\start-erii.cmd"""
CreateObject("WScript.Shell").Run command, 0, False
