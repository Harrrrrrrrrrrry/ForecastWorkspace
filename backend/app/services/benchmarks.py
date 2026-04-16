from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkIndex:
    symbol: str
    name: str


BENCHMARK_INDICES: list[BenchmarkIndex] = [
    BenchmarkIndex(symbol="^GSPC", name="S&P 500"),
    BenchmarkIndex(symbol="^IXIC", name="NASDAQ Composite"),
    BenchmarkIndex(symbol="^DJI", name="Dow Jones Industrial Average"),
    BenchmarkIndex(symbol="^RUT", name="Russell 2000"),
]
