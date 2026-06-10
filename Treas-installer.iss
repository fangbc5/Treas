; Treas 淼淼百宝箱 - Windows 安装程序配置 (Inno Setup)
; 生成安装包命令: ISCC.exe Treas-installer.iss

#define MyAppName "Treas"
#define MyAppDisplayName "Treas - 淼淼百宝箱"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Treas"
#define MyAppURL "https://github.com/fangbc5/Treas"
#define MyAppExeName "Treas.exe"
#define MyAppIdentifier "com.treas.app"

[Setup]
; 应用信息
AppId={{B8F5D3A2-7E1C-4F9A-A5D6-3E7F8B2C1D40}
AppName={#MyAppDisplayName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppDisplayName}
UninstallDisplayName={#MyAppDisplayName}
UninstallDisplayIcon={app}\{#MyAppExeName}

; 输出设置
OutputDir=installer_output
OutputBaseFilename=Treas-Setup-{#MyAppVersion}
SetupIconFile=resources\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; 权限
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; 安装界面
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 包含 PyInstaller 打包输出的所有文件
Source: "dist\Treas\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppDisplayName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\_internal\resources\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppDisplayName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent