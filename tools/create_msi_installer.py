import os

def generate_wix_script(version, exe_name="ReportFlow.exe"):
    """
    تولید یک فایل WiX (.wxs) برای ساخت نصب‌کننده MSI.
    این اسکریپت ساختار استاندارد نصب در Program Files و ایجاد Shortcut را فراهم می‌کند.
    """
    wxs_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
    <Product Id="*" Name="ReportFlow Automation" Language="1033" Version="{version}" Manufacturer="Ali Marandi" UpgradeCode="7e5f4a21-3c2b-4d1a-9e8f-5b6c7d8e9f0a">
        <Package InstallerVersion="200" Compressed="yes" InstallScope="perMachine" />

        <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />
        <MediaTemplate EmbedCab="yes" />

        <Feature Id="ProductFeature" Title="ReportFlow" Level="1">
            <ComponentGroupRef Id="ProductComponents" />
            <ComponentRef Id="ApplicationShortcut" />
        </Feature>
    </Product>

    <Fragment>
        <Directory Id="TARGETDIR" Name="SourceDir">
            <Directory Id="ProgramFilesFolder">
                <Directory Id="INSTALLFOLDER" Name="ReportFlow" />
            </Directory>
            <Directory Id="ProgramMenuFolder">
                <Directory Id="ApplicationProgramsFolder" Name="ReportFlow"/>
            </Directory>
        </Directory>
    </Fragment>

    <Fragment>
        <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
            <Component Id="MainExecutable">
                <File Source="dist\\{exe_name}" Id="ReportFlowEXE" KeyPath="yes" Checksum="yes" />
            </Component>
        </ComponentGroup>

        <DirectoryRef Id="ApplicationProgramsFolder">
            <Component Id="ApplicationShortcut" Guid="*">
                <Shortcut Id="ApplicationStartMenuShortcut" 
                          Name="ReportFlow" 
                          Description="Automated Financial Reporting"
                          Target="[INSTALLFOLDER]{exe_name}"
                          WorkingDirectory="INSTALLFOLDER"/>
                <RemoveFolder Id="CleanUpShortCut" On="uninstall"/>
                <RegistryValue Root="HKCU" Key="Software\\AliMarandi\\ReportFlow" Name="installed" Type="integer" Value="1" KeyPath="yes"/>
            </Component>
        </DirectoryRef>
    </Fragment>
</Wix>
"""
    with open("reportflow.wxs", "w", encoding="utf-8") as f:
        f.write(wxs_content)
    
    print("Generated reportflow.wxs")
    print("\nTo build the MSI, run these commands on a Windows machine with WiX Toolset installed:")
    print("1. candle reportflow.wxs")
    print("2. light reportflow.obj -o ReportFlowInstaller.msi")

if __name__ == "__main__":
    # استخراج نسخه از فایل اصلی یا ورودی کاربر
    generate_wix_script("1.3.0")
