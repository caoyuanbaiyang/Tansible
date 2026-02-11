# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['venv\\Lib\\site-packages'],
             binaries=[],
             datas=[],
             hiddenimports=['model.CheckConnect.CheckConnect','model.CheckHostname.CheckHostname', 'model.DbPwdModify.DbPwdModify', 'model.DbPwdModifys.DbPwdModifys', 'model.Tsftp.Tsftp','model.Tsftp1.Tsftp1', 'model.Tshell.Tshell', 'model.Tupload.Tupload', 'model.Tvsget1.Tvsget1', 'model.SysPwdModify.SysPwdModify', 'model.shell_invoke.shell_invoke'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Tansible3.2',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
