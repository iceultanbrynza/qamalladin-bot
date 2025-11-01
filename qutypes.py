from enum import Enum

class ProgressResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    FINISHED = "finished"
    STANDSTILL = 'standsill'