from __future__ import annotations

from abc import abstractmethod
from dataclasses import asdict, dataclass
from functools import cached_property
from typing import Any, Type

import yaml


@dataclass(kw_only=True, frozen=True)
class AbridgedCompose:
    services: dict[str, Service]
    volumes: dict[str, None] | None = None

    def for_compose_yml(self) -> dict[str, Any]:
        r = {"services": for_compose_yml_with_dict(self.services)}
        call_and_set_if_not_none(r, "volumes", self.volumes, for_compose_yml_with_dict)
        return r


@dataclass(kw_only=True, frozen=True)
class Service:
    _name: str
    image: str | None = None
    build: Build | None = None
    command: Command | None = None
    depends_on: str | list[str] | None = None
    ports: list[Port] | None = None
    volumes: list[Volume] | None = None

    def for_compose_yml(self) -> dict[str, Any]:
        r = {}
        call_and_set_if_not_none(r, "image", self.image, str)
        call_and_set_if_not_none(r, "build", self.build, for_compose_yml)
        call_and_set_if_not_none(r, "command", self.command, for_compose_yml)
        call_and_set_if_not_none(r, "depends_on", self.depends_on, for_compose_yml)
        call_and_set_if_not_none(r, "ports", self.ports, for_compose_yml_with_list)
        call_and_set_if_not_none(r, "volumes", self.volumes, for_compose_yml_with_list)
        return r


@dataclass(kw_only=True, frozen=True)
class Build:
    context: str
    args: dict[str, Any] | None = None

    def for_compose_yml(self) -> str | dict[str, str | dict]:
        if self.args is None:
            return str(self.context)
        else:
            return {
                "context": str(self.context),
                "args": dict(self.args),
            }


@dataclass(kw_only=True, frozen=True)
class Command:
    value: str | list[str]

    def for_compose_yml(self) -> str | list[str]:
        return self.value


@dataclass(kw_only=True, frozen=True)
class Port:
    value: str

    def for_compose_yml(self) -> str:
        return self.value


@dataclass(kw_only=True, frozen=True)
class Volume:
    source: str
    container_path: str

    def for_compose_yml(self) -> str:
        return f"{self.source}:{self.container_path}"


@dataclass(kw_only=True, frozen=True)
class SoftwareComponent:
    version: str

    @cached_property
    def abbr(self) -> str:
        return self.version.replace(".", "")

    @abstractmethod
    def up(
        self,
        postgresql: Postgresql,
        postgis: Postgis,
    ) -> tuple[Postgresql, Postgis]:
        ...


@dataclass(kw_only=True, frozen=True)
class Postgresql(SoftwareComponent):
    @cached_property
    def pgdata_volume_name(self) -> str:
        return f"pgdata{self.abbr}"

    @cached_property
    def pgdata_container_path(self) -> str:
        return f"/var/lib/pgdata/{self.version}/data"

    def up(
        self,
        postgresql: Postgresql,
        postgis: Postgis,
    ) -> tuple[Postgresql, Postgis]:
        if self == postgresql:
            raise ValueError("no change", self, postgresql)
        return self, postgis


@dataclass(kw_only=True, frozen=True)
class Postgis(SoftwareComponent):
    def up(
        self,
        postgresql: Postgresql,
        postgis: Postgis,
    ) -> tuple[Postgresql, Postgis]:
        if self == postgis:
            raise ValueError("no change", self, postgis)
        return postgresql, self


def for_compose_yml(obj: Any) -> Any:
    match obj:
        case None:
            return None
        case obj if hasattr(obj, "for_compose_yml"):
            return obj.for_compose_yml()
        case str(obj):
            return obj
        case dict(obj):
            return for_compose_yml_with_dict(obj)
        case list(obj):
            return for_compose_yml_with_list(obj)
        case _:
            return asdict(obj)


def for_compose_yml_with_dict(obj: dict) -> dict:
    return {key: for_compose_yml(value) for key, value in obj.items()}


def for_compose_yml_with_list(obj: list) -> list:
    return [for_compose_yml(item) for item in obj]


def call_and_set_if_not_none(container, key, value, fn) -> None:
    if value is not None:
        container[key] = fn(value)


def remove_keys_with_none_values_from_dict(d: dict) -> dict:
    """{'x': None} -> {}"""
    r = {}
    for k, v in d.items():
        if v is None:
            continue
        elif isinstance(v, dict):
            r[k] = remove_keys_with_none_values_from_dict(v)
        else:
            r[k] = v
    return r


