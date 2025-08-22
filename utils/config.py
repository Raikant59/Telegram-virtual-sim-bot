from models.config import Config

def get_config(key: str, default=None):
    cfg = Config.objects(key=key).first()
    return cfg.value if cfg else default

def set_config(key: str, value: str):
    cfg = Config.objects(key=key).first()
    if cfg:
        cfg.update(value=value)
    else:
        Config(key=key, value=value).save()
