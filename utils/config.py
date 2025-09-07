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


def get_required_links():
    """
    Return both IDs and invite links for group & channel.
    """
    return {
        "group_id": get_config("required_group_id", ""),
        "group_link": get_config("required_group_link", ""),
        "channel_id": get_config("required_channel_id", ""),
        "channel_link": get_config("required_channel_link", "")
    }


def set_required_links(group_id: str, group_link: str, channel_id: str, channel_link: str):
    set_config("required_group_id", group_id)
    set_config("required_group_link", group_link)
    set_config("required_channel_id", channel_id)
    set_config("required_channel_link", channel_link)
