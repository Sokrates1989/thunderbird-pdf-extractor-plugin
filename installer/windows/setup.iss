; Builds the per-user Windows setup around the already verified XPI and native-host artifacts.

#ifndef AppVersion
  #define AppVersion "0.4.0"
#endif

#define AppName "Thunderbird PDF Archiver"
#define AppPublisher "Sokrates1989"
#define AppUrl "https://github.com/Sokrates1989/thunderbird-pdf-extractor-plugin"
#define ExtensionId "thunderbird-pdf-archiver@sokrates1989.de"
#define ExtensionFileName "thunderbird-pdf-archiver-" + AppVersion + ".xpi"
#define GermanExtensionSource "thunderbird-pdf-archiver-" + AppVersion + "-de.xpi"
#define EnglishExtensionSource "thunderbird-pdf-archiver-" + AppVersion + "-en.xpi"
#define NativeHostName "de.sokrates1989.thunderbird_pdf_archiver"
#define NativeHostFileName "thunderbird-pdf-archiver-host.exe"
#define NativeManifestFileName NativeHostName + ".json"

#ifdef TestMode
  #define SetupAppId "ThunderbirdPdfArchiver.Setup.Test"
  #define ProductDataRoot "{localappdata}\ThunderbirdPdfArchiverInstallerTest"
  #define NativeRegistrySubkey "Software\ThunderbirdPdfArchiverInstallerTest\NativeMessagingHosts\" + NativeHostName
  #define ExtensionRegistrySubkey "Software\ThunderbirdPdfArchiverInstallerTest\Thunderbird\Extensions"
  #define SetupOutputName "Thunderbird-PDF-Archiver-Setup-" + AppVersion + "-test"
#else
  #define SetupAppId "ThunderbirdPdfArchiver.Setup"
  #define ProductDataRoot "{localappdata}\ThunderbirdPdfArchiver"
  #define NativeRegistrySubkey "Software\Mozilla\NativeMessagingHosts\" + NativeHostName
  #define ExtensionRegistrySubkey "Software\Mozilla\Thunderbird\Extensions"
  #define SetupOutputName "Thunderbird-PDF-Archiver-Setup-" + AppVersion + "-win-x64"
#endif

