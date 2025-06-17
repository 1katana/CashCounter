from enum import Enum

class Status(str, Enum):
    pass

class DownloadStatus(Status):
    QUEUED = "queued"
    UPLOADED = "uploaded"

class WatermarkStatus(Status):
    CAPTION = "caption"
    NOT_CAPTION = "not_caption"

class DoneStatus(Status):
    ERROR_DONE = "error_done"
    DONE = "done"
    FAILED = "failed"
