import importlib.metadata
import json
import pathlib
import time
import timeit
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, NamedTuple

import benchmarks
import matplotlib.pyplot as plt
import pandas
from common import Benchmark, Methods

ROOT_DIR = pathlib.Path(__file__).parent.parent
DATA_PATH = ROOT_DIR / "benchmark" / "data.json"
TABLE_PATH = ROOT_DIR / "examples" / "benchmark_table.md"
CHART_PATH = ROOT_DIR / "docs" / "benchmark_chart.svg"
CHART_TRUNCATE = 20

packages = [
    path.stem
    for path in pathlib.Path(benchmarks.__file__).parent.iterdir()
    if not path.name.startswith("_")
]


def time_it(func: Callable, arg: Any) -> float:
    timer = timeit.Timer("func(arg)", globals=locals())
    number, _ = timer.autorange()
    return min(timer.repeat(number=number)) / number


class BenchmarkResult(NamedTuple):
    first_run: float
    deserialization: float
    serialization: float


def run_benchmark(
    methods: Methods, data: Mapping[str, Any], key: str
) -> BenchmarkResult:
    print(f"\t{key}")
    assert isinstance(methods, Methods)
    deserializer, serializer = methods
    first_run_start = time.perf_counter_ns()
    deserialized = deserializer(data[key])
    serializer(deserialized)
    first_run_end = time.perf_counter_ns()
    first_run = (first_run_end - first_run_start) * 1e-9
    print(f"\t\tfirst run: {first_run}")
    deserialization = time_it(deserializer, data[key])
    print(f"\t\tdeserialization: {deserialization}")
    serialization = time_it(serializer, deserialized)
    print(f"\t\tserialization: {serialization}")
    return BenchmarkResult(first_run, deserialization, serialization)


class FullBenchmarkResult(NamedTuple):
    simple_deserialization: float
    complex_deserialization: float
    simple_serialization: float
    complex_serialization: float


@dataclass(frozen=True)
class LibraryBenchmarkResult:
    library: str
    version: str
    result: FullBenchmarkResult

    def total(self) -> float:
        return sum(self.result)

    def relative(self, ref: "LibraryBenchmarkResult") -> "LibraryBenchmarkResult":
        result = FullBenchmarkResult(*(a / b for a, b in zip(self.result, ref.result)))
        return replace(self, result=result)


def run_library_benchmark(
    package: str, data: Mapping[str, Any]
) -> LibraryBenchmarkResult:
    print("====================")
    print(package)
    # import module before importing benchmark module in order to remove it
    # from startup_time
    importlib.import_module(package)
    start_import = time.perf_counter_ns()
    module = importlib.import_module(f"{benchmarks.__name__}.{package}")
    end_import = time.perf_counter_ns()
    startup_time = (end_import - start_import) * 1e-9
    simple_methods, complex_methods, library = next(
        val for val in module.__dict__.values() if isinstance(val, Benchmark)
    )
    library = library or package
    simple_results, complex_results = [
        run_benchmark(methods, data, key)
        for methods, key in [(simple_methods, "simple"), (complex_methods, "complex")]
    ]
    print(
        f"startup time: {startup_time + simple_results.first_run + complex_results.first_run}"
    )
    return LibraryBenchmarkResult(
        library,
        importlib.metadata.version(library),
        FullBenchmarkResult(
            simple_results.deserialization,
            complex_results.deserialization,
            simple_results.serialization,
            complex_results.serialization,
        ),
    )


def main():
    with open(DATA_PATH) as json_file:
        data = json.load(json_file)
    results = sorted(
        (run_library_benchmark(p, data) for p in packages),
        key=LibraryBenchmarkResult.total,
    )
    relative_results = [res.relative(results[0]) for res in results]
    with open(TABLE_PATH, "w") as table:
        table.write("|library|version|deserialization|serialization|\n")
        table.write("|-|-|-:|-:|\n")
        for res in relative_results:
            if all(r == 1.0 for r in res.result):
                deserialization, serialization = "/", "/"
            else:
                deserialization, serialization = [
                    f"x{round(sum(res.result[index:index+2])/2, 1)}"
                    f" ({round(res.result[index], 1)}/{round(res.result[index+1], 1)})"
                    for index in (0, 2)
                ]
            table.write(
                f"|{res.library}|{res.version}|{deserialization}|{serialization}|\n"
            )
    columns = [
        f"{op} ({bench})"
        for op in ("deserialization", "serialization")
        for bench in ("simple", "complex")
    ]
    df = pandas.DataFrame(
        [
            [res.library] + [min(r, CHART_TRUNCATE) for r in res.result]
            for res in relative_results
        ],
        columns=["library"] + columns,
    )
    ax = df.plot.bar(x="library", title="Benchmark (lower is better)", rot=45)
    plt.xlabel("")
    plt.tight_layout()
    for container in ax.containers:
        ax.bar_label(
            container,
            labels=["" if v < CHART_TRUNCATE else "··" for v in container.datavalues],
            padding=2,
            rotation=90,
        )
    plt.savefig(str(CHART_PATH))


if __name__ == "__main__":
    main()