[Setup]
AppId={#SetupAppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={#ProductDataRoot}\{#AppVersion}
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
CloseApplications=no
RestartApplications=no
OutputDir=..\..\artifacts
OutputBaseFilename={#SetupOutputName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern dynamic
ShowLanguageDialog=yes
SetupLogging=yes
UninstallDisplayName={#AppName}
LicenseFile=..\..\LICENSE
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Windows installer for {#AppName}
VersionInfoCopyright=Copyright (C) {#AppPublisher}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
german.ThunderbirdCloseTitle=Thunderbird muss neu gestartet werden
german.ThunderbirdClosePrompt=Thunderbird wird gerade ausgeführt.%n%nSpeichern Sie zuerst offene Entwürfe. Der Installer fordert Thunderbird anschließend zum normalen Beenden auf und wartet bis zu 60 Sekunden. Thunderbird wird niemals erzwungen beendet.%n%nJetzt fortfahren?
german.ThunderbirdCloseFailed=Thunderbird konnte nicht sicher beendet werden. Speichern Sie offene Entwürfe, schließen Sie Thunderbird manuell und starten Sie den Installer erneut.
german.LaunchThunderbird=Thunderbird jetzt starten
german.ProfileInstallFailed=Die Erweiterung konnte nicht in das Thunderbird-Profil kopiert werden: %1
english.ThunderbirdCloseTitle=Thunderbird must be restarted
english.ThunderbirdClosePrompt=Thunderbird is currently running.%n%nSave any open drafts first. Setup will then request a normal shutdown and wait for up to 60 seconds. Thunderbird is never force-terminated.%n%nContinue now?
english.ThunderbirdCloseFailed=Thunderbird could not be closed safely. Save any open drafts, close Thunderbird manually, and run Setup again.
english.LaunchThunderbird=Start Thunderbird now
english.ProfileInstallFailed=The extension could not be copied into the Thunderbird profile: %1

[Files]
Source: "..\..\artifacts\native-host\{#NativeHostFileName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\artifacts\{#GermanExtensionSource}"; DestDir: "{app}"; DestName: "{#ExtensionFileName}"; Flags: ignoreversion; Languages: german
Source: "..\..\artifacts\{#EnglishExtensionSource}"; DestDir: "{app}"; DestName: "{#ExtensionFileName}"; Flags: ignoreversion; Languages: english
Source: "native-manifest.json"; DestDir: "{app}"; DestName: "{#NativeManifestFileName}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
#ifdef TestMode
Root: HKCU32; Subkey: "Software\ThunderbirdPdfArchiverInstallerTest"; Flags: uninsdeletekey
Root: HKCU64; Subkey: "Software\ThunderbirdPdfArchiverInstallerTest"; Flags: uninsdeletekey; Check: IsWin64
#endif
Root: HKCU32; Subkey: "{#NativeRegistrySubkey}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#NativeManifestFileName}"; Flags: uninsdeletekey
Root: HKCU64; Subkey: "{#NativeRegistrySubkey}"; ValueType: string; ValueName: ""; ValueData: "{app}\{#NativeManifestFileName}"; Flags: uninsdeletekey; Check: IsWin64
Root: HKCU32; Subkey: "{#ExtensionRegistrySubkey}"; ValueType: string; ValueName: "{#ExtensionId}"; ValueData: "{app}\{#ExtensionFileName}"; Flags: uninsdeletevalue uninsdeletekeyifempty
Root: HKCU64; Subkey: "{#ExtensionRegistrySubkey}"; ValueType: string; ValueName: "{#ExtensionId}"; ValueData: "{app}\{#ExtensionFileName}"; Flags: uninsdeletevalue uninsdeletekeyifempty; Check: IsWin64

[UninstallDelete]
Type: filesandordirs; Name: "{#ProductDataRoot}\logs"
Type: dirifempty; Name: "{#ProductDataRoot}"

[Run]
Filename: "{code:GetThunderbirdExecutable}"; Description: "{cm:LaunchThunderbird}"; Flags: nowait postinstall skipifsilent; Check: ShouldOfferThunderbirdLaunch

[Code]
var
  ThunderbirdExecutable: String;

function PowerShellExecutable: String;
begin
  Result := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
end;

function ThunderbirdIsRunning: Boolean;
var
  ExitCode: Integer;
  Parameters: String;
begin
  Parameters := '-NoProfile -NonInteractive -WindowStyle Hidden -Command ' +
    '"if (Get-Process -Name thunderbird -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"';
  Result := Exec(PowerShellExecutable, Parameters, '', SW_HIDE,
    ewWaitUntilTerminated, ExitCode) and (ExitCode = 0);
end;

function RequestSafeThunderbirdShutdown: Boolean;
var
  ExitCode: Integer;
  Parameters: String;
begin
  Parameters := '-NoProfile -NonInteractive -WindowStyle Hidden -Command ' +
    '"$limit = (Get-Date).AddSeconds(60); ' +
    '$processes = @(Get-Process -Name thunderbird -ErrorAction SilentlyContinue); ' +
    'foreach ($process in $processes) { [void]$process.CloseMainWindow() }; ' +
    'while ((Get-Process -Name thunderbird -ErrorAction SilentlyContinue) -and ' +
    '((Get-Date) -lt $limit)) { Start-Sleep -Milliseconds 500 }; ' +
    'if (Get-Process -Name thunderbird -ErrorAction SilentlyContinue) { exit 1 }"';
  Result := Exec(PowerShellExecutable, Parameters, '', SW_HIDE,
    ewWaitUntilTerminated, ExitCode) and (ExitCode = 0);
end;

function FindThunderbirdExecutable: String;
var
  Candidate: String;
begin
  Result := '';
  if RegQueryStringValue(HKCU,
      'Software\Microsoft\Windows\CurrentVersion\App Paths\thunderbird.exe',
      '', Candidate) and FileExists(Candidate) then
  begin
    Result := Candidate;
    Exit;
  end;
  if RegQueryStringValue(HKLM,
      'Software\Microsoft\Windows\CurrentVersion\App Paths\thunderbird.exe',
      '', Candidate) and FileExists(Candidate) then
  begin
    Result := Candidate;
    Exit;
  end;
  Candidate := ExpandConstant('{autopf}\Mozilla Thunderbird\thunderbird.exe');
  if FileExists(Candidate) then
    Result := Candidate;
end;

function ThunderbirdProfilesRoot: String;
begin
#ifdef TestMode
  Result := ExpandConstant('{#ProductDataRoot}\Profiles');
#else
  Result := ExpandConstant('{userappdata}\Thunderbird\Profiles');
#endif
end;

procedure InstallExtensionIntoExistingProfiles;
var
  FindRecord: TFindRec;
  ProfilesRoot: String;
  ProfileDirectory: String;
  ExtensionsDirectory: String;
  DestinationPath: String;
  SourcePath: String;
begin
  ProfilesRoot := ThunderbirdProfilesRoot;
  if not DirExists(ProfilesRoot) then
    Exit;

  SourcePath := ExpandConstant('{app}\{#ExtensionFileName}');
  if FindFirst(AddBackslash(ProfilesRoot) + '*', FindRecord) then
  begin
    try
      repeat
        if ((FindRecord.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and
           (FindRecord.Name <> '.') and (FindRecord.Name <> '..') then
        begin
          ProfileDirectory := AddBackslash(ProfilesRoot) + FindRecord.Name;
          ExtensionsDirectory := AddBackslash(ProfileDirectory) + 'extensions';
          if DirExists(ExtensionsDirectory) then
          begin
            DestinationPath := AddBackslash(ExtensionsDirectory) + '{#ExtensionId}.xpi';
            if not CopyFile(SourcePath, DestinationPath, False) then
              RaiseException(FmtMessage(CustomMessage('ProfileInstallFailed'), [DestinationPath]));
          end;
        end;
      until not FindNext(FindRecord);
    finally
      FindClose(FindRecord);
    end;
  end;
end;

procedure RemoveExtensionFromExistingProfiles;
var
  FindRecord: TFindRec;
  ProfilesRoot: String;
  Candidate: String;
begin
  ProfilesRoot := ThunderbirdProfilesRoot;
  if not DirExists(ProfilesRoot) then
    Exit;

  if FindFirst(AddBackslash(ProfilesRoot) + '*', FindRecord) then
  begin
    try
      repeat
        if ((FindRecord.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and
           (FindRecord.Name <> '.') and (FindRecord.Name <> '..') then
        begin
          Candidate := AddBackslash(ProfilesRoot) + FindRecord.Name +
            '\extensions\{#ExtensionId}.xpi';
          if FileExists(Candidate) and not DeleteFile(Candidate) then
            Log('Could not remove profile extension during uninstall: ' + Candidate);
        end;
      until not FindNext(FindRecord);
    finally
      FindClose(FindRecord);
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
#ifndef TestMode
  if ThunderbirdIsRunning then
  begin
    if MsgBox(CustomMessage('ThunderbirdClosePrompt'), mbConfirmation,
        MB_YESNO) <> IDYES then
    begin
      Result := CustomMessage('ThunderbirdCloseFailed');
      Exit;
    end;
    if not RequestSafeThunderbirdShutdown then
      Result := CustomMessage('ThunderbirdCloseFailed');
  end;
#endif
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    InstallExtensionIntoExistingProfiles;
end;

function InitializeUninstall: Boolean;
begin
  Result := True;
#ifndef TestMode
  if ThunderbirdIsRunning then
  begin
    if MsgBox(CustomMessage('ThunderbirdClosePrompt'), mbConfirmation,
        MB_YESNO) <> IDYES then
    begin
      Result := False;
      Exit;
    end;
    Result := RequestSafeThunderbirdShutdown;
    if not Result then
      MsgBox(CustomMessage('ThunderbirdCloseFailed'), mbError, MB_OK);
  end;
#endif
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RemoveExtensionFromExistingProfiles;
end;

function GetThunderbirdExecutable(Param: String): String;
begin
  if ThunderbirdExecutable = '' then
    ThunderbirdExecutable := FindThunderbirdExecutable;
  Result := ThunderbirdExecutable;
end;

function ShouldOfferThunderbirdLaunch: Boolean;
begin
#ifdef TestMode
  Result := False;
#else
  Result := GetThunderbirdExecutable('') <> '';
#endif
end;
