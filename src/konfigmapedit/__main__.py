# __main__.py

from konfigmapedit import app_module

def main():
    is_success = app_module.main()
    exit(0 if is_success else 1)

if __name__ == '__main__':
    main()

