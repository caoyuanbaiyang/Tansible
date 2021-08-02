# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['E:\\PyCharmProject\\Tansible\\main.py'],
             pathex=['C:\\Users\\hp\\AppData\\Local\\Programs\\Python\\Python37\\Lib', 'C:\\Users\\hp\\AppData\\Local\\Programs\\Python\\Python37\\libs', 'E:\\PyCharmProject\\Tansible\\venv\\Lib\\site-packages', 'E:\\PyCharmProject\\程序发布\\Tansible', 'E:\\PyCharmProject\\Tansible'],
             binaries=[],
             datas=[],
             hiddenimports=['model.CheckHostname.CheckHostname', 'model.DbPwdModify.DbPwdModify', 'model.DbPwdModifys.DbPwdModifys', 'model.Tsftp.Tsftp', 'model.Tshell.Tshell', 'model.Tshell.Tsupershell', 'model.Tupload.Tupload', 'model.Tvsget.Tvsget', 'model.Tvsget1.Tvsget1', 'model.SysPwdModify.SysPwdModify'],
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
          name='Tansible',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
