from dataclasses import dataclass
@dataclass(frozen=True)
class ChartPoint: timestamp:str; value:float; metadata:tuple[tuple[str,str],...]=()
@dataclass(frozen=True)
class ChartSeries: name:str; source_label:str; points:tuple[ChartPoint,...]; state:str; disclaimer:str; total_points:int; offset:int; limit:int
