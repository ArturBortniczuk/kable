import os

class Config:
    SECRET_KEY = 'a84dc4f52e25f258dfee0dd1a4d4d0e9'
    MAIL_SERVER = 'smtp-eltron.ogicom.pl'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'kable@grupaeltron.pl'
    MAIL_PASSWORD = 'L1AkKTiNBjWgN'
    MAIL_DEFAULT_SENDER = 'kable@grupaeltron.pl'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///queries.db'
    EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'data.xlsx')

class ProductionConfig(Config):
    DEBUG = False
    BASE_DIR = '/home/ArturBortniczuk/myapp'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR}/instance/queries.db'
    EXCEL_PATH = os.path.join(BASE_DIR, 'data.xlsx')

# Wybierz konfigurację na podstawie zmiennej środowiskowej
config = ProductionConfig if os.getenv('FLASK_ENV') == 'production' else DevelopmentConfig