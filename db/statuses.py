from enum import Enum

class Status(str, Enum):
    pass

class DownloadStatus(Status):
    QUEUED = "queued"
    UPLOADED = "uploaded"

class WatermarkStatus(Status):
    WATERMARK = "watermark"
    ERROR_DONE = "error_done"
    DONE = "done"
