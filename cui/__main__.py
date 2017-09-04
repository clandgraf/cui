import traceback

from cui import core

def main():
    c = core.Core()
    try:
        c.run()
    except:
        c.logger.log(traceback.format_exc())

if __name__ == '__main__':
    main()
