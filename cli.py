"""
This script generates a CSV indicating the response times of each public comment from an agent.
This works only on 1 specific ticket.

Requires the following secrets (as environment variables):

  - ZENDESK_EMAIL: Zendesk user email
  - ZENDESK_TOKEN: Zendesk user API token
  - ZENDESK_SUBDOMAIN: Zendesk subdomain (e.g., foobar if you are on foobar.zendesk.com)

Example usage:

    # evaluates ticket 123, outputs in 123.csv
    $ poetry run python cli.py https://foobar.zendesk.com/agent/tickets/123
"""

from collections import defaultdict
import csv
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
import os
import re
from typing import Iterable, Optional
from urllib.parse import urlparse

import click
from zenpy import Zenpy
from zenpy.lib.api_objects import (
    Comment as ZenpyComment,
    User as ZenpyUser,
)


@dataclass
class Ticket:
    PATH_EXPRESSION = re.compile("^/agent/tickets/(?P<id>\d+)$")

    id: int

    @classmethod
    def from_url(cls, url: str):
        path = urlparse(url).path
        matched = cls.PATH_EXPRESSION.search(path)
        assert matched, f"Failed to parse info from URL: {url}"
        return cls(**matched.groupdict())


@dataclass
class User:
    ROLES_AGENT = ["agent", "admin"]

    name: str
    email: str
    role: str
    time_zone: str
    locale: str
    organization_id: int

    @classmethod
    def from_zenpyuser(cls, user: ZenpyUser):
        return cls(
            name=user.name,
            email=user.email,
            role=user.role,
            time_zone=user.iana_time_zone,
            locale=user.locale,
            organization_id=user.organization_id,
        )

    def is_agent(self) -> bool:
        return self.role in self.ROLES_AGENT


@dataclass
class Response:
    user: User = field(init=False)
    responded_at: datetime = field(init=False)
    # ideally, make this private;
    # no need to expose this
    created_at: str
    author: ZenpyUser

    def __post_init__(self):
        # HACK: not ideal but Python's datetime.datetime.fromisoformat does not parse the `Z` notation.
        # Hence, we "chip" off this last `Z` character.
        self.responded_at = datetime.fromisoformat(self.created_at[:-1])
        self.user = User.from_zenpyuser(self.author)


def _zendesk_creds() -> dict:
    return {
        "email": os.environ["ZENDESK_EMAIL"],
        "token": os.environ["ZENDESK_TOKEN"],
        "subdomain": os.environ["ZENDESK_SUBDOMAIN"],
    }


@dataclass
class ResponseTime:
    asked_at: datetime
    answered_at: datetime
    duration: timedelta = field(init=False)

    def __post_init__(self):
        self.duration = self.answered_at - self.asked_at

    def formula(self):
        return f"{self.answered_at} - {self.asked_at} = {self.duration}"

    def __str__(self):
        return self.formula()

    def weekends(self) -> Iterable[datetime]:
        for i in range(self.duration.days + 1):
            dt = self.asked_at + timedelta(days=i)
            # Monday is 0, Saturday = 5, Sunday = 6
            is_a_weekend = dt.weekday() >= 5
            if is_a_weekend:
                yield dt.date()


@dataclass
class Evaulation:
    response: Response
    time_taken: Optional[ResponseTime]

    FIELDS = [
        "email",
        "user type",
        "commented at",
        "formula",
        "weekends",
        "response time",
    ]

    def as_record(self) -> dict:
        record = defaultdict()
        record.update(
            {
                "email": self.response.user.email,
                "user type": "agent" if self.response.user.is_agent() else "customer",
                "commented at": str(self.response.responded_at),
            }
        )
        if self.time_taken:
            record.update(
                {
                    "formula": self.time_taken.formula(),
                    "weekends": ",".join([str(d) for d in self.time_taken.weekends()]),
                    "response time": str(self.time_taken.duration),
                }
            )
        return record


class Evaluate:
    def __init__(self, responses: Iterable[Response]):
        # Assumptions:
        #   - Responses are sorted in ascending order.
        #   - First response is by a customer.
        self.responses = responses

    def __len__(self):
        return len(self.responses)

    def __iter__(self):
        prev = None
        last_customer_response = None

        while True:
            try:
                current = next(self.responses)
            except StopIteration:
                break
            resp_time = None
            if current.user.is_agent() and not prev.user.is_agent():
                # get & calculate response time
                resp_time = ResponseTime(
                    asked_at=last_customer_response.responded_at,
                    answered_at=current.responded_at,
                )
            elif not current.user.is_agent():
                if not prev or prev.user.is_agent():
                    last_customer_response = current
            yield Evaulation(response=current, time_taken=resp_time)
            prev = current


@lru_cache(maxsize=1)
def _zendesk() -> Zenpy:
    return Zenpy(**_zendesk_creds())


def _zendesk_comments(ticket_id: int) -> Iterable[ZenpyComment]:
    zd = _zendesk()
    return zd.tickets.comments(ticket=ticket_id)


def responses(ticket_url: str) -> Iterable[Response]:
    for c in _zendesk_comments(ticket_url):
        # only yield public comments (responses)
        if c.public:
            yield Response(
                author=c.author,
                created_at=c.created_at,
            )


@click.command()
@click.argument("ticket_url", nargs=1)
@click.option("--output", "-o", required=False, type=click.Path(exists=False))
def cli(ticket_url: str, output: str):
    """ """
    ticket = Ticket.from_url(ticket_url)

    click.secho(f"Evaluating {ticket_url}", fg="yellow")
    evaluated = Evaluate(responses(ticket.id))
    click.secho(f"Evaluated {ticket_url}", fg="green")

    out = output or f"{ticket.id}.csv"
    assert os.path.splitext(out)[1] == ".csv"

    with open(out, "w") as outfile:
        w = csv.DictWriter(outfile, fieldnames=Evaulation.FIELDS)
        w.writeheader()
        for e in evaluated:
            w.writerow(e.as_record())

    click.secho(f"Generated evaluated output: {out}", fg="green")


if __name__ == "__main__":
    cli()
