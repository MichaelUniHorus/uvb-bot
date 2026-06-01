import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class NztiData:
    date: str
    time: str
    nzti: str
    name: str
    number1: str
    number2: str

def parse_nzti_message(text: str) -> Optional[NztiData]:
    patterns = [
        r'(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2})\s+МСК.*?НЖТИ\s+(\d+)\s+([А-Яа-яёЁA-Za-z]+)\s+(\d+)\s+(\d+)',
        r'(\d{2}\.\d{2}\.\d{2})\s+(\d{2}:\d{2}).*?НЖТИ\s+(\d+)\s+([А-Яа-яёЁA-Za-z]+)\s+(\d+)\s+(\d+)',
        r'НЖТИ\s+(\d+)\s+([А-Яа-яёЁA-Za-z]+)\s+(\d+)\s+(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            groups = match.groups()
            if len(groups) == 6:
                return NztiData(
                    date=groups[0],
                    time=groups[1],
                    nzti=groups[2],
                    name=groups[3],
                    number1=groups[4],
                    number2=groups[5]
                )
            elif len(groups) == 4:
                return NztiData(
                    date="",
                    time="",
                    nzti=groups[0],
                    name=groups[1],
                    number1=groups[2],
                    number2=groups[3]
                )
    return None

def has_nzti_tag(text: str) -> bool:
    return "#НЖТИ" in text or "#нжти" in text
