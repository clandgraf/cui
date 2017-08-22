import imp
import traceback

from cui import core

def main():
    cui_init = imp.load_source('cui.init', './init.py')
    c = core.Core(cui_init)
    try:
        c.run()
    except:
        c.logger.log(traceback.format_exc())

if __name__ == '__main__':
    main()
