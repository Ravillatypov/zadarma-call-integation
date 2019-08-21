from settings.base import Config

try:
    from settings.local import Config
except:
    pass

