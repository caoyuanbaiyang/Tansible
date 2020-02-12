import yaml
import os
import re


class ReadCfg(object):
    def readcfg(self, filepath=None):
        configpath = ''
        if filepath:
            configpath = filepath
        else:
            root_dir = os.path.abspath('.')
            configpath = os.path.join(root_dir, "config", "hosts.yaml")
        with open(configpath, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        return cfg

    def remove_bom(self, config_path):
        content = open(config_path, encoding="utf-8").read()
        content = re.sub(r"\xfe\xff", "", content)
        content = re.sub(r"\ufeff", "", content)
        content = re.sub(r"\xff\xfe", "", content)
        content = re.sub(r"\xef\xbb\xbf", "", content)
        open(config_path, encoding="utf-8", mode='w').write(content)


if __name__ == '__main__':
    cfgct = ReadCfg().readcfg()
    print(cfgct)
    # print(cfgct['Host1']['hostname'])
