#define MyAppName "吓吓C盘"
#define MyAppVersion "1.0"
#define MyAppPublisher "TYU Software"
#define MyAppExeName "吓吓C盘.exe"

[Setup]
AppId={{B8A8E930-5F49-4E95-A89C-E00D48421E71}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=吓吓C盘_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ShowLanguageDialog=no
LanguageDetectionMethod=none

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Messages]
WelcomeLabel1=欢迎安装 {#MyAppName}
WelcomeLabel2=这将在您的计算机上安装 {#MyAppName}。%n%n建议在继续之前关闭所有其他应用程序。
FinishedLabel=安装完成。%n%n点击"完成"退出安装程序。
BeveledLabel=简体中文
ButtonNext=下一步(&N)
ButtonBack=上一步(&B)
ButtonCancel=取消(&C)
ButtonInstall=安装(&I)
ButtonFinish=完成(&F)
SelectDirLabel3=安装程序将安装 {#MyAppName} 到下列文件夹。
SelectDirBrowseLabel=点击"下一步"继续。如果要选择其他文件夹，请点击"浏览"。

[CustomMessages]
CreateDesktopIcon=创建桌面快捷方式(&D)
LaunchAfterInstall=安装完成后运行 {#MyAppName}

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "cleaner.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\cleaner.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\cleaner.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchAfterInstall}"; Flags: nowait postinstall skipifsilent runascurrentuser

[UninstallDelete]
Type: filesandordirs; Name: "{app}" 