def remove_private_keys_from_dict(d: dict) -> dict:
    """{'a':1, '_b':2} -> {'a':1}"""
    r = {}
    for k, v in d.items():
        if str(k).startswith("_"):
            continue
        elif isinstance(v, dict):
            r[k] = remove_private_keys_from_dict(v)
        else:
            r[k] = v
    return r


############################################################


POSTGRESQL_94 = Postgresql(version="9.4")
POSTGRESQL_95 = Postgresql(version="9.5")
POSTGRESQL_96 = Postgresql(version="9.6")
POSTGRESQL_11 = Postgresql(version="11")
POSTGRESQL_15 = Postgresql(version="15")

POSTGIS_21 = Postgis(version="2.1")
POSTGIS_22 = Postgis(version="2.2")
POSTGIS_23 = Postgis(version="2.3")
POSTGIS_24 = Postgis(version="2.4")
POSTGIS_33 = Postgis(version="3.3")


def postgis_package_version_abbr(postgresql: Postgresql, postgis: Postgis) -> str:
    if (postgis, postgresql) in [
        (POSTGIS_21, POSTGRESQL_94),
        (POSTGIS_22, POSTGRESQL_95),
        (POSTGIS_23, POSTGRESQL_96),
    ]:
        return postgis.abbr[0]
    else:
        return postgis.abbr


############################################################


START_POSTGRESQL = POSTGRESQL_94
START_POSTGIS = POSTGIS_21
STEPS: list[SoftwareComponent] = [
    POSTGIS_24,
    POSTGRESQL_11,
    POSTGIS_33,
    POSTGRESQL_15,
]


BASE_SERVICE = Service(
    _name="base",
    image="base:el7",
    build=Build(context="base-el7"),
    command=Command(value="/usr/bin/true"),
)


service_list: list[Service] = [BASE_SERVICE]
volume_names: dict[str, None] = {}
postgresql = START_POSTGRESQL
postgis = START_POSTGIS
for step in [None] + STEPS:
    if step:
        postgresql, postgis = step.up(postgresql, postgis)
    tag = f"{postgis.abbr}_{postgresql.abbr}"
    name = f"postgis_{tag}"
    image = f"postgis:{tag}"
    db = Service(
        _name=f"{name}_db",
        image=image,
        build=Build(
            context="image-postgis",
            args=dict(
                postgresql_version_full=postgresql.version,
                postgresql_version_abbr=postgresql.abbr,
                postgis_package_version_abbr=postgis_package_version_abbr(
                    postgresql=postgresql,
                    postgis=postgis,
                ),
            ),
        ),
        command=Command(value="/usr/sbin/init"),
        ports=[Port(value="5432:5432")],
        volumes=[
            Volume(
                source=postgresql.pgdata_volume_name,
                container_path=postgresql.pgdata_container_path,
            )
        ],
    )
    volume_names[postgresql.pgdata_volume_name] = None
    cli = Service(
        _name=name,
        image=image,
        depends_on=[db._name],
    )
    service_list.append(cli)
    service_list.append(db)

compose = AbridgedCompose(
    services={s._name: s for s in service_list},
    volumes={name: None for name in volume_names} if volume_names else None,
)


############################################################


class BlankNone:
    """Print None as blank when used as context manager

    Based on https://stackoverflow.com/a/67524482 and https://stackoverflow.com/a/37445121
    """

    def __init__(self) -> None:
        self.priors = {}
        self.representer_classes: list[Type[yaml.representer.BaseRepresenter]] = [
            yaml.Dumper,
            yaml.SafeDumper,
        ]

    def __enter__(self):
        assert not (self.priors)
        for representer_class in self.representer_classes:
            self.priors[representer_class] = representer_class.yaml_representers[
                type(None)
            ]
            representer_class.add_representer(
                type(None),
                lambda representer, _: representer.represent_scalar(
                    "tag:yaml.org,2002:null",
                    "",
                ),
            )

    def __exit__(self, exc_type, exc_val, exc_tb):
        for representer in self.representer_classes:
            representer.yaml_representers[type(None)] = self.priors.pop(representer)
        assert not (self.priors)


with BlankNone():
    print(yaml.safe_dump(data=for_compose_yml(compose), sort_keys=False))
