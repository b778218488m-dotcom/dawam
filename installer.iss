[Setup]
AppName=Fekra Dawam
AppVersion=1.0
DefaultDirName={autopf}\Fekra Dawam
DefaultGroupName=Fekra Dawam
OutputDir=Output
OutputBaseFilename=Fekra-Dawam-Setup
Compression=lzma
SolidCompression=yes
[Files]
Source: "dist\Fekra-Dawam.exe"; DestDir: "{app}"
[Icons]
Name: "{autoprograms}\Fekra Dawam"; Filename: "{app}\Fekra-Dawam.exe"
Name: "{autodesktop}\Fekra Dawam"; Filename: "{app}\Fekra-Dawam.exe"
[Run]
Filename: "{app}\Fekra-Dawam.exe"; Description: "Run Fekra Dawam"; Flags: postinstall nowait skipifsilent
