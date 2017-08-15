import imp
import traceback

from cui import cui_core

def main():
    cui_init = imp.load_source('cui.init', './init.py')
    core = cui_core.Core(cui_init)
    core.set_state('tab-stop', 4)
    try:
        core.run()
    except:
        core.logger.log(traceback.format_exc())

if __name__ == '__main__':
    main()
