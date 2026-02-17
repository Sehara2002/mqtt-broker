from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict, Set, Dict, Optional

@dataclass
class BrokerState:
    # exact topic -> set of writers
    subscribers: DefaultDict[str, Set[object]] = field(default_factory=lambda: defaultdict(set))
    # writer -> set of topics (for cleanup)
    client_topics: DefaultDict[object, Set[str]] = field(default_factory=lambda: defaultdict(set))
    # writer -> client_id
    client_ids: Dict[object, str] = field(default_factory=dict)

STATE = BrokerState()