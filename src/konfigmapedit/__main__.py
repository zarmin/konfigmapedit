# __main__.py

import app

if __name__ == '__main__':
    is_success = app.main()
    exit(0 if is_success else 1)

