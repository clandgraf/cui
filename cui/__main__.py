import imp

from cui import cui_core

def main():
    imp.load_source('cui.init', './init.py')
    core = cui_core.Core()
    core.run()

if __name__ == '__main__':
    main()
