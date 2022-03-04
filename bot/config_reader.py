import configparser
from dataclasses import dataclass


@dataclass
class AthanasiusBot:
    token: str
    admin_ids: list
    cluster_link: str


@dataclass
class Config:
    Athanasius_bot: AthanasiusBot


def read_list_ids(old_list_ids: str) -> list:
    return [int(id_) for id_ in old_list_ids[1:-1].split(', ')]


def load_config(path: str):
    config = configparser.ConfigParser()
    config.read(path)

    athanasius_bot = config["Athanasius_bot"]

    return Config(
        Athanasius_bot=AthanasiusBot(
            token=athanasius_bot["token"],
            admin_ids=[_id for _id in read_list_ids(athanasius_bot["admin_ids"])],
            cluster_link=athanasius_bot['MongoDBClusterLink'],
        )
    )
