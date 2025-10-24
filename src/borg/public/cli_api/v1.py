"""Pydantic models that can parse borg 1.x's JSON output.

The two top-level models are:

- `BorgLogLine`, which parses any line of borg's logging output,
- all `Borg*Result` classes, which parse the final JSON output of some borg commands.

The different types of log lines are defined in the other models.
"""

import json
import logging
from datetime import datetime
from typing import Any, List, Literal, Optional, Union

import pydantic
from typing_extensions import Self

_log = logging.getLogger(__name__)


class BaseBorgLogLine(pydantic.BaseModel):
    def get_level(self) -> int:
        """Get the log level for this line as a `logging` level value.

        If this is a log message with a levelname, use it.
        Otherwise, progress messages get `DEBUG` level, and other messages get `INFO`.
        """
        return logging.DEBUG


class ArchiveProgressLogLine(BaseBorgLogLine):
    type: Literal["archive_progress"]
    time: float
    finished: bool
    original_size: Optional[int] = None
    compressed_size: Optional[int] = None
    deduplicated_size: Optional[int] = None
    nfiles: Optional[int] = None
    path: Optional[str] = None


class ProgressMessage(BaseBorgLogLine):
    type: Literal["progress_message"]
    operation: int
    msgid: Optional[str]
    finished: bool
    message: Optional[str] = None
    time: float


class ProgressPercent(BaseBorgLogLine):
    type: Literal["progress_percent"]
    operation: int
    msgid: Optional[str] = None
    finished: bool
    message: Optional[str] = None
    current: Optional[int] = None
    info: Optional[List[str]] = None
    total: Optional[int] = None
    time: float


class FileStatus(BaseBorgLogLine):
    type: Literal["file_status"]
    status: str
    path: str


class LogMessage(BaseBorgLogLine):
    type: Literal["log_message"]
    time: float
    levelname: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    name: str
    message: str
    msgid: Optional[str] = None

    def get_level(self) -> int:
        try:
            return getattr(logging, self.levelname)
        except AttributeError:
            _log.warning(
                "could not find log level %s, giving the following message WARNING level: %s",
                self.levelname,
                json.dumps(self),
            )
            return logging.WARNING


_BorgLogLinePossibleTypes = Union[
    ArchiveProgressLogLine, ProgressMessage, ProgressPercent, FileStatus, LogMessage
]


class BorgLogLine(pydantic.RootModel[_BorgLogLinePossibleTypes]):
    """A log line from Borg with the `--log-json` argument.

    Those are typically printed by borg on stderr.

    """

    def get_level(self) -> int:
        return self.root.get_level()


class _BorgArchive(pydantic.BaseModel):
    """Basic archive attributes."""

    name: str
    id: str
    start: datetime


class _BorgArchiveStatistics(pydantic.BaseModel):
    """Statistics of an archive."""

    original_size: int
    compressed_size: int
    deduplicated_size: int
    nfiles: int


class _BorgLimitUsage(pydantic.BaseModel):
    """Usage of borg limits by an archive."""

    max_archive_size: float


class _BorgDetailedArchive(_BorgArchive):
    """Archive attributes, as printed by `json info` or `json create`.

    Fields only present in `borg info` output (not in `borg create`):
    - hostname, username, comment, chunker_params
    """

    end: datetime
    duration: float
    stats: _BorgArchiveStatistics
    limits: _BorgLimitUsage
    command_line: List[str]
    hostname: Optional[str] = None
    username: Optional[str] = None
    comment: Optional[str] = None
    chunker_params: Optional[Union[str, List[Union[str, int]]]] = None


class BorgCreateResult(pydantic.BaseModel):
    """JSON object printed at the end of `borg create`."""

    archive: _BorgDetailedArchive


class BorgListResult(pydantic.BaseModel):
    """JSON object printed at the end of `borg list`."""

    archives: List[_BorgArchive]
